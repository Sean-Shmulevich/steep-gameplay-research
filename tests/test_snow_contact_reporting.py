import unittest
from engine.snow_contact_reporting import report_contact
from engine.snow_post_pending import summed_submissions


def state():
    return dict(records=[],max_a_squared=0,max_b_squared=0,max_a=[0]*4,max_b=[0]*4,sum_a=[0]*4,sum_b=[0]*4)


def record(**kw):
    r=dict(enabled=True,kind=1,identifier=42,a=[3,4,0,20],b=[0,0,2,-4],point=[1,2,3,1]);r.update(kw);return r


class ContactReportingTests(unittest.TestCase):
    def test_zero_gate_reports_without_submitting_impulse(self):
        r=record();s=state();out=report_contact(s,r,0)
        self.assertEqual(s['records'],[])
        self.assertEqual(out['records'][0]['magnitude'],5)
        self.assertEqual(out['sum_a'],[3,4,0,20])
        self.assertEqual(summed_submissions([r],0,1,.125),[])

    def test_tie_preserves_maximum_but_still_accumulates(self):
        s=report_contact(state(),record(),1)
        t=report_contact(s,record(a=[-3,-4,0,7]),1)
        self.assertEqual(t['max_a'],[3,4,0,20])
        self.assertEqual(t['sum_a'],[0,0,0,27])
        self.assertEqual(len(t['records']),2)

    def test_disabled_other_kind_negative_gate_skip(self):
        for r,g in [(record(enabled=False),1),(record(kind=2),1),(record(),-1)]:
            self.assertEqual(report_contact(state(),r,g),state())
