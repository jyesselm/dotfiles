"""Regression coverage for GUI convergence without touching live apps."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sync_search as s


class SearchTests(unittest.TestCase):
    def test_f4_preserves_other_profiles_rules_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'karabiner.json'
            other = {'description':'Another shortcut','manipulators':[]}
            inactive = {'name':'Other','selected':False}
            path.write_text(json.dumps({'profiles':[inactive,{'selected':True,'complex_modifications':{'rules':[other,{'description':s.OLD_DESCRIPTION}]}}]}))
            original = path.read_bytes()
            self.assertEqual(s.configure_f4(path,True)[0],'ok')
            self.assertEqual(path.read_bytes(),original)
            self.assertEqual(s.configure_f4(path)[0],'changed')
            data = json.loads(path.read_text())
            self.assertEqual(data['profiles'][0],inactive)
            self.assertEqual(data['profiles'][1]['complex_modifications']['rules'],[s.f4_rule(),other])
            self.assertEqual(s.configure_f4(path)[0],'ok')
            self.assertEqual(len(list(Path(d).glob('*.before-*'))),1)

    def test_gui_command_excludes_indexers_and_other_python(self):
        self.assertTrue(s.is_gui_command('/env/bin/python /home/user/.local/bin/s gui'))
        self.assertTrue(s.is_gui_command('/env/bin/python -m search_cli.cli gui'))
        for command in ('python something.py','s warm','s index','s','python -m search_cli.cli notes'):
            self.assertFalse(s.is_gui_command(command),command)

    def test_source_change_retires_resident_once_and_plan_does_not_mutate(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d);source=root/'src/search_cli/desktop_ui.py'
            source.parent.mkdir(parents=True);source.write_text('old')
            marker=root/'state/gui.sha256'
            with patch.object(s,'resident_pid',return_value=55),patch.object(s.os,'kill') as kill:
                s.refresh_resident(root,marker,True)
                kill.assert_not_called();self.assertFalse(marker.exists())
            with patch.object(s,'resident_pid',side_effect=[55,None]),patch.object(s.os,'kill') as kill:
                self.assertEqual(s.refresh_resident(root,marker)[0],'changed')
                kill.assert_called_once_with(55,s.signal.SIGTERM)
            with patch.object(s,'resident_pid') as pid:
                self.assertEqual(s.refresh_resident(root,marker)[0],'ok');pid.assert_not_called()
            source.write_text('new')
            with patch.object(s,'resident_pid',return_value=None):
                self.assertEqual(s.refresh_resident(root,marker)[0],'changed')

    def test_pid_validation_requires_owner_and_gui_command(self):
        from subprocess import CompletedProcess
        with tempfile.TemporaryDirectory() as d:
            lock=Path(d)/'lock';lock.write_text('55\npython\nhost\n')
            for line,expected in [('501 /env/bin/python /home/me/.local/bin/s gui',55),('502 /env/bin/python /home/me/.local/bin/s gui',None),('501 python other.py',None)]:
                with patch.object(s.subprocess,'run',return_value=CompletedProcess([],0,line,'')):
                    self.assertEqual(s.resident_pid(lock,501),expected)

    def test_retire_only_old_alfred_search_binding(self):
        import plistlib
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);prefs=root/'Library/Application Support/Alfred/prefs.json'
            prefs.parent.mkdir(parents=True)
            folder=root/'Alfred.alfredpreferences';prefs.write_text(json.dumps({'current':str(folder)}))
            path=folder/'workflows/search/info.plist';path.parent.mkdir(parents=True)
            old={'type':'alfred.workflow.trigger.hotkey','config':{'hotkey':43,'hotmod':1048576,'hotstring':','}}
            other={'type':'alfred.workflow.trigger.hotkey','config':{'hotkey':44,'hotmod':1048576}}
            path.write_bytes(plistlib.dumps({'name':'Search CLI Launcher','objects':[old,other]}))
            original=path.read_bytes()
            s.retire_alfred_binding(root,True);self.assertEqual(path.read_bytes(),original)
            self.assertEqual(s.retire_alfred_binding(root)[0],'changed')
            data=plistlib.loads(path.read_bytes())
            self.assertEqual(data['objects'][0]['config']['hotmod'],0)
            self.assertEqual(data['objects'][1],other)
            self.assertEqual(s.retire_alfred_binding(root)[0],'ok')
            self.assertEqual(len(list(path.parent.glob('info.before-*'))),1)
