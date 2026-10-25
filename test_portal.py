import datetime as dt, tempfile, unittest, zipfile
from pathlib import Path
import server as p

class PortalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=p.ROOT)
        self.old=(p.DB,p.REPORTS)
        p.DB=Path(self.tmp.name)/'test.sqlite3';p.REPORTS=Path(self.tmp.name)
        p.init()
    def tearDown(self):
        p.DB,p.REPORTS=self.old
        self.tmp.cleanup()
    def populated(self):
        s=p.state()
        s['faculty']=[{'id':'f1','name':'Test Faculty','designation':'Professor','areas':['A7']},{'id':'f2','name':'Second Faculty','designation':'Professor','areas':['A4']}]
        s['goals']=[{'id':'g1','title':'Research target','target':'Two proposals','section':'A7','start':'2026-10-01','due':'2026-12-31','owner':''}]
        return s
    def test_assignment_dates_and_idempotence(self):
        s=self.populated();self.assertTrue(p.automate(s,dt.date(2026,10,25)))
        self.assertEqual(len(s['tasks']),5)
        growth=[t for t in s['tasks'] if t['kind']=='growth']
        self.assertTrue(all(t['owner']=='f1' for t in growth))
        self.assertEqual(growth[-1]['due'],'2026-12-31')
        self.assertEqual(s['tasks'][0]['due'],'2026-10-23')
        self.assertFalse(p.automate(s,dt.date(2026,10,25)))
        p.automate(s,dt.date(2026,10,26));self.assertEqual(len(s['tasks']),7)
    def test_month_boundaries(self):
        self.assertEqual(p.prior_month(dt.date(2027,1,2)),'2026-12')
        self.assertEqual(p.prior_month(dt.date(2024,3,2)),'2024-02')
    def test_report_mapping_and_package_fidelity(self):
        s=self.populated();p.automate(s,dt.date(2026,10,25))
        s['settings'].update(school='Test School',department='Test Department',programmes='BTech',dean='Test Dean',hod='Test HOD')
        for date,value in [('2026-10-01','Old snapshot'),('2026-10-20','Latest snapshot'),('2026-11-01','Wrong month')]:
            s['updates'].append({'id':date,'faculty':'f1','date':date,'section':'A7','values':['Proposals','2',value,'2','Quality','Review','Test Faculty','Evidence']})
        s['summary']['2026-10']={'achievements':'Summary achievement'}
        p.save(s);name=p.report('2026-10')
        with zipfile.ZipFile(p.ROOT/'mis-template.docx') as ref,zipfile.ZipFile(p.REPORTS/name) as out:
            for n in ref.namelist():
                if n!='word/document.xml':self.assertEqual(ref.read(n),out.read(n),n)
            xml=p.ET.fromstring(out.read('word/document.xml'))
            text=' '.join(t.text or '' for t in xml.iter(p.W+'t'))
            self.assertIn('Latest snapshot',text);self.assertNotIn('Old snapshot',text);self.assertNotIn('Wrong month',text)
            self.assertIn('Summary achievement',text);self.assertIn('Test Department',text)
            self.assertNotIn('182/190 (95.8%)',text)
            self.assertNotIn('42% of semester plan',text)
            tables=xml.findall('.//'+p.W+'body/'+p.W+'tbl');self.assertEqual(len(tables),10)
            self.assertEqual(len(tables[6].findall(p.W+'tr')),2)
            self.assertEqual(p.ET.tostring(xml.find('.//'+p.W+'sectPr')),p.ET.tostring(p.ET.fromstring(ref.read('word/document.xml')).find('.//'+p.W+'sectPr')))
    def test_missing_data_is_explicit(self):
        name=p.report('2026-09')
        with zipfile.ZipFile(p.REPORTS/name) as z:
            self.assertIn('No verified data submitted',z.read('word/document.xml').decode())

if __name__=='__main__':unittest.main()
