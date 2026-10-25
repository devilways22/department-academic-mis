import plistlib
from pathlib import Path
import unittest
from schedule_reports import plan,systemd_quote

class SchedulerTests(unittest.TestCase):
    def test_linux_timer_and_space_safe_paths(self):
        files,install,remove=plan('linux',home=Path('/home/test'),root=Path('/home/test/Dept Portal'),python='/opt/python 3/bin/python3')
        service=next(text for path,text in files.items() if path.suffix=='.service')
        timer=next(text for path,text in files.items() if path.suffix=='.timer')
        expected='ExecStart='+systemd_quote('/opt/python 3/bin/python3')+' '+systemd_quote(Path('/home/test/Dept Portal')/'server.py')+' --run-once'
        self.assertIn(expected,service)
        self.assertIn('Persistent=true',timer)
        self.assertIn('09:00:00',timer)
        self.assertEqual(install[-1][:4],['systemctl','--user','enable','--now'])
        self.assertEqual(remove[0][:4],['systemctl','--user','disable','--now'])
    def test_mac_plist_and_daily_schedule(self):
        files,install,remove=plan('darwin',home=Path('/Users/test'),root=Path('/Users/test/Dept Portal'),python='/usr/local/bin/python3')
        data=plistlib.loads(next(iter(files.values())).encode())
        self.assertEqual(data['ProgramArguments'],['/usr/local/bin/python3',str(Path('/Users/test/Dept Portal')/'server.py'),'--run-once'])
        self.assertEqual(data['StartCalendarInterval'],{'Hour':9,'Minute':0})
        self.assertTrue(data['RunAtLoad'])
        self.assertEqual(install[0][1],'bootstrap');self.assertEqual(remove[0][1],'bootout')
    def test_systemd_path_escaping(self):
        self.assertEqual(systemd_quote('/tmp/50% portal'),'"/tmp/50%% portal"')
        with self.assertRaises(ValueError):systemd_quote('/tmp/bad\npath')

if __name__=='__main__':unittest.main()
