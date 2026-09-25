import importlib.util
import io
import json
from pathlib import Path
import plistlib
import tarfile
import tempfile
import unittest
spec=importlib.util.spec_from_file_location('mac_state',Path(__file__).with_name('mac-state.py'))
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
class Tests(unittest.TestCase):
 def setUp(self): self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
 def tearDown(self): self.temp.cleanup()
 def test_inventory_stops_at_app_bundles(self):
  outer=self.root/'Test.app/Contents'; outer.mkdir(parents=True)
  (outer/'Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier':'test','CFBundleShortVersionString':'1.2'}))
  (outer/'Nested.app').mkdir()
  apps,errors=m.app_inventory([self.root])
  self.assertEqual(len(apps),1); self.assertEqual(apps[0]['version'],'1.2'); self.assertFalse(errors)
 def test_archive_roundtrip_preserves_executable_workflow(self):
  src=self.root/'workflow'; src.write_text('private test data'); src.chmod(0o700)
  out=self.root/'out.tar.gz'; hashes={}
  with tarfile.open(out,'w:gz') as a:
   m.add_tree(a,src,'alfred/workflow',hashes)
   m.add_bytes(a,'manifest.json',json.dumps({'sha256':hashes}).encode(),{})
  self.assertEqual(m.verify_tar(out)['sha256'],hashes)
  with tarfile.open(out) as a: self.assertEqual(a.getmember('alfred/workflow').mode,0o700)
 def test_rejects_symlink_sources(self):
  p=self.root/'link'; p.symlink_to('/etc/passwd')
  with tarfile.open(self.root/'out.tar','w') as a:
   with self.assertRaises(RuntimeError): m.add_tree(a,p,'link',{})
 def test_rejects_path_traversal(self):
  out=self.root/'out.tar.gz'
  with tarfile.open(out,'w:gz') as a: m.add_bytes(a,'../bad',b'x',{})
  with self.assertRaises(ValueError): m.verify_tar(out)
 def test_rejects_tampered_content(self):
  out=self.root/'out.tar.gz'
  with tarfile.open(out,'w:gz') as a:
   m.add_bytes(a,'file',b'changed',{})
   m.add_bytes(a,'manifest.json',json.dumps({'sha256':{'file':'wrong'}}).encode(),{})
  with self.assertRaises(ValueError): m.verify_tar(out)
 def test_public_inventory_contains_no_paths_or_private_data(self):
  state={'created_utc':'now','macos':'test','architecture':'arm64','homebrew':{},
         'applications':[{'name':'Test','version':'1','path':'/Users/private/Applications/Test.app'}],
         'private_license':'secret','errors':['private error']}
  exported=m.public_inventory(state)
  self.assertNotIn('secret',json.dumps(exported)); self.assertNotIn('/Users',json.dumps(exported))
  self.assertNotIn('errors',exported)
 def test_private_write_never_overwrites_key(self):
  p=self.root/'key'; m.private_write(p,b'secret')
  self.assertEqual(p.stat().st_mode & 0o777,0o600)
  with self.assertRaises(FileExistsError): m.private_write(p,b'replacement')
  self.assertEqual(p.read_bytes(),b'secret')
if __name__=='__main__': unittest.main()
