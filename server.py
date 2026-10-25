"""Department MIS portal. Standard-library runtime, local SQLite storage."""
import calendar, copy, datetime as dt, io, json, os, re, sqlite3, sys, threading, time, uuid, zipfile
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
from contextlib import contextmanager

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
DATA.mkdir(exist_ok=True)
REPORTS = DATA / 'reports'
REPORTS.mkdir(exist_ok=True)
DB = DATA / 'portal.sqlite3'
LOCK = threading.RLock()
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
def today(): return dt.datetime.now(IST).date()
def uid(): return uuid.uuid4().hex
@contextmanager
def connect():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    try:
        with c: yield c
    finally: c.close()
def init():
    with connect() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS state(id INTEGER PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS reports(month TEXT PRIMARY KEY, filename TEXT NOT NULL, generated TEXT NOT NULL);''')
        c.execute('INSERT OR IGNORE INTO state VALUES(1,?)', (json.dumps({'settings': {'school':'','department':'','programmes':'','dean':'','hod':'','weeklyDay':4},'faculty':[],'tasks':[],'updates':[],'goals':[],'summary':{}}),))
def state():
    with connect() as c: return json.loads(c.execute('SELECT payload FROM state WHERE id=1').fetchone()[0])
def save(s):
    with connect() as c: c.execute('UPDATE state SET payload=? WHERE id=1',(json.dumps(s),))
def prior_month(d): return (d.replace(day=1)-dt.timedelta(days=1)).strftime('%Y-%m')
def week(d): return (d-dt.timedelta(days=d.weekday())).isoformat()

HEADERS = {
'A2':['Indicator / KPI','Definition / unit','Annual or semester target','Target for month','Actual this month','Cumulative actual','Variance / status','Brief explanation / action'],
'A4':['Indicator','What to report / unit','Target','Actual this month','Cumulative actual','Gap / reason','Corrective action, owner & date','Evidence reference'],
'A5':['Indicator','Population / denominator','Target','Actual','Gap / students needing support (aggregate)','Action taken','Owner & due date','Outcome / evidence'],
'A6':['Activity / KPI','Target / due date','Actual / completion date','Status','Reason for variance','Pending action / owner','Evidence'],
'A7':['Indicator','Target (year/month)','Actual this month','Cumulative actual','Quality / value / outcome','Next milestone & date','Owner','Evidence'],
'A8':['Area / activity','Target','Actual','Variance / explanation','Action / next milestone','Owner & due date','Benefit / evidence'],
'A9':['Requirement / issue','Applicable standard / target','Due date','Current status','Risk / impact','Action / responsible person','Support / decision required','Evidence'],
'A10':['Previous commitment / issue','Original due date','Current status / evidence','Reason not closed','Next action / revised date','Accountable person','Decision / support required']}
LABELS={'A2':'Executive dashboard','A4':'Teaching & curriculum','A5':'Student support','A6':'Assessment & exams','A7':'Research & innovation','A8':'Faculty & collaborations','A9':'Quality & infrastructure','A10':'Review commitments'}

def automate(s, d):
    """Idempotent weekly requests and monthly growth milestones."""
    changed=False
    monday=week(d)
    due=(dt.date.fromisoformat(monday)+dt.timedelta(days=int(s['settings'].get('weeklyDay',4)))).isoformat()
    for f in s['faculty']:
        key=f'weekly:{monday}:{f["id"]}'
        if not any(t.get('key')==key for t in s['tasks']):
            s['tasks'].append({'id':uid(),'key':key,'title':'Submit weekly academic update','owner':f['id'],'section':'A10','start':monday,'due':due,'status':'Not Started','progress':0,'target':'Submit verified weekly MIS entries with evidence','evidence':'','reason':'','recovery':'','support':'','kind':'weekly'})
            changed=True
    for g in s['goals']:
        if not g.get('active',True): continue
        for offset, step in enumerate(['Baseline & action plan','Execute & collect evidence','Review outcomes & close gaps'],1):
            key=f'goal:{g["id"]}:{offset}'
            if any(t.get('key')==key for t in s['tasks']): continue
            start=dt.date.fromisoformat(g['start'])
            end=dt.date.fromisoformat(g['due'])
            due_date=start+(end-start)*offset/3
            owner=g.get('owner')
            if not owner and s['faculty']:
                eligible=[f for f in s['faculty'] if g['section'] in f.get('areas',[])] or s['faculty']
                owner=min(eligible,key=lambda f:sum(t['owner']==f['id'] and t['status']!='Completed' for t in s['tasks']))['id']
            if not owner: continue
            s['tasks'].append({'id':uid(),'key':key,'title':g['title']+' · '+step,'owner':owner,'section':g['section'],'start':g['start'],'due':due_date.isoformat(),'status':'Not Started','progress':0,'target':g['target'],'evidence':'','reason':'','recovery':'','support':'','kind':'growth'})
            changed=True
    return changed

W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
ET.register_namespace('w',W[1:-1])
def set_text(element,text):
    ps=element.findall(W+'p') if element.tag==W+'tc' else [element]
    p=ps[0] if ps else ET.SubElement(element,W+'p')
    proto=p.find(W+'r')
    style=copy.deepcopy(proto.find(W+'rPr')) if proto is not None and proto.find(W+'rPr') is not None else None
    for child in list(p):
        if child.tag!=W+'pPr': p.remove(child)
    r=ET.SubElement(p,W+'r')
    if style is not None: r.append(style)
    ET.SubElement(r,W+'t').text=str(text)
    for extra in ps[1:]: element.remove(extra)
def report(month):
    dt.datetime.strptime(month,'%Y-%m')
    s=state()
    cut=dt.date.fromisoformat(month+'-01').replace(day=calendar.monthrange(int(month[:4]),int(month[5:]))[1])
    people={f['id']:f['name']+' / '+f['designation'] for f in s['faculty']}
    with zipfile.ZipFile(ROOT/'mis-template.docx') as z:
        source_xml=z.read('word/document.xml')
        for _, (prefix, uri) in ET.iterparse(io.BytesIO(source_xml), events=['start-ns']):
            if prefix!='xml': ET.register_namespace(prefix,uri)
        xml=ET.fromstring(source_xml)
        tables=xml.findall('.//'+W+'body/'+W+'tbl')
        settings=s['settings']
        particulars='  |  '.join([f'School: {settings["school"] or "Pending"}',f'Department/Discipline: {settings["department"] or "Pending"}',f'Programme(s): {settings["programmes"] or "Pending"}',f'Reporting month: {month}',f'Cut-off date: {cut.isoformat()}',f'Dean: {settings["dean"] or "Pending"}',f'HOD/Coordinator: {settings["hod"] or "Pending"}','Date submitted: Pending submission'])
        set_text(tables[0].findall(W+'tr')[1].findall(W+'tc')[0],particulars)
        # Weekly records are cumulative snapshots: latest per faculty/section/indicator wins.
        latest={}
        for u in sorted(s['updates'],key=lambda u:(u['date'],u.get('savedAt',''))):
            if u['date'].startswith(month): latest[(u['faculty'],u['section'],u['values'][0].strip().casefold())]=u
        sections=['A2','A3','A4','A5','A6','A7','A8','A9','A10']
        for table,section in zip(tables[1:],sections):
            old=table.findall(W+'tr'); proto=copy.deepcopy(old[1])
            for row in old[1:]: table.remove(row)
            rows=[]
            if section=='A3':
                for t in s['tasks']:
                    if t['start']<=cut.isoformat() and t['due']>=month+'-01':
                        rows.append([str(len(rows)+1),t['title'],t['target'],t['start'],t['due'],people.get(t['owner'],'Owner pending'),t['status']+f' / {t["progress"]}%',t['evidence'],t['reason'],t['recovery'],t['support']])
            else:
                rows=[u['values'] for u in latest.values() if u['section']==section]
            if not rows: rows=[['No verified data submitted for this reporting period']+['Pending']*(len(proto.findall(W+'tc'))-1)]
            for values in rows:
                row=copy.deepcopy(proto)
                for cell,value in zip(row.findall(W+'tc'),values): set_text(cell,value or 'Not reported')
                table.append(row)
        replacements={'Key achievements this month (up to 3):': 'achievements','Major gaps / risks and recovery actions:':'risks','Decisions/resources required from University leadership:':'decisions','Priorities for next month:':'priorities'}
        summary=s['summary'].get(month,{})
        for p in xml.findall('.//'+W+'body/'+W+'p'):
            text=''.join(t.text or '' for t in p.iter(W+'t'))
            for label,key in replacements.items():
                if text.startswith(label): set_text(p,label+' '+(summary.get(key) or 'Pending review'))
            if text.startswith('Dean:'): set_text(p,f'Dean: {settings["dean"] or "Pending"}    Signature: __________________    Date: ______________')
        filename=f'Monthly_Academic_MIS_{month}.docx'
        tmp=REPORTS/(filename+'.tmp')
        generated=ET.tostring(xml,encoding='utf-8',xml_declaration=True)
        original_root=re.search(rb'<w:document\b[^>]*>',source_xml).group(0)
        generated=re.sub(rb'<w:document\b[^>]*>',lambda _:original_root,generated,count=1)
        with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as out:
            for item in z.infolist(): out.writestr(item,generated if item.filename=='word/document.xml' else z.read(item.filename))
        tmp.replace(REPORTS/filename)
    with connect() as c: c.execute('INSERT OR REPLACE INTO reports VALUES(?,?,?)',(month,filename,dt.datetime.now(IST).isoformat()))
    return filename

def tick():
    with LOCK:
        s=state()
        if automate(s,today()): save(s)
        month=prior_month(today())
        with connect() as c: exists=c.execute('SELECT 1 FROM reports WHERE month=?',(month,)).fetchone()
        if today().day>=2 and not exists: report(month)
def scheduler():
    while True:
        try: tick()
        except Exception as e: print('Scheduler:',e,flush=True)
        time.sleep(60)

class Handler(BaseHTTPRequestHandler):
    def send(self,data,code=200,ctype='application/json'):
        body=json.dumps(data,ensure_ascii=False).encode() if ctype=='application/json' else data
        self.send_response(code); self.send_header('Content-Type',ctype); self.send_header('Content-Length',str(len(body))); self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff'); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/api/state':
            with LOCK:
                s=state()
                with connect() as c: s['reports']=[dict(r) for r in c.execute('SELECT * FROM reports ORDER BY month DESC')]
            s['headers']=HEADERS; s['labels']=LABELS; s['today']=today().isoformat()
            return self.send(s)
        if path=='/api/backup':
            with LOCK: return self.send(state())
        if path.startswith('/reports/'):
            name=path.split('/')[-1]
            if name!=os.path.basename(name) or not (REPORTS/name).is_file(): return self.send({'error':'Report not found'},404)
            return self.send((REPORTS/name).read_bytes(),ctype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        files={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}
        if path in files:
            ctype={'/':'text/html; charset=utf-8','/app.js':'text/javascript; charset=utf-8','/style.css':'text/css; charset=utf-8'}[path]
            return self.send((ROOT/files[path]).read_bytes(),ctype=ctype)
        self.send({'error':'Not found'},404)
    def do_POST(self):
        try:
            # Local service accepts same-origin requests only.
            if self.headers.get('Origin') and self.headers['Origin'] not in ['http://127.0.0.1:8765','http://localhost:8765']: return self.send({'error':'Origin denied'},403)
            size=int(self.headers.get('Content-Length',0))
            if size>2000000: raise ValueError('Request too large')
            p=json.loads(self.rfile.read(size)); path=urlparse(self.path).path
            with LOCK:
                s=state()
                if path=='/api/settings':
                    s['settings'].update({k:str(p.get(k,''))[:500] for k in ['school','department','programmes','dean','hod']})
                    s['settings']['weeklyDay']=int(p.get('weeklyDay',4))
                    if s['settings']['weeklyDay'] not in range(7): raise ValueError('Invalid weekly day')
                elif path=='/api/faculty':
                    if not p.get('name','').strip(): raise ValueError('Faculty name required')
                    s['faculty'].append({'id':uid(),'name':p['name'],'designation':p.get('designation','Faculty'),'email':p.get('email',''),'areas':p.get('areas',[])})
                elif path=='/api/goals':
                    if not p.get('title','').strip() or not p.get('target','').strip(): raise ValueError('Goal and measurable target required')
                    if p['section'] not in HEADERS: raise ValueError('Invalid area')
                    if dt.date.fromisoformat(p['due'])<dt.date.fromisoformat(p['start']): raise ValueError('Due date must follow start date')
                    if p.get('owner') and not any(f['id']==p['owner'] for f in s['faculty']): raise ValueError('Invalid owner')
                    s['goals'].append({**p,'id':uid(),'active':True})
                elif path=='/api/task':
                    t=next(t for t in s['tasks'] if t['id']==p['id'])
                    if p['status'] not in ['Not Started','On Track','At Risk','Delayed','Completed','On Hold']: raise ValueError('Invalid status')
                    progress=int(p['progress'])
                    if progress<0 or progress>100: raise ValueError('Progress must be 0–100')
                    if p['status'] in ['At Risk','Delayed'] and (not p.get('reason') or not p.get('recovery')): raise ValueError('Reason and recovery action with revised date are required')
                    t.update({k:p.get(k,'') for k in ['status','evidence','reason','recovery','support']}); t['progress']=100 if p['status']=='Completed' else progress
                elif path=='/api/update':
                    if not any(f['id']==p['faculty'] for f in s['faculty']): raise ValueError('Select a faculty member')
                    if p['section'] not in HEADERS or len(p['values'])!=len(HEADERS[p['section']]): raise ValueError('Invalid report fields')
                    if not p['values'][0].strip(): raise ValueError('Indicator required')
                    dt.date.fromisoformat(p['date'])
                    if p['date']>today().isoformat(): raise ValueError('Future updates are not allowed')
                    p.update(id=uid(),savedAt=dt.datetime.now(IST).isoformat()); s['updates'].append(p)
                elif path=='/api/weekly-complete':
                    t=next(t for t in s['tasks'] if t['id']==p['id'] and t.get('kind')=='weekly')
                    entries=[u for u in s['updates'] if u['faculty']==t['owner'] and week(dt.date.fromisoformat(u['date']))==t['start']]
                    if not entries: raise ValueError('Add at least one weekly MIS entry before completing the submission')
                    t['status']='Completed'; t['progress']=100; t['evidence']=f'{len(entries)} MIS entries submitted; HOD review required'
                elif path=='/api/summary': s['summary'][p['month']]={k:p.get(k,'') for k in ['achievements','risks','decisions','priorities']}
                elif path=='/api/report':
                    filename=report(p['month']); return self.send({'filename':filename})
                elif path=='/api/run': pass
                else: return self.send({'error':'Unknown action'},404)
                automate(s,today()); save(s)
            self.send({'ok':True})
        except (ValueError,KeyError,StopIteration,TypeError) as e: self.send({'error':str(e) or 'Record not found'},400)
        except Exception as e:
            print('Request failed:',e,flush=True); self.send({'error':'Could not save. Check the portal log.'},500)
    def log_message(self,*args): pass

if __name__=='__main__':
    init(); tick()
    if '--run-once' in sys.argv:
        print('Scheduled MIS check complete',flush=True)
        sys.exit(0)
    threading.Thread(target=scheduler,daemon=True).start()
    httpd=ThreadingHTTPServer(('127.0.0.1',8765),Handler)
    if '--open-browser' in sys.argv:
        import webbrowser
        threading.Timer(1,lambda:webbrowser.open('http://127.0.0.1:8765')).start()
    print('Department MIS portal ready: http://127.0.0.1:8765',flush=True)
    httpd.serve_forever()
