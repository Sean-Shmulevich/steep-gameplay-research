import copy
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from engine.pose_link_builder_bench import inspect

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/'engine/examples/pose_link_builder.json'

class BuilderBenchTests(unittest.TestCase):
    def fixture(self):return json.loads(FIXTURE.read_text())

    def test_fixture_outputs_and_no_input_mutation(self):
        d=self.fixture();before=copy.deepcopy(d);r=inspect(d)
        self.assertEqual(d,before)
        self.assertEqual(r['final_counters'],dict(primary_count=1,secondary_count=2,result_count=3))
        self.assertEqual(r['primary'][0]['body_indices'],[7,8])
        self.assertEqual(r['primary'][0]['response'],[2]*4)
        self.assertEqual(r['secondary'][0]['direction'][:3],[-1,0,0])
        self.assertEqual(r['result_rows_hex'][0],struct.pack('<4f',3,3,3,3).hex())
        raw=bytes.fromhex(r['primary_rows_hex'][0])
        self.assertEqual(raw[0x40:0x50],bytes([0xa5])*16)

    def test_indexed_resource_can_select_different_profile(self):
        d=self.fixture();data=d['inputs'];p=copy.deepcopy(data['profiles']['profile']);p['field30']=.75
        data['profiles']['selected']=p
        data['resources']['resource']=dict(kind28=6,default20='profile',map60=[0],table50=['selected'])
        r=inspect(d)
        self.assertEqual(r['secondary'][0]['coefficient'],[.75]*4)

    def test_rejects_missing_capacity_and_implicit_provenance(self):
        d=self.fixture();d['inputs']['context']['result_rows_hex']=[]
        with self.assertRaises(ValueError):inspect(d)
        d=self.fixture();d.pop('provenance')
        with self.assertRaises(ValueError):inspect(d)

    def test_zero_count_preserves_all_storage(self):
        d=self.fixture();p=bytearray.fromhex(d['inputs']['payload_hex']);struct.pack_into('<I',p,0x110,0)
        d['inputs']['payload_hex']=p.hex();r=inspect(d)
        self.assertEqual(r['primary'],[])
        for name in ('primary','secondary','result'):
            self.assertEqual(r[name+'_rows_hex'],d['inputs']['context'][name+'_rows_hex'])

    def test_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'result.json'
            subprocess.run([sys.executable,'-m','engine.pose_link_builder_bench',str(FIXTURE),'--output',str(output)],cwd=ROOT,check=True,capture_output=True)
            self.assertEqual(json.loads(output.read_text()),inspect(self.fixture()))
