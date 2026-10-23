import unittest
from engine.allocation_metadata_removal import unregister_metadata, notify_metadata_observers
from engine.allocation_metadata_lookup import lookup_allocation_metadata


class MetadataRemovalTests(unittest.TestCase):
    def test_observers_see_cleared_entry_and_old_record_index(self):
        record=dict(index=3);registry=dict(entries=[None]*127,default=3,
            observers=[dict(object_style=True,target='object',context=None)])
        registry['entries'][3]=record;events=[]
        def notify(target,event,value):
            self.assertEqual((event,value['index'],registry['default']), (0,3,255))
            self.assertIsNone(registry['entries'][3])
            self.assertEqual(events,['lock','unlock'])
            value['index']=9
            return 0x80000000
        result=unregister_metadata(registry,record,lock=lambda _:events.append('lock'),
            unlock=lambda _:events.append('unlock'),notify_object=notify,
            notify_function=lambda *_:self.fail())
        self.assertEqual(result,0x80000000)
        self.assertEqual(record['index'],255)

    def test_slot_membership_is_not_checked_and_region_tag_is_unchanged(self):
        record=dict(index=2);registry=dict(entries=[None]*127,default=5,observers=[])
        registry['entries'][2]='different-record';region=bytes([2])
        unregister_metadata(registry,record,lock=lambda _:None,unlock=lambda _:None,
                            notify_object=lambda *_:self.fail(),notify_function=lambda *_:self.fail())
        self.assertEqual(registry['default'],5)
        self.assertEqual(region,bytes([2]))
        self.assertIsNone(lookup_allocation_metadata(0,read_region=lambda _:region,
            read_entry=lambda i:registry['entries'][i],default_index=lambda:self.fail()))

    def test_dynamic_notifications_combine_full_low32_results(self):
        observers=[dict(object_style=True,target='object',context=None)]
        def notify(*_):
            observers.append(dict(object_style=False,target='function',context=7))
            return 0x100000002
        result=notify_metadata_observers(observers,1,{},notify_object=notify,
            notify_function=lambda event,record,ctx,target:0x80000004)
        self.assertEqual(result,0x80000006)
