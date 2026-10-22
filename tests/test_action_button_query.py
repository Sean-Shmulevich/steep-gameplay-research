import struct
import unittest
from engine.action_button_query import query_cached_button,special_button_state,special_timestamp_slot

class ButtonQueryTests(unittest.TestCase):
    def query(self,code=65,**changes):
        args=dict(owners=(),requested_owner=0,enabled=True,cutoff=10,
                  resolve_index=lambda _:3,timestamp=lambda _:11,key_byte=lambda _:128,
                  special_timestamp=lambda _:11,special_value=lambda _:True)
        args.update(changes);return query_cached_button(code,**args)
    def test_owner_and_strict_timestamp_gate(self):
        self.assertTrue(self.query(owners=(123,0)))
        self.assertFalse(self.query(owners=(0,123)))
        self.assertFalse(self.query(timestamp=lambda _:10))
        self.assertFalse(self.query(enabled=False))
    def test_lookup_is_repeated_and_sentinel_reads_preceding_slot(self):
        calls=[];indices=iter((3,-1))
        def resolve(_):calls.append('lookup');return next(indices)
        self.assertFalse(self.query(resolve_index=resolve));self.assertEqual(calls,['lookup','lookup'])
        calls=[]
        def timestamp(i):calls.append(i);return 11
        self.assertFalse(self.query(65535,resolve_index=lambda _:-1,timestamp=timestamp))
        self.assertEqual(calls,[-1])
    def test_special_packet_sign_swap_and_slots(self):
        packet=bytearray(20);packet[12]=128;packet[13]=1;packet[19]=128
        self.assertTrue(special_button_state(240,bytes(packet),swapped=False))
        self.assertFalse(special_button_state(240,bytes(packet),swapped=True))
        self.assertTrue(special_button_state(249,bytes(packet),swapped=False))
        struct.pack_into('<i',packet,8,-1)
        self.assertTrue(special_button_state(244,bytes(packet),swapped=False))
        self.assertFalse(special_button_state(243,bytes(packet),swapped=False))
        self.assertEqual(special_timestamp_slot(243,False),8)
        self.assertEqual(special_timestamp_slot(240,True),1)

    def test_owner_release_sets_cutoff_only_for_top(self):
        from engine.action_button_query import release_button_owner
        r=release_button_owner((1,2,1),1,cutoff=5,current_timestamp=11)
        self.assertEqual(r,dict(owners=(1,2),cutoff=11,removed_index=2))
        r=release_button_owner((1,2,3),2,cutoff=5,current_timestamp=11)
        self.assertEqual(r,dict(owners=(1,3),cutoff=5,removed_index=1))
        self.assertIsNone(release_button_owner((),1,cutoff=5,current_timestamp=11)['removed_index'])

    def test_release_suppresses_old_cached_press(self):
        from engine.action_button_query import release_button_owner
        released=release_button_owner((0,99),99,cutoff=0,current_timestamp=11)
        self.assertFalse(self.query(owners=released['owners'],cutoff=released['cutoff'],timestamp=lambda _:11))
        self.assertTrue(self.query(owners=released['owners'],cutoff=released['cutoff'],timestamp=lambda _:12))
