import copy
import unittest
from engine.phase_input_observation import correlate_input_reports


class InputReportTests(unittest.TestCase):
    def setUp(self):
        self.domain = dict(session_id='fixture', clock_id='qpc', ticks_per_second=1000)
        self.events = [dict(kind='key_delivery', key_up=up, api_reported_sent=1,
            qpc_ticks=tick, qpc_frequency=1000, scan_raw=17, pid=9,
            creation_filetime='fixture-creation', hwnd='fixture-window', mode='sendinput')
            for up, tick in ((False, 100), (True, 200))]

    def run_case(self, receipts=(), events=None, other_domain=None):
        return correlate_input_reports(receipts, self.events if events is None else events,
            request_domain=self.domain, input_domain=self.domain if other_domain is None else other_domain)

    def test_boundaries_and_repeated_ids_are_preserved(self):
        report = self.run_case([dict(id=1, outcome=1, entry=a, exit=b) for a,b in
            [(10,90),(110,190),(210,220),(90,100),(100,101),(199,200),(90,210)]])
        self.assertEqual([v['index'] for v in report['groups']['overlaps_report_boundary']], [3,4,5,6])
        self.assertEqual(len(report['groups']['inside_reported_hold']), 1)
        self.assertTrue(report['coverage_on_both_sides'])
        self.assertFalse(report['ingestion_proved'])
        self.assertFalse(report['exact_input_latency_proved'])

    def test_reject_mismatched_or_failed_delivery(self):
        for key,value in [('pid',8),('scan_raw',30),('creation_filetime','different'),
                          ('api_reported_sent',0),('qpc_frequency',2000),('key_up',False),
                          ('qpc_ticks',99)]:
            with self.subTest(key=key):
                events=copy.deepcopy(self.events);events[1][key]=value
                with self.assertRaises(ValueError): self.run_case(events=events)
        with self.assertRaises(ValueError):self.run_case(events=self.events[:1])

    def test_domain_and_interval_validation(self):
        for key,value in [('session_id','different'),('clock_id','different'),('ticks_per_second',True)]:
            domain=dict(self.domain);domain[key]=value
            with self.assertRaises(ValueError):self.run_case(other_domain=domain)
        for receipt in [dict(id=0,outcome=1,entry=1,exit=2),dict(id=1,outcome=1,entry=2,exit=1),dict(id=1,outcome=1,entry=True,exit=2),dict(id=1,outcome=2,entry=0,exit=0)]:
            with self.assertRaises(ValueError):self.run_case([receipt])
        self.assertFalse(self.run_case()['coverage_on_both_sides'])
