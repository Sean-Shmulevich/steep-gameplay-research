import json
from pathlib import Path
import unittest
from reference.animation_work_application import update_context_free_work, update_context_work
from reference.animation_evaluator import finish_work_update


class WorkCycleTests(unittest.TestCase):
    def test_connected_original_instruction_receipt(self):
        receipt=json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/work_cycle_validation.json').read_text())
        final_actions=set()
        for sample in receipt['samples']:
            seeds=iter(sample['rsqrt_seeds']);calls=iter(sample['math_services'])
            def trig(name,x):
                item=next(calls)
                self.assertEqual((name,x),(item['name'],item['input']))
                return item['output']
            update=update_context_free_work(**sample['inputs'],
                reciprocal_sqrt=lambda _:next(seeds),acos=lambda x:trig('acos',x),
                sin=lambda x:trig('sin',x))
            self.assertEqual(json.loads(json.dumps(update)),sample['update'])
            args=sample['inputs']
            final=finish_work_update(update,sample['prior_work'],args['indices'],
                args['parent_position'],args['parent_rotation'],args['direct'],
                lambda _:None,lambda _:next(seeds))
            self.assertEqual(json.loads(json.dumps(final)),sample['final'])
            self.assertEqual(list(seeds),[]);self.assertEqual(list(calls),[])
            final_actions.add(final['action'])
        self.assertEqual(final_actions,{'no_handoff','cleared','replaced'})
    def test_context_switching_original_instruction_receipt(self):
        receipt=json.loads((Path(__file__).resolve().parents[1] /
            'native/snow_host/context_cycle_validation.json').read_text())
        final_actions=set()
        for sample in receipt['samples']:
            seeds=iter(sample['rsqrt_seeds']);calls=iter(sample['math_services'])
            def trig(name,x):
                item=next(calls)
                self.assertEqual((name,x),(item['name'],item['input']))
                return item['output']
            update=update_context_work(**sample['inputs'],
                reciprocal_sqrt=lambda _:next(seeds),acos=lambda x:trig('acos',x),
                sin=lambda x:trig('sin',x))
            self.assertEqual(json.loads(json.dumps(update)),sample['update'])
            args=sample['inputs']
            final=finish_work_update(update,sample['prior_work'],args['indices'],
                args['parent_position'],args['parent_rotation'],args['direct'],
                lambda _:sample['replacement_context'],lambda _:next(seeds))
            self.assertEqual(json.loads(json.dumps(final)),sample['final'])
            self.assertEqual(list(seeds),[]);self.assertEqual(list(calls),[])
            final_actions.add(final['action'])
        self.assertEqual(final_actions,{'no_handoff','cleared','replaced'})
