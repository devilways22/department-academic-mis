"""Optional per-user Linux/macOS scheduler. Run --dry-run before installation."""
import argparse
import os
from pathlib import Path
import plistlib
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
LABEL = 'org.department-academic-mis.daily'

def systemd_quote(value):
    value=str(value)
    if '\n' in value or '\r' in value: raise ValueError('Paths must not contain newlines')
    return '"'+value.replace('\\','\\\\').replace('"','\\"').replace('%','%%')+'"'

def plan(platform, home=None, root=None, python=None):
    home=Path(home) if home else Path.home()
    root=Path(root) if root else ROOT
    python=python or sys.executable
    if platform=='linux':
        directory=home/'.config/systemd/user'
        service=directory/'department-academic-mis.service'
        timer=directory/'department-academic-mis.timer'
        files={service:('[Unit]\nDescription=Department Academic MIS report check\n\n[Service]\nType=oneshot\n'
            f'WorkingDirectory={systemd_quote(root)}\nExecStart={systemd_quote(python)} {systemd_quote(root/"server.py")} --run-once\n'),
            timer:('[Unit]\nDescription=Daily academic MIS check at 09:00\n\n[Timer]\nOnCalendar=*-*-* 09:00:00\nPersistent=true\nUnit=department-academic-mis.service\n\n[Install]\nWantedBy=timers.target\n')}
        install=[['systemctl','--user','daemon-reload'],['systemctl','--user','enable','--now',timer.name]]
        remove=[['systemctl','--user','disable','--now',timer.name]]
        return files,install,remove
    if platform=='darwin':
        plist=home/'Library/LaunchAgents'/f'{LABEL}.plist'
        data={'Label':LABEL,'ProgramArguments':[str(python),str(root/'server.py'),'--run-once'],
              'WorkingDirectory':str(root),'StartCalendarInterval':{'Hour':9,'Minute':0},'RunAtLoad':True,
              'ProcessType':'Background'}
        files={plist:plistlib.dumps(data).decode('utf-8')}
        uid=os.getuid() if hasattr(os,'getuid') else 501
        return files,[['launchctl','bootstrap',f'gui/{uid}',str(plist)]],[['launchctl','bootout',f'gui/{uid}',str(plist)]]
    raise ValueError('Use Windows Enable Automatic Reports.ps1, or run this script on Linux/macOS.')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['install','remove'],nargs='?',default='install')
    parser.add_argument('--dry-run',action='store_true',help='Print proposed files and commands without changing anything')
    parser.add_argument('--platform',choices=['linux','darwin'],help='Preview another platform; requires --dry-run')
    args=parser.parse_args()
    if args.platform and not args.dry_run: parser.error('--platform is supported only with --dry-run')
    try: files,install,remove=plan(args.platform or sys.platform)
    except ValueError as e: parser.error(str(e))
    commands=install if args.action=='install' else remove
    if args.dry_run:
        for path,content in files.items(): print(f'FILE: {path}\n{content}')
        for command in commands: print('COMMAND:',repr(command))
        return
    if args.action=='install':
        if any(path.exists() for path in files):
            parser.error('A scheduler file already exists. Run remove first before reinstalling.')
        for path,content in files.items():
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(content,encoding='utf-8')
    try:
        for command in commands: subprocess.run(command,check=True)
    except (OSError,subprocess.CalledProcessError) as e:
        print(f'Scheduler action failed: {e}. Configuration paths are:',file=sys.stderr)
        for path in files: print(path,file=sys.stderr)
        print('Check your systemd user session or macOS LaunchAgent permissions; then remove/reinstall.',file=sys.stderr)
        sys.exit(1)
    if args.action=='remove':
        for path in files: path.unlink(missing_ok=True)
        if sys.platform=='linux': subprocess.run(['systemctl','--user','daemon-reload'],check=True)
    print('Scheduler '+('installed: daily 09:00 local time.' if args.action=='install' else 'removed.'))

if __name__=='__main__': main()
