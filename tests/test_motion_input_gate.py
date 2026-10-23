import json
from pathlib import Path
import unittest
from engine.motion_input_gate import resolve_motion_input_gate

class MotionInputGateTests(unittest.TestCase):
    def test_original_instruction_matrix(self):
        receipt=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/motion_gate_validation.json').read_text())
        self.assertTrue(receipt['passed'])
        self.assertEqual(len(receipt['rows']),192)
        for row in receipt['rows']:
            with self.subTest(row=row):
                flags=dict(active=bool(row['active']), controller_blocked=bool(row['controller_blocked']),
                           motion_enabled=bool(row['motion_enabled']),skip_ingestion=bool(row['initial_skip']))
                def prepare():
                    override=row['synthetic_preparation_skip']
                    if override is not None:flags['skip_ingestion']=bool(override)
                result=resolve_motion_input_gate(flags.__getitem__,lambda:bool(row['predicate_a']),
                    lambda:bool(row['predicate_b']),prepare,prepare)
                self.assertEqual(result.ingestion_enabled,row['ingested'])

    def test_preparation_changes_skip_before_it_is_read(self):
        flags=dict(active=True,controller_blocked=False,motion_enabled=True,skip_ingestion=True)
        def forbidden():raise AssertionError('predicate B must be skipped')
        result=resolve_motion_input_gate(flags.__getitem__,lambda:True,forbidden,
            lambda:flags.update(skip_ingestion=False),forbidden)
        self.assertTrue(result.ingestion_enabled)
        self.assertEqual(result.events,('active','controller_blocked','motion_enabled',
                                       'predicate_a','prepare_a','skip_ingestion'))

    def test_outer_gate_stops_before_controller_resolution(self):
        reads=[]
        def read(name):
            reads.append(name)
            if name!='active':raise AssertionError('unexpected later read')
            return False
        def forbidden():raise AssertionError('unexpected helper')
        result=resolve_motion_input_gate(read,forbidden,forbidden,forbidden,forbidden)
        self.assertFalse(result.ingestion_enabled)
        self.assertEqual(reads,['active'])
        self.assertEqual(result.stopped_at,'active')

    def test_unresolved_value_is_not_silently_false(self):
        with self.assertRaises(ValueError):
            resolve_motion_input_gate(lambda _:None,lambda:False,lambda:False,lambda:None,lambda:None)

    def test_gate_drives_batch_without_reads_when_preparation_suppresses(self):
        from engine.motion_input_batch import prepare_motion_input_batch
        from engine.motion_input_ingestion import ingest_motion_prefix
        zero=bytes(16)
        previous=ingest_motion_prefix((zero,)*4,flip_x=False,counts=(0,0),smoothed=(zero,zero),alpha=.5)
        for suppress in (False,True):
            flags=dict(active=True,controller_blocked=False,motion_enabled=True,skip_ingestion=False)
            gate=resolve_motion_input_gate(flags.__getitem__,lambda:False,lambda:True,
                lambda:None,lambda:flags.update(skip_ingestion=suppress))
            reads=[]
            def read(action):reads.append(action);return zero
            batch=prepare_motion_input_batch(previous,[dict(elapsed_dt=.01,derivative_dt=.01)]*3,
                ingestion_enabled=gate.ingestion_enabled,read_action=read,
                alternate_enabled=False,actor_predicate=False,flip_x=False,alpha=.5)
            samples=[]
            batch.execute(lambda i,e,d,m:samples.append(m))
            self.assertEqual(reads,[] if suppress else [0x76,0x77,0x76,0x77])
            self.assertEqual(len(samples),3)
            self.assertTrue(all(m is batch.motion for m in samples))

    def test_concrete_mode_predicates_select_only_their_preparation(self):
        from engine.motion_input_gate import preparation_mode_matches
        for mode,expected in ((0,None),(5,'prepare_b'),(9,'prepare_a'),(0xffffffff,None)):
            calls=[]
            flags=dict(active=True,controller_blocked=False,motion_enabled=True,skip_ingestion=False)
            gate=resolve_motion_input_gate(flags.__getitem__,
                lambda:preparation_mode_matches(mode,'a'),
                lambda:preparation_mode_matches(mode,'b'),
                lambda:calls.append('prepare_a'),lambda:calls.append('prepare_b'))
            self.assertTrue(gate.ingestion_enabled)
            self.assertEqual(gate.preparation,expected)
            self.assertEqual(calls,[] if expected is None else [expected])
        for invalid in (-1,1<<32,True,None):
            with self.assertRaises(ValueError):preparation_mode_matches(invalid,'a')
