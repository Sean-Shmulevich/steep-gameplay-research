import struct
import unittest
from engine.pose_contact_pool import acquire_payload_slot


def pool():
    return dict(free_head=0,current_page=0,page_count=0,page_capacity=0,page_index=0,
                slot_index=0,slots_per_page=2,alignment=16,active_count=0,pages=[])


class ContactPoolTest(unittest.TestCase):
    def test_free_list_has_priority_and_keeps_payload_bytes(self):
        state=pool();state.update(free_head=100,current_page=2000,active_count=0xffffffff)
        data=bytearray(struct.pack('<Q',300)+b'X'*280)
        def forbidden(*args):raise AssertionError('Unexpected allocation')
        self.assertEqual(acquire_payload_slot(state,{100:data},allocate_page=forbidden,reserve_pages=forbidden),100)
        self.assertEqual(state['free_head'],300);self.assertEqual(state['active_count'],0)
        self.assertEqual(state['current_page'],2000);self.assertEqual(state['slot_index'],0)
        self.assertEqual(data,struct.pack('<Q',300)+b'X'*280)

    def test_page_boundary_and_subsequent_allocation(self):
        state=pool();requests=[]
        def allocate(size,alignment,tag):
            requests.append((size,alignment,tag));return 1000*len(requests)
        def reserve(s,n):s['pages'].extend([0]*(n-len(s['pages'])));s['page_capacity']=n
        values=[acquire_payload_slot(state,{},allocate_page=allocate,reserve_pages=reserve) for _ in range(3)]
        self.assertEqual(values,[1000,1288,2000])
        self.assertEqual(requests,[(576,16,44)]*2)
        self.assertEqual(state['pages'][:2],[1000,2000]);self.assertEqual(state['page_capacity'],8)
        self.assertEqual(state['active_count'],3)

    def test_existing_next_page_is_selected_without_allocation(self):
        state=pool();state.update(current_page=1000,page_count=2,page_capacity=2,
                                  pages=[1000,2000],slot_index=1)
        def forbidden(*args):raise AssertionError('Unexpected allocation')
        self.assertEqual(acquire_payload_slot(state,{},allocate_page=forbidden,reserve_pages=forbidden),1288)
        self.assertEqual((state['current_page'],state['page_index'],state['slot_index']),(2000,1,0))


class ContactBatchTest(unittest.TestCase):
    def test_freelist_links_are_consumed_before_owner_reset(self):
        from engine.pose_contact_pool import supply_payload_batch
        state=pool();state['free_head']=100
        first=bytearray(b'X'*288);second=bytearray(b'Y'*288)
        struct.pack_into('<Q',first,0,200);struct.pack_into('<Q',second,0,0)
        before={100:bytes(first),200:bytes(second)};payloads={100:first,200:second}
        def forbidden(*args):raise AssertionError('Unexpected allocation')
        self.assertEqual(supply_payload_batch(state,payloads,2,allocate_page=forbidden,
                                             reserve_pages=forbidden),[100,200])
        self.assertEqual(state['free_head'],0);self.assertEqual(state['active_count'],2)
        for identity in (100,200):
            expected=bytearray(before[identity]);expected[:8]=bytes(8)
            expected[0x110:0x114]=bytes(4);expected[0x114]|=1
            self.assertEqual(payloads[identity],expected)

    def test_zero_batch_does_not_acquire_or_initialize(self):
        from engine.pose_contact_pool import supply_payload_batch
        state=pool();before=state.copy()
        def forbidden(*args):raise AssertionError('Unexpected allocation')
        self.assertEqual(supply_payload_batch(state,{},0,allocate_page=forbidden,
                                             reserve_pages=forbidden),[])
        self.assertEqual(state,before)
