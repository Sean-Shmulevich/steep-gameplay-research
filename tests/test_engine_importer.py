import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from engine.importer import main
from engine.runtime import Engine


class ImporterTests(unittest.TestCase):
    def test_rejects_public_repository_output_before_reading_source(self):
        target=Path(__file__).resolve().parents[1]/'forbidden-asset.json'
        with patch('sys.argv',['importer','missing.json','--rig','male','--clip','idle','--unit-scale','1','--output',str(target)]):
            with self.assertRaisesRegex(ValueError,'outside the public'):
                main()
        self.assertFalse(target.exists())

    def test_synthetic_export_roundtrip(self):
        source={'skeletons':{'test':{'bones':[{'name':'root','binding_hash':7,'parent_index':None,'local_bind':{'translation':[0,0,0],'quaternion_xyzw':[0,0,0,1]}}]}},'representative_clips':[{'name':'idle','duration':1,'tracks':[]}]}
        with tempfile.TemporaryDirectory() as directory:
            src=Path(directory)/'source.json';dst=Path(directory)/'scene.json'
            src.write_text(json.dumps(source))
            with patch('sys.argv',['importer',str(src),'--rig','test','--clip','idle','--unit-scale','1','--loop','--output',str(dst)]),contextlib.redirect_stdout(io.StringIO()):
                main()
            engine=Engine(json.loads(dst.read_text()))
            engine.step(2)
            self.assertEqual(engine.rig['bones'][0]['name'],'root')
            self.assertEqual(engine.incidents,[])
