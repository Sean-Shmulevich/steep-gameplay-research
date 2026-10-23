import unittest
from engine.command_record_copy import copy_record
from engine.examples.command_attachment_probe import run_probe


def source():
    holder=dict(status=2)
    return dict(kind=3,holder_08=holder,holder_10=holder,payload_18_30=bytes(range(24)),
        invoker='callback',payload_38_60=bytes(range(40)),associated=dict(count=1))


class CommandCopyTests(unittest.TestCase):
    def test_copies_retain_attachment_until_last_discard_without_callback(self):
        result=run_probe(copies=3)
        self.assertEqual([s['references'] for s in result['samples']],[1,4,3,2,1,0])
        self.assertEqual(result['events'],['associated_destroy'])
        self.assertEqual(result['callback_invocations'],0)
        self.assertFalse(result['module_lifetime_proved'])

    def test_destination_padding_survives_and_old_reference_is_not_released(self):
        old=dict(count=8);destination=dict(padding='unchanged',associated=old)
        s=source();self.assertIs(copy_record(destination,s),destination)
        self.assertEqual(destination['padding'],'unchanged');self.assertEqual(old['count'],8)
        self.assertIs(destination['associated'],s['associated'])
        self.assertEqual(s['associated']['count'],2);self.assertEqual(s['holder_08']['status'],4)

    def test_self_copy_clears_attachment_without_decrementing_it(self):
        s=source();associated=s['associated'];copy_record(s,s)
        self.assertIsNone(s['associated']);self.assertEqual(associated['count'],1)
        self.assertEqual(s['holder_08']['status'],4)

    def test_uint32_increment_wrap_is_not_saturated(self):
        s=source();s['associated']['count']=0xffffffff;s['holder_08']['status']=0xffffffff
        copy_record({},s)
        self.assertEqual(s['associated']['count'],0);self.assertEqual(s['holder_08']['status'],1)
