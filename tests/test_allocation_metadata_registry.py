import unittest
from engine.allocation_metadata_registry import register_metadata, select_default_metadata


class MetadataRegistryTests(unittest.TestCase):
    def services(self, events):
        return dict(lock=lambda _:events.append('lock'),unlock=lambda _:events.append('unlock'),
            notify_object=lambda target,event,record:events.append(('object',target,event,record['index'])),
            notify_function=lambda event,record,context,target:events.append(('function',target,event,context,record['index'])))

    def test_first_available_slot_and_post_unlock_notifications(self):
        registry=dict(entries=[object()]*127,default=255,observers=[
            dict(object_style=True,target='object',context=None),
            dict(object_style=False,target='function',context='context')])
        registry['entries'][126]=None;record=dict(index=255);events=[]
        self.assertTrue(register_metadata(registry,record,**self.services(events)))
        self.assertIs(registry['entries'][126],record)
        self.assertEqual(events,['lock','unlock',('object','object',0,126),('function','function',0,'context',126)])

    def test_full_registry_sets_default_to_unassigned_after_failed_registration(self):
        registry=dict(entries=[object()]*127,default=4,observers=[]);record=dict(index=255)
        self.assertFalse(select_default_metadata(registry,record,**self.services([])))
        self.assertEqual(registry['default'],255)

    def test_existing_index_is_trusted_without_registry_membership_check(self):
        registry=dict(entries=[None]*127,default=255,observers=[]);events=[]
        self.assertTrue(select_default_metadata(registry,dict(index=200),**self.services(events)))
        self.assertEqual(registry['default'],200);self.assertEqual(events,[])
        self.assertTrue(all(x is None for x in registry['entries']))

    def test_appended_observer_runs_in_same_traversal(self):
        first=dict(object_style=True,target='first',context=None)
        registry=dict(entries=[None]*127,default=255,observers=[first]);record=dict(index=255)
        events=[];services=self.services(events)
        def notify(target,event,record):
            events.append(target)
            if target=='first':registry['observers'].append(dict(first,target='second'))
            else:record['index']=7
        services['notify_object']=notify
        self.assertTrue(select_default_metadata(registry,record,**services))
        self.assertEqual(events,['lock','unlock','first','second'])
        self.assertEqual(registry['default'],7)
        self.assertIs(registry['entries'][0],record)
