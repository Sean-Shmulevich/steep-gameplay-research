import json
from dataclasses import replace
import unittest

from engine.mixed_scheduler import MixedScheduler
from engine import request_state as r


def binding(callback):
    return {'version': 'synthetic-v1', 'callback': callback}


class MixedSchedulerTests(unittest.TestCase):
    def test_multiple_claims_empty_is_not_completion(self):
        seen = []
        model = MixedScheduler([
            {'id': 'range', 'kind': 'range', 'receivers': ['a', 'b'], 'max_concurrency': 2,
             'handler': 'body', 'successors': ['end']},
            {'id': 'end', 'kind': 'terminal'}], {'body': binding(lambda ctx, receiver: seen.append(receiver))})
        model.submit('range')
        first, second = model.reserve('range'), model.reserve('range')
        a, b = model.claim_range(first), model.claim_range(second)
        snap = model.snapshot()
        self.assertEqual(snap['jobs']['range']['remaining'], 0)
        self.assertEqual(snap['jobs']['range']['executions'], 2)
        self.assertEqual(snap['jobs']['range']['outstanding_dispatches'], 2)
        self.assertEqual(snap['jobs']['end']['terminal_begins'], 0)
        self.assertEqual(seen, [])
        with self.assertRaises(ValueError):
            model.finish_dispatch(first)
        with self.assertRaises(RuntimeError):
            model.prepare_range('range', ['replacement'])
        model.execute_range(first, a)
        model.finish_dispatch(first)
        snap = model.snapshot()
        self.assertEqual(snap['jobs']['range']['state'], r.DONE)
        self.assertEqual(snap['jobs']['range']['executions'], 1)
        self.assertEqual(snap['jobs']['end']['holds'], 1)
        self.assertEqual(snap['jobs']['end']['terminal_begins'], 0)
        model.execute_range(second, b)
        model.finish_dispatch(second)
        snap = model.snapshot()
        self.assertEqual(seen, ['b', 'a'])
        self.assertEqual(snap['jobs']['range']['state'], r.UNSCHEDULED)
        self.assertEqual(snap['jobs']['range']['outstanding_dispatches'], 0)
        self.assertEqual(snap['jobs']['end']['terminal_begins'], 1)
        finalization = [e for e in snap['trace']['records'] if e['kind'] == 'mixed_finalize_enter']
        self.assertEqual(finalization[0]['outstanding_dispatches'], 1)

    def test_callback_done_on_reservation_is_not_returned(self):
        seen = []
        model = MixedScheduler([{'id': 'root', 'kind': 'callback', 'handler': 'body', 'successors': ['end']},
                                {'id': 'end', 'kind': 'terminal'}], {'body': binding(lambda ctx, _: seen.append('ran'))})
        model.submit('root')
        token = model.reserve()
        snap = model.snapshot()
        self.assertEqual(snap['jobs']['root']['state'], r.DONE)
        self.assertEqual(snap['jobs']['root']['executions'], 1)
        self.assertEqual(snap['jobs']['end']['terminal_begins'], 0)
        self.assertEqual(seen, [])
        with self.assertRaises(ValueError):
            model.finish_dispatch(token)
        model.execute_callback(token)
        self.assertEqual(model.snapshot()['jobs']['end']['terminal_begins'], 0)
        model.finish_dispatch(token)
        self.assertEqual(model.snapshot()['jobs']['end']['terminal_begins'], 1)

    def test_mixed_reconvergence_executes_only_selected_branch(self):
        for selected in (True, False):
            seen = []
            defs = [{'id': 'branch', 'kind': 'conditional', 'condition': selected, 'successors': ['left'], 'secondary': ['right']},
                    {'id': 'left', 'kind': 'range', 'receivers': ['left'], 'handler': 'body', 'successors': ['join']},
                    {'id': 'right', 'kind': 'range', 'receivers': ['right'], 'handler': 'body', 'successors': ['join']},
                    {'id': 'join', 'kind': 'terminal'}]
            model = MixedScheduler(defs, {'body': binding(lambda ctx, receiver: seen.append(receiver))})
            model.activate('branch')
            self.assertEqual(model.snapshot()['jobs']['join']['holds'], 2)
            model.submit('branch')
            model.run_ready()
            snap = model.snapshot()
            self.assertEqual(seen, ['left' if selected else 'right'])
            self.assertEqual(snap['jobs']['join']['terminal_begins'], 1)
            self.assertEqual(snap['jobs']['branch']['started'], 0)
            unselected = snap['jobs']['right' if selected else 'left']
            self.assertEqual(unselected['requested'], 1)
            self.assertEqual(unselected['started'], 0)

    def test_conditional_activation_primary_recurses_before_secondary_holds(self):
        model = MixedScheduler([
            {'id': 'branch', 'kind': 'conditional', 'successors': ['left'], 'secondary': ['right']},
            {'id': 'left', 'kind': 'terminal', 'successors': ['child']},
            {'id': 'right', 'kind': 'terminal'}, {'id': 'child', 'kind': 'terminal'}])
        model.activate('branch')
        added = [e['job'] for e in model.snapshot()['trace']['records'] if e['kind'] == 'mixed_hold_added']
        self.assertEqual(added, ['left', 'child', 'right'])

    def test_normal_release_recurses_before_next_recipient(self):
        # First successor terminal adds an extra join hold while its outgoing
        # activation is already active, then releases it immediately. The trace
        # must show its whole begin before source visits the second successor.
        model = MixedScheduler([
            {'id': 'root', 'kind': 'callback', 'successors': ['terminal', 'second']},
            {'id': 'terminal', 'kind': 'terminal'}, {'id': 'second', 'kind': 'terminal'}])
        model.submit('root')
        model.run_ready()
        events = model.snapshot()['trace']['records']
        first_begin = next(i for i,e in enumerate(events) if e['kind'] == 'mixed_terminal_begin' and e['job'] == 'terminal')
        second_release = next(i for i,e in enumerate(events) if e['kind'] == 'mixed_normal_hold_released' and e['job'] == 'second')
        self.assertLess(first_begin, second_release)

    def test_two_requests_and_endframe_resubmission_overlap_bookkeeping(self):
        context = {'roots': 0, 'observed': []}
        def root(ctx, _):
            ctx['roots'] += 1
        def end(ctx, _):
            if ctx['roots'] < 2:
                before = model.snapshot()['jobs']['end']
                model.submit('root', context=ctx)
                after = model.snapshot()['jobs']['root']
                ctx['observed'].append((before['executions'], before['outstanding_dispatches'], before['state'], after['state']))
        model = MixedScheduler([{'id': 'root', 'kind': 'callback', 'handler': 'root', 'successors': ['end']},
                                {'id': 'end', 'kind': 'callback', 'handler': 'end'}],
                               {'root': binding(root), 'end': binding(end)})
        model.submit('root', context)
        self.assertEqual(model.run_ready(context), 4)
        self.assertEqual(context['roots'], 2)
        self.assertEqual(context['observed'], [(1, 1, r.DONE, r.SCHEDULED)])
        self.assertEqual(model.snapshot()['jobs']['end']['requested'], 2)
        self.assertEqual(model.snapshot()['jobs']['end']['started'], 2)

    def test_three_cycle_example_with_skipped_middle_route(self):
        from engine.examples.mixed_scheduler_probe import run_probe
        result = run_probe()
        self.assertEqual(result['completed_cycles'], [1, 2, 3])
        self.assertEqual([row['cycle'] for row in result['receiver_visits']], [1, 1, 3, 3])

    def test_early_worker_exit_does_not_finalize_positive_remaining(self):
        model = MixedScheduler([{'id': 'r', 'kind': 'range', 'receivers': [1, 2], 'successors': ['end']},
                                {'id': 'end', 'kind': 'terminal'}])
        model.submit('r')
        token = model.reserve()
        claimed = model.claim_range(token)
        model.execute_range(token, claimed)
        with self.assertRaises(ValueError):
            model.finish_dispatch(token)
        model.finish_dispatch(token, early_exit=True)
        snap = model.snapshot()
        self.assertEqual(snap['jobs']['r']['remaining'], 1)
        self.assertEqual(snap['jobs']['r']['state'], r.SCHEDULED)
        self.assertEqual(snap['jobs']['end']['terminal_begins'], 0)
        model.run_ready()
        self.assertEqual(model.snapshot()['jobs']['end']['terminal_begins'], 1)

    def test_range_claim_tail_arithmetic_and_reverse_visit(self):
        seen = []
        model = MixedScheduler([{'id': 'r', 'kind': 'range', 'receivers': list(range(10)),
                                 'chunk_size': 2, 'tail_threshold': 4, 'handler': 'body'}],
                               {'body': binding(lambda ctx, receiver: seen.append(receiver))})
        model.submit('r')
        model.run_ready()
        claims = [e['count'] for e in model.snapshot()['trace']['records'] if e['kind'] == 'mixed_range_claimed']
        self.assertEqual(claims, [2, 2, 2, 1, 1, 1, 1])
        self.assertEqual(seen, list(reversed(range(10))))

    def test_credit_defer_then_credit_recipient_starts_immediately(self):
        model = MixedScheduler([{'id': 'root', 'kind': 'callback', 'successors': ['r'], 'credit_recipients': ['r']},
                                {'id': 'r', 'kind': 'range', 'receivers': [1], 'credit_gate': True, 'credits': 0}])
        model.submit('root')
        model.run_ready()
        job = model.snapshot()['jobs']['r']
        self.assertEqual(job['started'], job['requested'])
        self.assertEqual(job['credits'], 0)
        self.assertFalse(job['deferred'])
        self.assertEqual(job['state'], r.UNSCHEDULED)

    def test_trace_drops_explicit_and_snapshot_has_no_live_tokens(self):
        model = MixedScheduler([{'id': 'r', 'kind': 'range', 'receivers': [1]}], trace_capacity=2)
        model.submit('r')
        token = model.reserve()
        model.claim_range(token)
        snap = model.snapshot()
        self.assertEqual(json.loads(json.dumps(snap)), snap)
        self.assertFalse(snap['trace']['complete'])
        self.assertGreater(snap['trace']['dropped'], 0)
        self.assertNotIn('scheduler_id', json.dumps(snap))

    def test_stale_tokens_and_cycles_rejected(self):
        with self.assertRaises(ValueError):
            MixedScheduler([{'id': 'x', 'kind': 'terminal', 'successors': ['x']}])
        model = MixedScheduler([{'id': 'r', 'kind': 'range', 'receivers': []}])
        model.submit('r')
        self.assertIsNone(model.reserve())
        other = MixedScheduler([{'id': 'c', 'kind': 'callback'}])
        other.submit('c')
        token = other.reserve()
        with self.assertRaises(ValueError):
            model.execute_callback(token)
        other.execute_callback(token)
        other.finish_dispatch(token)
        with self.assertRaises(ValueError):
            other.execute_callback(token)

    def test_forged_numeric_token_fields_do_not_mutate_or_strand_dispatch(self):
        model = MixedScheduler([{'id': 'r', 'kind': 'range', 'receivers': [1]}])
        model.submit('r')
        token = model.reserve()
        claimed = model.claim_range(token)
        before = model.snapshot()
        for bad in (replace(token, dispatch=float(token.dispatch)), replace(token, dispatch=False)):
            with self.assertRaises(ValueError):
                model.claim_range(bad)
            self.assertEqual(model.snapshot(), before)
        for field in ('dispatch', 'sequence', 'start', 'count'):
            for value in (float(getattr(claimed, field)), bool(getattr(claimed, field))):
                with self.assertRaises(ValueError):
                    model.execute_range(token, replace(claimed, **{field: value}))
                self.assertEqual(model.snapshot(), before)
        model.execute_range(token, claimed)
        model.finish_dispatch(token)
        self.assertEqual(model.snapshot()['jobs']['r']['executions'], 0)

    def test_callback_fault_is_fail_stop_not_native_unwind(self):
        def fail(ctx, receiver):
            raise ValueError('synthetic callback failure')
        model = MixedScheduler([{'id': 'c', 'kind': 'callback', 'handler': 'fail'}], {'fail': binding(fail)})
        model.submit('c')
        with self.assertRaises(ValueError):
            model.run_ready()
        snap = model.snapshot()
        self.assertEqual(snap['jobs']['c']['executions'], 1)
        self.assertIsNotNone(snap['fault'])
        with self.assertRaises(RuntimeError):
            model.submit('c')


if __name__ == '__main__':
    unittest.main()
