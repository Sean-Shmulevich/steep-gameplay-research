import struct
import unittest
from engine.pose_observers import dispatch_pose_observers


def rec(token,enabled=1):return struct.pack('<QB7s',token,enabled,b'padding')


class PoseObserverTests(unittest.TestCase):
    def test_append_and_disable_during_dispatch(self):
        registry=dict(count=2,slots=[rec(1),rec(2),rec(0)])
        state=dict(active=0,deferred_cleanup=0);seen=[]
        def invoke(token,body,value):
            seen.append((token,body,value,state['active']))
            if token==1:
                registry['slots'][1]=rec(2,0)
                registry['slots'][2]=rec(3);registry['count']=3
                state['deferred_cleanup']=1
        result=dispatch_pose_observers(77,2,get_registry=lambda:registry,thread_state=state,invoke=invoke)
        self.assertEqual(seen,[(1,77,2,1),(3,77,2,1)])
        self.assertEqual(result['removed_indices'],[1])
        self.assertEqual(registry,dict(count=2,slots=[rec(1),rec(3),rec(3)]))
        self.assertEqual(state,dict(active=0,deferred_cleanup=0))

    def test_replacement_resumes_at_next_index(self):
        original=dict(count=1,slots=[rec(1)])
        replacement=dict(count=3,slots=[rec(9),rec(10),rec(11)])
        holder=[original];seen=[];state=dict(active=0,deferred_cleanup=0)
        def invoke(token,body,value):
            seen.append(token);holder[0]=replacement
        dispatch_pose_observers(0,0,get_registry=lambda:holder[0],thread_state=state,invoke=invoke)
        self.assertEqual(seen,[1,10,11])

    def test_disabled_entries_remain_without_cleanup_request(self):
        registry=dict(count=2,slots=[rec(1,0),rec(2,0)])
        state=dict(active=0,deferred_cleanup=0)
        result=dispatch_pose_observers(0,0,get_registry=lambda:registry,thread_state=state,invoke=None)
        self.assertEqual(result,dict(called=[],removed_indices=[]))
        self.assertEqual(registry['count'],2)

    def test_register_duplicates_and_remove_first_only(self):
        from engine.pose_observers import register_pose_observer, unregister_pose_observer
        registry=dict(count=0,capacity=0,slots=[]);growth=[]
        def grow(r,n):
            growth.append(n);r['slots'].extend([bytes(16)]*(n-len(r['slots'])));r['capacity']=n
        for _ in range(2):register_pose_observer(registry,9,padding=b'padding',grow=grow)
        self.assertEqual(growth,[8])
        state=dict(active=1,deferred_cleanup=0)
        for _ in range(2):self.assertEqual(unregister_pose_observer(registry,9,thread_state=state),0)
        self.assertEqual(registry['count'],2)
        self.assertEqual(registry['slots'][1][8],1)
        dispatch_pose_observers(0,2,get_registry=lambda:registry,thread_state=state,invoke=lambda *a:None)
        self.assertEqual(registry['count'],1)
        self.assertEqual(registry['slots'][0],rec(9))

    def test_missing_membership_guard_and_immediate_compaction(self):
        from engine.pose_observers import unregister_pose_observer
        registry=dict(count=3,slots=[rec(1),rec(2),rec(3)])
        state=dict(active=0,deferred_cleanup=0)
        self.assertEqual(unregister_pose_observer(registry,2,thread_state=state),1)
        self.assertEqual(registry,dict(count=2,slots=[rec(1),rec(3),rec(3)]))
        with self.assertRaises(ValueError):unregister_pose_observer(registry,77,thread_state=state)
        self.assertEqual(registry['count'],2)
