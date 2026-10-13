import copy
import json
import unittest

from engine.jobs import JobExecutor


def registry(callback, version='1'):
    return {'work': {'version': version, 'callback': callback}}


class JobTests(unittest.TestCase):
    def test_claim_is_not_completion_and_declared_order(self):
        definitions = [{'id': 'first', 'handler': 'work'},
                       {'id': 'dependent', 'handler': 'work', 'depends_on': ['first']},
                       {'id': 'independent', 'handler': 'work'}]
        executor = JobExecutor(definitions, registry(lambda ctx: ctx.append('called')))
        context = []
        self.assertEqual(executor.ready(), ['first', 'independent'])
        self.assertEqual(executor.claim(), 'first')
        self.assertEqual(context, [])
        self.assertEqual(executor.ready(), ['independent'])
        self.assertFalse(executor.drained())
        executor.execute('first', context)
        self.assertEqual(context, ['called'])
        self.assertEqual(executor.ready(), ['dependent', 'independent'])
        self.assertEqual([row['job'] for row in executor.run_ready(context)], ['dependent', 'independent'])

    def test_delayed_claim_retains_callback_despite_external_registry_change(self):
        handlers = registry(lambda ctx: 'old')
        executor = JobExecutor([{'id': 'a', 'handler': 'work'}], handlers)
        executor.claim('a')
        handlers['work']['callback'] = lambda ctx: 'new'
        self.assertEqual(executor.execute('a'), 'old')
        self.assertEqual(executor.snapshot()['jobs']['a']['claimed_handler']['version'], '1')

    def test_modifications_rejected_until_claim_drains(self):
        executor = JobExecutor([{'id': 'a', 'handler': 'work'}], registry(lambda ctx: 1))
        executor.claim()
        for call in (lambda: executor.reset(), lambda: executor.remove_job('a'),
                     lambda: executor.replace_handler('work', lambda ctx: 2, '2')):
            with self.assertRaises(RuntimeError):
                call()
        executor.execute('a')
        executor.replace_handler('work', lambda ctx: 2, '2')
        executor.reset()
        self.assertEqual(executor.run_ready()[0]['result'], 2)
        self.assertEqual(executor.epoch, 1)

    def test_running_is_inspectable_and_not_safe_to_modify(self):
        observed = []
        def callback(ctx):
            observed.append(executor.snapshot()['jobs']['a']['stage'])
            with self.assertRaises(RuntimeError):
                executor.replace_handler('work', lambda ctx: 2, '2')
            return 1
        executor = JobExecutor([{'id': 'a', 'handler': 'work'}], registry(callback))
        executor.run_ready()
        self.assertEqual(observed, ['running'])

    def test_failure_blocks_dependents_but_independent_can_execute(self):
        def fail(ctx):
            raise RuntimeError('expected fixture failure')
        definitions = [{'id': 'a', 'handler': 'work'},
                       {'id': 'b', 'handler': 'other', 'depends_on': ['a']},
                       {'id': 'c', 'handler': 'other'}]
        handlers = dict(registry(fail), other={'version': '1', 'callback': lambda ctx: 7})
        executor = JobExecutor(definitions, handlers)
        with self.assertRaises(RuntimeError):
            executor.run_ready()
        self.assertTrue(executor.drained())
        self.assertEqual(executor.ready(), ['c'])
        self.assertEqual(executor.run_ready(), [{'job': 'c', 'result': 7}])
        self.assertEqual(executor.snapshot()['jobs']['b']['stage'], 'pending')
        restored = JobExecutor.restore(executor.snapshot(), handlers)
        self.assertEqual(restored.snapshot(), executor.snapshot())

    def test_cycle_missing_dependency_and_version_rejection(self):
        bad = [[{'id': 'a', 'handler': 'work', 'depends_on': ['a']}],
               [{'id': 'a', 'handler': 'work', 'depends_on': ['b']}, {'id': 'b', 'handler': 'work', 'depends_on': ['a']}],
               [{'id': 'a', 'handler': 'work', 'depends_on': ['missing']}],
               [{'id': 'a', 'handler': 'work', 'handler_version': 'wrong'}]]
        for definitions in bad:
            with self.assertRaises(ValueError):
                JobExecutor(definitions, registry(lambda ctx: 1))

    def test_quiescent_checkpoint_continuation_and_registry_versions(self):
        definitions = [{'id': 'a', 'handler': 'work'}, {'id': 'b', 'handler': 'work', 'depends_on': ['a']}]
        handlers = registry(lambda ctx: {'value': ctx['value']})
        executor = JobExecutor(definitions, handlers)
        executor.run_ready({'value': 3}, max_jobs=1)
        snapshot = json.loads(json.dumps(executor.snapshot()))
        restored = JobExecutor.restore(snapshot, handlers)
        self.assertEqual(executor.run_ready({'value': 4}), restored.run_ready({'value': 4}))
        self.assertEqual(executor.snapshot(), restored.snapshot())
        with self.assertRaises(ValueError):
            JobExecutor.restore(snapshot, registry(lambda ctx: 1, version='2'))

    def test_claimed_snapshot_is_inspectable_but_not_restorable(self):
        executor = JobExecutor([{'id': 'a', 'handler': 'work'}], registry(lambda ctx: 1))
        executor.claim()
        snapshot = json.loads(json.dumps(executor.snapshot()))
        with self.assertRaises(ValueError):
            JobExecutor.restore(snapshot, registry(lambda ctx: 1))
        snapshot['drained'] = True
        with self.assertRaises(ValueError):
            JobExecutor.restore(snapshot, registry(lambda ctx: 1))

    def test_bounded_trace_and_result_not_aliased(self):
        value = {'items': [1]}
        executor = JobExecutor([{'id': 'a', 'handler': 'work'}], registry(lambda ctx: value), trace_capacity=2)
        result = executor.run_ready()[0]['result']
        value['items'].append(2)
        result['items'].append(3)
        snapshot = executor.snapshot()
        self.assertEqual(snapshot['jobs']['a']['result'], {'items': [1]})
        self.assertEqual(snapshot['trace']['attempted'], 3)
        self.assertEqual(snapshot['trace']['dropped'], 1)
        self.assertFalse(snapshot['trace']['complete'])

    def test_invalid_json_result_fails_and_does_not_release_dependents(self):
        executor = JobExecutor([{'id': 'a', 'handler': 'work'}], registry(lambda ctx: float('nan')))
        with self.assertRaises(ValueError):
            executor.run_ready()
        self.assertEqual(executor.snapshot()['jobs']['a']['stage'], 'failed')
        self.assertTrue(executor.drained())

    def test_remove_requires_no_dependents(self):
        executor = JobExecutor([{'id': 'a', 'handler': 'work'}, {'id': 'b', 'handler': 'work', 'depends_on': ['a']}], registry(lambda ctx: 1))
        before = copy.deepcopy(executor.snapshot())
        with self.assertRaises(ValueError):
            executor.remove_job('a')
        self.assertEqual(before, executor.snapshot())
        executor.remove_job('b')
        executor.remove_job('a')
        self.assertEqual(executor.ready(), [])


if __name__ == '__main__':
    unittest.main()
