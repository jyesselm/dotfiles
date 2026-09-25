"""No live preference writes: isolated snapshots and mocked defaults calls."""
import contextlib
import importlib.util
import io
from pathlib import Path
import plistlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch
spec = importlib.util.spec_from_file_location('mac_settings', Path(__file__).with_name('mac-settings.py'))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.quiet = contextlib.redirect_stdout(io.StringIO()); self.quiet.__enter__()
    def tearDown(self):
        self.quiet.__exit__(None,None,None); self.temp.cleanup()
    def snapshot(self):
        return {'format':1,'domains':{'com.apple.dock':{'values':{'autohide':True},'unset':['tilesize']}}}
    def test_capture_excludes_unlisted_and_records_absence(self):
        with patch.object(m,'read_domain',return_value={'autohide':True,'license':'private','recent-apps':['private']}):
            s=m.capture()
        r=s['domains']['com.apple.dock']
        self.assertEqual(r['values'],{'autohide':True}); self.assertIn('tilesize',r['unset'])
        self.assertNotIn(b'private',plistlib.dumps(s))
    def test_unknown_domain_and_key_rejected(self):
        s=self.snapshot(); s['domains']['com.private']={}
        with self.assertRaises(ValueError): m.validate(s)
        s=self.snapshot(); s['domains']['com.apple.dock']['values']['persistent-apps']=[]
        with self.assertRaises(ValueError): m.validate(s)
    def test_plan_has_no_writes(self):
        with patch.object(m,'read_domain',return_value={'autohide':False,'tilesize':50,'unrelated':123}), patch.object(m,'backup',side_effect=AssertionError('backup')), patch.object(m.subprocess,'run',side_effect=AssertionError('process')):
            m.apply(self.snapshot(),plan=True)
    def test_apply_only_selected_keys_and_backup_first(self):
        events=[]
        def run(argv,**kwargs):
            events.append(argv); return subprocess.CompletedProcess(argv,0,b'',b'')
        pending=[('com.apple.dock','autohide',True,False),('com.apple.dock','tilesize',None,True)]
        def backup(data): events.append('backup'); return Path('/tmp/backup')
        with patch.object(m,'changes',side_effect=[pending,[]]), patch.object(m,'capture',return_value={}), patch.object(m,'backup',side_effect=backup), patch.object(m.subprocess,'run',side_effect=run):
            m.apply(self.snapshot(),plan=False)
        self.assertEqual(events[0],'backup')
        self.assertEqual(events[1][1:4],['write','com.apple.dock','autohide'])
        self.assertIs(plistlib.loads(events[1][-1].encode()),True)
        self.assertEqual(events[2],['/usr/bin/defaults','delete','com.apple.dock','tilesize'])
    def test_failure_reports_rollback_path(self):
        with patch.object(m,'changes',return_value=[('com.apple.dock','autohide',True,False)]), patch.object(m,'capture',return_value={}), patch.object(m,'backup',return_value=Path('/tmp/rollback.plist')), patch.object(m.subprocess,'run',return_value=subprocess.CompletedProcess([],1,b'',b'')):
            with self.assertRaisesRegex(RuntimeError,'rollback.plist'): m.apply(self.snapshot(),False)
    def test_backup_failure_prevents_changes(self):
        with patch.object(m,'changes',return_value=[('com.apple.dock','autohide',True,False)]), patch.object(m,'capture',return_value={}), patch.object(m,'backup',side_effect=OSError('disk full')), patch.object(m.subprocess,'run',side_effect=AssertionError('wrote')):
            with self.assertRaises(OSError): m.apply(self.snapshot(),False)
    def test_atomic_private_save_and_unique_backups(self):
        with patch.object(m,'BACKUPS',self.root):
            a=m.backup(self.snapshot()); b=m.backup(self.snapshot())
        self.assertNotEqual(a,b); self.assertEqual(a.stat().st_mode & 0o777,0o600)
        self.assertEqual(plistlib.loads(a.read_bytes()),self.snapshot())
    def test_read_errors_not_treated_as_unset(self):
        with patch.object(m.subprocess,'run',return_value=subprocess.CompletedProcess([],1,b'',b'Permission denied')):
            with self.assertRaises(RuntimeError): m.read_domain('com.apple.dock')
    def test_noop_never_backs_up_or_writes(self):
        with patch.object(m,'read_domain',return_value={'autohide':True,'unrelated':123}), patch.object(m,'backup',side_effect=AssertionError('backup')):
            m.apply(self.snapshot(),False)

if __name__=='__main__': unittest.main()
