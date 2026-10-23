import unittest
from engine.command_phase import correlate_command_phases

DOMAIN = dict(session_id='one-process-capture', clock_id='qpc', ticks_per_second=10000000)


def interval(start, end, thread=7, result=101):
    return dict(entry_tick=start, exit_tick=end, thread=thread, result=result)


def correlate(commands, phases, **kwargs):
    return correlate_command_phases(commands, phases, command_domain=DOMAIN,
                                    phase_domain=DOMAIN, **kwargs)


class CommandPhaseTests(unittest.TestCase):
    def test_repeated_request_can_execute_on_different_threads(self):
        report = correlate([interval(2, 3), interval(12, 13, 8)],
                           [interval(10, 15, 8), interval(0, 5)])
        self.assertEqual([m['phase_indexes'] for m in report['matches']], [[1], [0]])
        self.assertEqual([m['request_id'] for m in report['matches']], [101, 101])
        self.assertFalse(report['native_phase_proved'])
        self.assertFalse(report['call_ancestry_proved'])

    def test_other_thread_overlap_cannot_assign_phase(self):
        match = correlate([interval(2, 3)], [interval(0, 5, 8)])['matches'][0]
        self.assertEqual(match['status'], 'not_matched')
        self.assertEqual(match['other_thread_enclosing_count'], 1)

    def test_nested_and_duplicate_phases_remain_ambiguous(self):
        for phases in ([interval(0, 10), interval(1, 9)],
                       [interval(0, 10), interval(0, 10)]):
            match = correlate([interval(2, 3)], phases)['matches'][0]
            self.assertEqual(match['status'], 'ambiguous_containment')
            self.assertEqual(match['phase_indexes'], [0, 1])

    def test_missing_phase_and_partial_overlap_are_not_nearest_matches(self):
        for phases in ([], [interval(0, 2)], [interval(3, 5)]):
            report = correlate([interval(1, 4)], phases, phase_dropped=1)
            self.assertEqual(report['matches'][0]['status'], 'not_matched')
            self.assertTrue(report['capture_loss_observed'])

    def test_clock_resolution_ties_preserve_ambiguity(self):
        report = correlate([interval(5, 5)], [interval(0, 5), interval(5, 10)])
        self.assertEqual(report['matches'][0]['status'], 'ambiguous_containment')

    def test_capture_domains_must_match(self):
        for key, value in [('session_id', 'different-process'), ('clock_id', 'wall'),
                           ('ticks_per_second', 1)]:
            with self.assertRaises(ValueError):
                correlate_command_phases([], [], command_domain=DOMAIN,
                                         phase_domain={**DOMAIN, key: value})

    def test_invalid_provenance_and_intervals_refuse(self):
        for domain in ({}, {**DOMAIN, 'ticks_per_second': True}, {**DOMAIN, 'session_id': ''}):
            with self.assertRaises(ValueError):
                correlate_command_phases([], [], command_domain=domain, phase_domain=domain)
        for record in (interval(4, 3), interval(True, 3), interval(0, 2, result=0), {}):
            with self.assertRaises(ValueError):
                correlate([record], [])
        with self.assertRaises(ValueError):
            correlate([], [], command_dropped=-1)

    def test_empty_capture_is_not_completion(self):
        report = correlate([], [interval(0, 10)])
        self.assertEqual(report['matches'], [])
        self.assertFalse(report['admission_proved'])
        self.assertFalse(report['lifetime_or_unload_proved'])
