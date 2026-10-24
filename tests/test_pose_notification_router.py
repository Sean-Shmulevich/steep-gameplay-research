import unittest
from engine.pose_notification_router import route_auxiliary_pose_notification


class NotificationRouterTests(unittest.TestCase):
    def test_only_event11_reads_nested_body_link(self):
        for event in (0,2,9,10,11,12,13,0xffffffff):
            seen=[]
            def read(body):seen.append(('read',body));return 99
            def service(code):return lambda manager,target:seen.append((code,manager,target))
            routed=route_auxiliary_pose_notification(7,event,manager=8,read_body_link=read,
                event10=service(10),event11=service(11),event12=service(12))
            expected=[] if event not in (10,11,12) else ( [('read',7),(11,8,99)] if event==11 else [(event,8,7)] )
            self.assertEqual(seen,expected)
            self.assertEqual(routed,event in (10,11,12))
