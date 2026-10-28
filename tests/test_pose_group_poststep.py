import struct
import unittest
from engine.pose_group_poststep import transition_pose_body_inactive,poststep_pose_group


def record():return dict(storage=bytearray(0x200),metadata=bytearray(0x60))


class GroupPoststepTests(unittest.TestCase):
    def run_step(self,g,b,**kw):
        args=dict(scalar=1,check_enabled=True,duration_threshold=.5,
                  linear_threshold=1,angular_threshold=1,set_inactive=lambda t:None,
                  integrate=lambda t,s:None,refresh=lambda t:None)
        args.update(kw);poststep_pose_group(g,bodies=b,**args)

    def test_all_quiet_transitions_then_skips_integration(self):
        g=dict(slots=[1,2],count=2,flag_a0=0);b={1:record(),2:record()};events=[]
        def inactive(t):
            events.append(t);r=b[t]
            transition_pose_body_inactive(t,r['storage'],r['metadata'],links={},clear_link=lambda t:self.fail())
        self.run_step(g,b,set_inactive=inactive,integrate=lambda *a:self.fail())
        self.assertEqual(events,[1,2]);self.assertEqual(g['flag_a0'],1)
        self.assertEqual([b[t]['metadata'][0x53] for t in (1,2)],[2,2])

    def test_empty_group_passes_and_failed_check_does_not_reactivate(self):
        g=dict(slots=[],count=0,flag_a0=0);self.run_step(g,{})
        self.assertEqual(g['flag_a0'],1)
        r=record();r['storage'][0xaa]=2
        g=dict(slots=[1],count=1,flag_a0=1)
        self.run_step(g,{1:r},integrate=lambda *a:self.fail())
        self.assertEqual(g['flag_a0'],1)

    def test_refresh_reloads_span_after_integration(self):
        g=dict(slots=[1,2],count=2,flag_a0=0);events=[]
        def integrate(t,s):
            events.append(('integrate',t));g['slots']=[3];g['count']=1
        self.run_step(g,{},check_enabled=False,integrate=integrate,
                      refresh=lambda t:events.append(('refresh',t)))
        self.assertEqual(events,[('integrate',1),('integrate',2),('refresh',3)])

    def test_transition_clears_ring_and_reloads_endpoint_after_service(self):
        r=record();r['metadata'][0x53]=0xaf;r['storage'][0x1a0:0x1b8]=bytes([7]*24)
        struct.pack_into('<Q',r['storage'],0x80,10)
        links={t:bytearray(0x40) for t in (10,20)};events=[]
        struct.pack_into('<Q',links[10],8,1);struct.pack_into('<Q',links[10],0x20,999)
        struct.pack_into('<Q',links[10],0x30,20);struct.pack_into('<Q',links[20],0x30,10)
        def clear(t):events.append(t);struct.pack_into('<Q',links[t],8,2)
        transition_pose_body_inactive(1,r['storage'],r['metadata'],links=links,clear_link=clear)
        self.assertEqual(events,[10,20]);self.assertEqual(r['metadata'][0x53],0xa2)
        self.assertEqual(r['storage'][0x1a0:0x1b8],bytes(24))
