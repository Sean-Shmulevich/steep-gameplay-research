import json
from pathlib import Path
import unittest
from engine.animation_registry_construction import construct_supplied_target


class ConstructionTests(unittest.TestCase):
    def test_original_supplied_storage_chain(self):
        self.check_receipt('registry_construction_validation.json')

    def test_original_lock_adapter_chain(self):
        self.check_receipt('registry_lock_chain_validation.json')

    def check_receipt(self, filename):
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host' / filename).read_text())
        for sample in receipt['samples']:
            args=dict(sample['inputs']);word=args.pop('target_word')
            args['identity_to_target']={int(k):v for k,v in args['identity_to_target'].items()}
            observed=[]
            def callback(snapshot):
                observed.append(snapshot)
                return word
            result=construct_supplied_target(**args,constructor=callback)
            expected=dict(sample['callback_observation'],registry_lock_held=False)
            self.assertEqual(observed,[expected])
            self.assertEqual(result['callback_observation'],expected)
            self.assertEqual(json.loads(json.dumps(result['result'])),sample['result'])

    def test_callback_snapshot_cannot_mutate_registry(self):
        rows=[]
        def callback(snapshot):
            snapshot['pairs'].clear()
            return 0
        result=construct_supplied_target(pairs=rows,identity='i',target='t',
            constructor=callback,enabled=True,secondary_holder_present=False,
            secondary_target=None,target_to_identity={},identity_to_target={})
        self.assertEqual(rows,[])
        self.assertTrue(result['result']['registered'])
        self.assertEqual(result['callback_observation']['pairs'],[['i','t']])
