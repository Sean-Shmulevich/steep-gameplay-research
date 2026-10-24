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
