import struct
import unittest
from engine.pose_group_worker import run_pose_group_worker,claim_pose_batch_serial


def fixture():
    contexts={1:bytearray(0x450),2:bytearray(0x450)}
    struct.pack_into('<QI',contexts[2],0x438,100,1)
    job=bytearray(24);struct.pack_into('<Q',job,0,2)
    struct.pack_into('<fQ',job,0xc,.5,10)
    settings=bytearray(64);settings[0x14]=2
    struct.pack_into('<3f',settings,0x34,1,2,3)
    batch=bytearray(16);struct.pack_into('<I',batch,0,2);struct.pack_into('<Q',batch,8,200)
    groups={3:bytearray(0xa8),4:bytearray(0xa8)}
    for token,g in groups.items():
        struct.pack_into('<QI',g,0x10,300,1);struct.pack_into('<I',g,0x98,1);g[0xa0]=1
    body=bytearray(0x40);struct.pack_into('<Q',body,0x30,30)
    args=dict(contexts=contexts,batches={100:batch},arrays={200:[3,4],300:[5]},groups=groups,
        bodies={5:body},metadata={30:bytearray(0x60)},settings={10:settings},
        claim=lambda token:claim_pose_batch_serial(contexts[token]))
    return job,args


class GroupWorkerTests(unittest.TestCase):
    def test_scratch_reuse_release_and_claim_owner(self):
        job,args=fixture();events=[]
        def solve(token,request):
            events.append((token,request['buffer'],request['capacity']))
            request.update(buffer=900,capacity=1000)
        def unexpected(*a):self.fail('Unexpected free-motion path')
        run_pose_group_worker(1,job,solve=solve,advance_motion=unexpected,poststep=unexpected,
            release=lambda p:events.append(('release',p)),**args)
        self.assertEqual(events,[(3,0,0),(4,900,1000),('release',900)])
        self.assertEqual(struct.unpack_from('<I',args['contexts'][1],0x448)[0],2)
        self.assertEqual(struct.unpack_from('<I',args['contexts'][2],0x448)[0],0)

    def test_bypass_fixed_body_still_runs_raw_enabled_poststep(self):
        job,args=fixture();events=[]
        args['settings'][10][0x20]=1;args['metadata'][30][0x52]=8
        run_pose_group_worker(1,job,solve=lambda *a:self.fail('bypassed'),
            advance_motion=lambda *a:self.fail('single fixed body'),
            poststep=lambda *a:events.append(a),release=lambda *a:self.fail('no buffer'),**args)
        self.assertEqual(events,[(3,.5,2,1.,2.,3.),(4,.5,2,1.,2.,3.)])

    def test_uint32_count_sum_and_inactive_flag(self):
        job,args=fixture();events=[]
        for g in args['groups'].values():struct.pack_into('<I',g,0x48,0xffffffff)
        run_pose_group_worker(1,job,solve=lambda *a:self.fail('wrapped sum is zero'),
            advance_motion=lambda *a:events.append('motion'),poststep=lambda *a:events.append('post'),
            release=lambda *a:self.fail('no buffer'),**args)
        self.assertEqual(events,['motion','post','motion','post'])

    def test_batch_pointer_reloaded_between_groups(self):
        job,args=fixture();events=[]
        args['arrays'][201]=[4,3]
        def solve(token,request):
            events.append(token)
            struct.pack_into('<Q',args['batches'][100],8,201)
        run_pose_group_worker(1,job,solve=solve,advance_motion=lambda *a:None,
            poststep=lambda *a:None,release=lambda *a:None,**args)
        self.assertEqual(events,[3,3])

    def test_serial_claim_wrap_is_not_saturation(self):
        context=bytearray(0x450);struct.pack_into('<I',context,0x448,0xffffffff)
        self.assertEqual(claim_pose_batch_serial(context),0xffffffff)
        self.assertEqual(struct.unpack_from('<I',context,0x448)[0],0)
