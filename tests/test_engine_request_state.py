import copy
import json
import unittest

from engine import request_state as r


class RequestStateTests(unittest.TestCase):
    def test_submit_only_unscheduled_and_credit_gate_is_not_checked(self):
        for state in (r.SCHEDULED, r.DONE):
            job = r.new_job(state=state, requested=3)
            self.assertEqual(r.submit(job), [])
            self.assertEqual(job['requested'], 3)
        job = r.new_job(credit_gate=True, credits=0)
        self.assertEqual(r.submit(job), [{'kind': 'invoke_begin', 'source': 'submit'}])
        self.assertEqual(job['requested'], 1)
        self.assertFalse(job['deferred'])
        self.assertEqual(job['started'], 0)  # explicit call boundary
        r.begin_ordinary(job)
        self.assertEqual(job['started'], 1)

    def test_submit_held_advances_request_without_begin(self):
        job = r.new_job(holds=2)
        self.assertEqual(r.submit(job), [])
        self.assertEqual(job['requested'], 1)

    def test_begin_local_gate_is_scheduled_not_requested_inequality(self):
        job = r.new_job(state=r.SCHEDULED, requested=3, started=1)
        self.assertEqual(r.begin_ordinary(job), [])
        self.assertEqual(job['started'], 1)
        job = r.new_job(state=r.DONE, requested=3, started=3, holds=2)
        effects = r.begin_ordinary(job)
        self.assertEqual(len(effects), 2)
        self.assertEqual(job['state'], r.DONE)  # no guessed queue/finalizer

    def test_two_predecessors_only_zero_to_one_advances_request(self):
        jobs = {'join': r.new_job()}
        first, second = r.new_dependency_list(['join']), r.new_dependency_list(['join'])
        r.activate(first, jobs)
        r.activate(second, jobs)
        self.assertEqual(jobs['join']['holds'], 2)
        self.assertEqual(jobs['join']['requested'], 1)
        self.assertEqual(r.release_normal(first, jobs), [])
        self.assertEqual(r.release_normal(second, jobs)[0]['kind'], 'invoke_begin')
        r.begin_ordinary(jobs['join'])
        self.assertEqual(jobs['join']['started'], 1)

    def test_duplicate_activation_and_forced_walk_do_not_add_holds(self):
        jobs = {'b': r.new_job()}
        dependencies = r.new_dependency_list(['b'])
        r.activate(dependencies, jobs)
        before = copy.deepcopy(jobs)
        self.assertEqual(r.activate(dependencies, jobs), [])
        effects = r.activate(dependencies, jobs, recurse=True)
        self.assertEqual(effects, [{'kind': 'invoke_activation', 'job': 'b', 'recurse': False}])
        self.assertEqual(jobs, before)

    def test_last_hold_with_already_started_request_does_not_begin(self):
        job = r.new_job(holds=1, requested=4, started=4, credit_gate=True)
        self.assertEqual(r.release_one_dependency(job), [])
        self.assertEqual(job['holds'], 0)
        self.assertFalse(job['deferred'])

    def test_credit_defer_and_credit_recipient_wakeup(self):
        job = r.new_job(holds=1, requested=2, credit_gate=True)
        self.assertEqual(r.release_one_dependency(job)[0]['kind'], 'begin_deferred')
        self.assertTrue(job['deferred'])
        self.assertEqual(job['started'], 0)
        effects = r.release_one_credit(job)
        self.assertEqual(effects, [{'kind': 'invoke_begin', 'source': 'credit_recipient'}])
        self.assertFalse(job['deferred'])
        self.assertEqual(job['credits'], 0)
        r.begin_ordinary(job)
        self.assertEqual(job['started'], 2)

    def test_normal_positive_credit_does_not_clear_prior_deferred_flag(self):
        job = r.new_job(holds=1, requested=1, credit_gate=True, credits=2, deferred=True)
        self.assertEqual(r.release_one_dependency(job)[0]['kind'], 'invoke_begin')
        self.assertEqual(job['credits'], 1)
        self.assertTrue(job['deferred'])

    def test_credit_wakeup_uses_postincrement_positive_and_all_other_gates(self):
        job = r.new_job(requested=1, credits=-1, deferred=True)
        self.assertEqual(r.release_one_credit(job), [])
        self.assertEqual(job['credits'], 0)
        self.assertEqual(r.release_one_credit(job)[0]['kind'], 'invoke_begin')
        for kw in ({'holds': 1, 'deferred': True}, {'deferred': False}, {'started': 1, 'deferred': True}):
            job = r.new_job(requested=1, **kw)
            self.assertEqual(r.release_one_credit(job), [])
            self.assertEqual(job['credits'], 1)

    def test_inactive_release_does_not_grant_credit_or_underflow(self):
        jobs = {'b': r.new_job(credits=0)}
        dependencies = r.new_dependency_list(['b'], ['b'])
        self.assertEqual(r.release_normal(dependencies, jobs), [])
        self.assertEqual(jobs['b']['credits'], 0)
        r.activate(dependencies, jobs)
        r.release_normal(dependencies, jobs)
        before = copy.deepcopy(jobs)
        self.assertEqual(r.release_normal(dependencies, jobs), [])
        self.assertEqual(jobs, before)

    def test_overlapping_credit_recipient_observes_defer_from_hold_release(self):
        jobs = {'b': r.new_job(credit_gate=True)}
        dependencies = r.new_dependency_list(['b'], ['b'])
        r.activate(dependencies, jobs)
        effects = r.release_normal(dependencies, jobs)
        self.assertEqual([e['kind'] for e in effects], ['begin_deferred', 'invoke_begin'])
        self.assertFalse(jobs['b']['deferred'])
        self.assertFalse(dependencies['active'])

    def test_checkpoint_equivalent_reducer_continuation(self):
        jobs = {'b': r.new_job(credit_gate=True)}
        dependencies = r.new_dependency_list(['b'])
        r.activate(dependencies, jobs)
        restored_jobs, restored_dependencies = json.loads(json.dumps([jobs, dependencies]))
        self.assertEqual(r.release_normal(dependencies, jobs), r.release_normal(restored_dependencies, restored_jobs))
        self.assertEqual(r.release_one_credit(jobs['b']), r.release_one_credit(restored_jobs['b']))
        self.assertEqual(jobs, restored_jobs)

    def test_underflow_transaction_and_alias_rejection(self):
        jobs = {'a': r.new_job(holds=1), 'b': r.new_job()}
        dependencies = r.new_dependency_list(['a', 'b'])
        dependencies['active'] = True
        before = copy.deepcopy((dependencies, jobs))
        with self.assertRaises(ValueError):
            r.release_normal(dependencies, jobs)
        self.assertEqual((dependencies, jobs), before)
        shared = r.new_job()
        with self.assertRaises(ValueError):
            r.activate(r.new_dependency_list(['a', 'b']), {'a': shared, 'b': shared})
        self.assertEqual(shared['holds'], 0)

    def test_repeated_same_id_is_not_silently_deduplicated(self):
        jobs = {'a': r.new_job()}
        dependencies = r.new_dependency_list(['a', 'a'])
        r.activate(dependencies, jobs)
        self.assertEqual(jobs['a']['holds'], 2)
        self.assertEqual(jobs['a']['requested'], 1)
        self.assertEqual(len(r.release_normal(dependencies, jobs)), 1)


if __name__ == '__main__':
    unittest.main()
