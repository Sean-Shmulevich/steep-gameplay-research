import unittest
from engine.providers import initialize,resolve

class ProviderTests(unittest.TestCase):
    def test_same_provider_new_key_retains_backing(self):
        provider=object();handle={}
        initialize(handle,7,lambda key:provider)
        old=handle['backing']
        events=initialize(handle,8,lambda key:provider)
        self.assertIs(handle['backing'],old)
        self.assertEqual(handle['key'],8)
        self.assertEqual(events[-1],'backing_retained')
    def test_override_and_failed_allocation_drop_old_backing(self):
        handle={};first=object();second=object()
        initialize(handle,7,lambda key:first)
        seen=[]
        def allocation(provider):
            seen.append(handle['backing']);self.assertIs(provider,second)
            return None
        events=initialize(handle,8,lambda key:self.fail('override must skip callback'),override=second,allocate=allocation)
        self.assertEqual(seen,[None]);self.assertIsNone(handle['backing'])
        self.assertEqual(events[-1],'allocation_failed')
    def test_unavailable_equal_row_does_not_end_search(self):
        rows=[dict(key=1,scalar=2,flag=False,available=False,resource='bad'),dict(key=1,scalar=3,flag=True,available=True,resource='good')]
        outputs={};self.assertEqual(resolve(rows,1,outputs),'good')
        self.assertEqual(outputs,dict(scalar=3,flag=True))
    def test_failed_lookup_retains_last_matching_outputs(self):
        outputs={'scalar':9,'flag':True}
        self.assertIsNone(resolve([dict(key=1,scalar=2,flag=False,available=False)],1,outputs))
        self.assertEqual(outputs,dict(scalar=2,flag=False))
        self.assertIsNone(resolve([],1,outputs));self.assertEqual(outputs['scalar'],2)
