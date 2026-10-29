import struct
import unittest
from engine.pose_group_prepare import prepare_pose_group
from engine.pose_group_runtime import run_pose_group_runtime


def fixture():
    arena=bytearray(0x2000);settings=bytearray(64)
    struct.pack_into('<H',settings,0x28,2)
    bodies={1:bytearray(0x1c0),2:bytearray(0x1c0)}
    metadata={10:bytearray(0x60),20:bytearray(0x60)}
    metadata[20][0x52]=8
    for index,(token,body) in enumerate(bodies.items()):
        struct.pack_into('<H',body,0x1c,index)
        struct.pack_into('<Q',body,0x30,10*token)
        struct.pack_into('<f',body,0x124,1.)
        for i in range(3):
            for offset in (0x40,0x170):
                struct.pack_into('<3f',body,offset+i*16,*[float(i==j) for j in range(3)])
    struct.pack_into('<f',bodies[2],0x70,1.)
    constraint=bytearray(0x1b0)
    struct.pack_into('<2Q',constraint,8,1,2)
    for offset in (0x80,0xc0):
        for i in range(3):struct.pack_into('<3f',constraint,offset+16*i,*[float(i==j) for j in range(3)])
    for offset in (0xf0,0x104,0x118):struct.pack_into('<I4f',constraint,offset,0,-1,1,1e12,1)
    for offset in (0x12c,0x140,0x154):struct.pack_into('<I4f',constraint,offset,1,-1,1,1e12,1)
    struct.pack_into('<3I',constraint,0x190,0xffffffff,0xffffffff,0xffffffff)
    group=bytearray(0xa8)
    for off,start,count in ((0x10,100,2),(0x40,200,0),(0x90,300,1)):
        struct.pack_into('<QI',group,off,start,count)
    plan=prepare_pose_group(arena,settings,scalar=.5,group_token=99,body_count=2,
        link_tokens=[],pose_tokens=[3],links={},payloads={},
        poses={3:dict(type=2,second_body=2,storage70=constraint[0x70:0x190])},
        bodies={2:dict(metadata_flags50=0)})
    events=[]
    def link(name,*args):events.append((name,args))
    def angle(*args):raise AssertionError('All angular rows skipped')
    args=dict(base_token=0,groups={99:group},arrays={100:[1,2],300:[3]},
        bodies=bodies,metadata=metadata,constraints={3:constraint},get_kind=lambda _:2,
        link_services={name:(lambda *a,name=name:link(name,*a)) for name in
                       ('build_link_rows','link_feedback','refresh_secondary_rows')},
        poststep=lambda *a:events.append(('poststep',a)),atan2=angle)
    return arena,plan,args,events


class GroupRuntimeTests(unittest.TestCase):
    def test_build_solve_feedback_share_state(self):
        arena,plan,args,events=fixture()
        run_pose_group_runtime(arena,**args)
        body=args['bodies'][1];constraint=args['constraints'][3]
        self.assertNotEqual(struct.unpack_from('<f',body,0x1a0)[0],0)
        state=plan['body_state_offset'];results=plan['results_offset']
        self.assertEqual(body[0x1a0:0x1ac],arena[state:state+12])
        self.assertEqual(constraint[0x19c:0x1a8],arena[results:results+12])
        self.assertEqual([e[0] for e in events],['build_link_rows','link_feedback','poststep'])
        self.assertEqual(struct.unpack_from('<I',arena,0xa4+4*10)[0],1)

    def test_secondary_phase_calls_explicit_update_and_restores_motion(self):
        arena,plan,args,events=fixture()
        flags=struct.unpack_from('<I',arena,0x38)[0]
        struct.pack_into('<I',arena,0x38,flags|0x10000)
        calls=[]
        def update(token,body,scalar):
            calls.append((token,bytes(body[0x1a0:0x1b8]),scalar))
            body[0x70:0x74]=struct.pack('<f',3.)
        run_pose_group_runtime(arena,update_body=update,**args)
        self.assertEqual(calls,[(1,bytes(24),1.),(2,bytes(24),1.)])
        self.assertNotEqual(args['bodies'][1][0x1a0:0x1b8],bytes(24))
        self.assertEqual(struct.unpack_from('<f',args['bodies'][1],0x70)[0],3.)
        self.assertIn('refresh_secondary_rows',[e[0] for e in events])

    def test_damping_service_required_when_reached(self):
        arena,plan,args,events=fixture()
        struct.pack_into('<Q',args['bodies'][1],0x1b8,500)
        with self.assertRaisesRegex(ValueError,'damping record'):
            run_pose_group_runtime(arena,**args)

    def test_fixed_body_does_not_resolve_damping_pointer(self):
        arena,plan,args,events=fixture()
        struct.pack_into('<Q',args['bodies'][2],0x1b8,500)
        run_pose_group_runtime(arena,**args)
