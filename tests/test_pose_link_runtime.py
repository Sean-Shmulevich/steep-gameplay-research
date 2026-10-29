import struct
import unittest
from tests.test_pose_group_runtime import fixture
from engine.pose_group_prepare import prepare_pose_group
from engine.pose_group_runtime import run_pose_group_runtime
from engine.pose_link_runtime import make_pose_link_services


def mixed_fixture(mode=0,count=2):
    arena,_,args,events=fixture()
    parsed={}
    resources={};profiles={}
    for token,body in args['bodies'].items():
        v=lambda off:list(struct.unpack_from('<3f',body,off))
        resource=token+1000;profile=token+2000
        parsed[token]=dict(frame=dict(basis=[v(o) for o in (0x40,0x50,0x60)],translation=v(0x70)),
            offset128=v(0x128),motion1a0=v(0x1a0),motion1ac=v(0x1ac),index1c=token-1,
            entries=[resource],metadata_flags50=0)
        resources[resource]=dict(kind28=0,default20=profile)
        profiles[profile]=dict(field30=.4,field40=.2,field60=1e14,field64=1.)
    payload=bytearray(288)
    struct.pack_into('<I',payload,0x110,count);payload[0x114]=1
    for i in range(count):
        struct.pack_into('<3f',payload,0x10+i*64,0,1,0)
        struct.pack_into('<f',payload,0x40+i*64,-.1)
    links={4:dict(flags84=1,first_body=1,second_body=2,payload_count=1,payload_slots=[5])}
    payloads={5:payload};args['arrays'][200]=[4]
    struct.pack_into('<I',args['groups'][99],0x48,1)
    settings=bytearray(64);struct.pack_into('<IHH',settings,0x24,mode,2,0)
    constraint=args['constraints'][3]
    plan=prepare_pose_group(arena,settings,scalar=.5,group_token=99,body_count=2,
        link_tokens=[4],pose_tokens=[3],links=links,payloads=payloads,
        poses={3:dict(type=2,second_body=2,storage70=constraint[0x70:0x190])},bodies=parsed)
    args['link_services']=make_pose_link_services(arena,arrays=args['arrays'],links=links,
        bodies=parsed,payloads=payloads,resources=resources,profiles=profiles,
        modes={name:0 for name in ('field30','field40','field60','field64')})
    return arena,plan,args,payload


class MixedLinkRuntimeTests(unittest.TestCase):
    def test_contact_and_constraint_counts_share_one_arena(self):
        for mode in range(4):
            for count in range(1,5):
                arena,plan,args,payload=mixed_fixture(mode,count)
                before=bytes(payload)
                run_pose_group_runtime(arena,**args)
                planned=struct.unpack_from('<25I',arena,0x108)
                built=struct.unpack_from('<25I',arena,0xa4)
                self.assertEqual(built,planned)
                self.assertEqual(planned[0],count)
                self.assertEqual(planned[10],1)
                self.assertEqual(planned[4],int(mode==0 and count>1))
                self.assertNotEqual(bytes(payload),before)
                constraint=args['constraints'][3]
                index=struct.unpack_from('<I',constraint,0x190)[0]
                self.assertGreaterEqual(index,count)
                offset=plan['results_offset']+16*index
                self.assertEqual(constraint[0x19c:0x1a8],arena[offset:offset+12])

    def test_secondary_refresh_preserves_pose_counts(self):
        arena,plan,args,payload=mixed_fixture()
        flags=struct.unpack_from('<I',arena,0x38)[0]
        struct.pack_into('<I',arena,0x38,flags|0x10000)
        calls=[]
        run_pose_group_runtime(arena,update_body=lambda *a:calls.append(a[0]),**args)
        self.assertEqual(calls,[1,2])
        self.assertEqual(struct.unpack_from('<I',arena,0xa4+4*10)[0],1)
        self.assertEqual(struct.unpack_from('<I',arena,0xa4)[0],2)
