import copy
import json
from pathlib import Path
import unittest
from engine.spawn_publication_bench import run


def request():
    bank=dict(parent=[9]*8,default_pose=[8]*8,records=[[7]*8,[6]*8],count=1,reset_word=123)
    frame=dict(position=[1,2,3,99],rotation=[0,0,0,2],position_parent=None,rotation_parent=None,
               reciprocal_estimate=.5,slots=['a','a'])
    return dict(branch='supplied_spawn_publication',banks={'a':bank},frames=[frame])


class SpawnPublicationBenchTests(unittest.TestCase):
    def test_original_pipeline_receipts(self):
        path=Path(__file__).resolve().parents[1]/'native/snow_host/spawn_pipeline_records_validation.json'
        for row in json.loads(path.read_text())['rows']:
            r=request();r['banks']['b']=copy.deepcopy(r['banks']['a'])
            r['frames']=[dict(position=row['state']['position'],rotation=row['state']['rotation'],
                position_parent=row['first_parent'],rotation_parent=row['second_parent'],
                reciprocal_estimate=row['estimate'],slots=None if row['slots'] is None else
                [None if i is None else ('a','b')[i] for i in row['slots']])]
            result=run(r)
            self.assertEqual([list(x) for x in result['frames'][0]['matrix']],row['result']['matrix'])
    def test_alias_reset_and_tail_preservation_without_input_mutation(self):
        r=request();original=copy.deepcopy(r);result=run(r)
        self.assertEqual(r,original)
        self.assertEqual(result['frames'][0]['events'][-2:],['reset_a','reset_a'])
        self.assertEqual(result['banks']['a']['records'],[[0,0,0,0,0,0,0,1],[6]*8])
        self.assertEqual(result['banks']['a']['reset_word'],0)
        self.assertEqual(result['input_sha256'],run(r)['input_sha256'])
    def test_second_frame_missing_skeleton_retains_bank(self):
        r=request();r['frames'].append(dict(r['frames'][0],slots=None,position=[9,8,7,0]))
        result=run(r)
        self.assertEqual(result['banks']['a']['parent'][:4],[1,2,3,1])
        self.assertEqual(result['frames'][1]['matrix'][3],(9,8,7,1))
    def test_reject_missing_estimate_unknown_bank_and_capacity(self):
        for edit in ('estimate','bank','capacity'):
            r=request()
            if edit=='estimate':del r['frames'][0]['reciprocal_estimate']
            if edit=='bank':r['frames'][0]['slots'][0]='unknown'
            if edit=='capacity':r['banks']['a']['count']=3
            with self.assertRaises(ValueError):run(r)
