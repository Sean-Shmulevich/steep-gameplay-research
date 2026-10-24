import unittest
from engine.markup_motion_callback import notification_84


class MarkupMotionCallbackTests(unittest.TestCase):
    def test_both_edges_follow_identical_order_and_mutated_vector(self):
        for value in (0,1,255):
            calls=[]
            def mark(name,result):
                def service(*args):calls.append((name,args));return result
                return service
            def vector(actor,v):
                self.assertEqual(v,[0.0]*4);calls.append(('vector',(actor,)));v[:]=[1.,2.,3.,4.]
            result=notification_84(10,84,value,0xffffffff,
                available=mark('available',1),entity=mark('entity',20),
                actor_type=mark('type',30),lookup=mark('lookup',40),
                dispatch=mark('dispatch',0),vector_service=vector,accumulate=mark('accumulate',None))
            self.assertEqual(result,'services_completed')
            self.assertEqual([x[0] for x in calls],['available','entity','type','lookup','dispatch','vector','accumulate'])
            self.assertEqual(calls[-1][1],(40,[1.,2.,3.,4.]))

    def test_early_exits_use_low_byte_and_null_actor(self):
        def forbidden(*args):self.fail('unexpected service')
        for predicate,actor,result in [(256,99,'interface_unavailable'),(257,0,'actor_absent'),(1,None,'actor_absent')]:
            self.assertEqual(notification_84(10,84,1,0xffffffff,available=lambda c:predicate,
                entity=lambda c:20,actor_type=lambda:30,lookup=lambda e,t:actor,
                dispatch=forbidden,vector_service=forbidden,accumulate=forbidden),result)
