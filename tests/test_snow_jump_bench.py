from copy import deepcopy
import json
from pathlib import Path
import unittest
from engine.snow_jump_bench import run


class SnowJumpBenchTests(unittest.TestCase):
    def scenario(self):
        return json.loads((Path(__file__).resolve().parents[1]/'engine/examples/snow_jump_input.json').read_text())

    def test_stateful_sequence_and_spin_preservation(self):
        document=self.scenario(); original=deepcopy(document); result=run(document)
        self.assertEqual(document,original)
        self.assertEqual([r['branch'] for r in result['trace']],['submit','cooldown','disabled','no_release','submit'])
        for r in result['trace']:
            for name in document['bodies']:
                self.assertEqual(r['bodies_after'][name]['angular'],tuple(document['bodies'][name]['angular']))
        self.assertEqual([r['body'] for r in result['trace'][0]['applications']],['rider','main'])
        self.assertGreater(result['final_bodies']['main']['linear'][2],15)

    def test_backend_suppression_does_not_cancel_countdown(self):
        document=self.scenario(); document['bodies']['main']['flags']=8
        result=run(document)
        self.assertEqual(result['final_bodies']['main']['linear'],(3,0,0))
        first=result['trace'][0]
        self.assertGreater(first['state_after']['cooldown'],0)
        self.assertTrue(first['applications'][1]['post_dispatch_requested'])
        self.assertFalse(first['applications'][1]['velocity_write_enabled'])

    def test_missing_rider_and_explicit_provenance(self):
        document=self.scenario(); del document['bodies']['rider']
        result=run(document)
        self.assertEqual([r['body'] for r in result['trace'][0]['applications']],['main'])
        del document['provenance']
        with self.assertRaises(ValueError): run(document)

    def test_invalid_interval_rejected_without_mutating_input(self):
        document=self.scenario(); document['frames'][0]['elapsed_dt']=0; original=deepcopy(document)
        with self.assertRaises(ValueError): run(document)
        self.assertEqual(document,original)

    def test_release_state_drives_one_jump_at_cooked_zero(self):
        path=Path(__file__).resolve().parents[1]/'engine/examples/snow_release_jump_input.json'
        document=json.loads(path.read_text()); original=deepcopy(document)
        result=run(document)
        self.assertEqual(document,original)
        self.assertEqual([r['branch'] for r in result['trace']],['no_release','no_release','submit','cooldown'])
        self.assertEqual(result['trace'][2]['release_state_after']['release_signal'],1)
        self.assertEqual(result['trace'][3]['release_state_after']['release_signal'],0)
        document['frames'][0]['release_signal']=1
        with self.assertRaisesRegex(ValueError,'not both'): run(document)

    def cooked_scenario(self):
        path=Path(__file__).resolve().parents[1]/'engine/examples/snow_cooker_jump_input.json'
        return json.loads(path.read_text())

    def test_cooker_delays_release_until_zero_and_preserves_spin(self):
        document=self.cooked_scenario(); original=deepcopy(document)
        result=run(document); rows=result['trace']
        self.assertEqual(document,original)
        self.assertEqual([r['cooker']['value'] for r in rows],[.25,.5,.25,0,0])
        self.assertEqual([r['branch'] for r in rows],
                         ['no_release','no_release','no_release','submit','cooldown'])
        self.assertEqual([r['cooker']['direction'] for r in rows],
                         ['ToZero','ToOne','ToZero','ToZero','ToZero'])
        self.assertEqual(rows[3]['release_state_after']['release_signal'],1)
        self.assertEqual(rows[4]['applications'],[])
        for name in document['bodies']:
            self.assertEqual(result['final_bodies'][name]['angular'],tuple(document['bodies'][name]['angular']))
            self.assertGreater(result['final_bodies'][name]['linear'][2],0)

    def test_cooker_clock_is_separate_from_release_clocks(self):
        document=self.cooked_scenario()
        document['frames'][2]['cooker_dt']=.02
        rows=run(document)['trace']
        self.assertEqual(rows[2]['cooker']['value'],0)
        self.assertEqual(rows[2]['branch'],'submit')
        self.assertEqual(rows[2]['release_state_after']['rate'],-25)
        self.assertAlmostEqual(rows[2]['release_state_after']['elapsed'],.01)

    def test_cooker_rejects_missing_provenance_and_ambiguous_inputs(self):
        for alteration, message in [
            (lambda d:d.pop('release_state'),'requires release_state'),
            (lambda d:d['frames'][0].update(cooked=0),'not both'),
            (lambda d:d['cooker']['decay'].pop('provenance'),'decay samples'),
            (lambda d:d['frames'][0].update(cooker_dt=0),'Positive cooker_dt'),
        ]:
            document=self.cooked_scenario(); alteration(document)
            with self.assertRaisesRegex(ValueError,message): run(document)

    def test_reconstructed_decay_changes_release_timing(self):
        path=Path(__file__).resolve().parents[1]/'engine/examples/snow_reconstructed_cooker_jump_input.json'
        document=json.loads(path.read_text()); result=run(document)
        rows=result['trace']
        self.assertEqual([r['branch'] for r in rows],
                         ['no_release']*4+['submit','cooldown'])
        self.assertGreater(rows[3]['cooker']['value'],0)
        self.assertEqual(rows[4]['cooker']['value'],0)
        self.assertEqual(result['decay_configuration'],document['cooker']['decay'])
        document['cooker']['decay']['samples']=[1]*257
        with self.assertRaisesRegex(ValueError,'only mode'): run(document)
