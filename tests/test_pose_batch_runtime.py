import struct
import unittest
from functools import cmp_to_key
from tests.test_pose_worker_runtime import worker_fixture
from engine.pose_batch_runtime import RetainedPointerArrays, run_retained_pose_batch_pass
from engine.pose_dispatch import pose_dispatch_serial_atomics
from engine.pose_context_init import initialize_pose_jobs, bind_pose_jobs


class BatchRuntimeTests(unittest.TestCase):
    def test_interior_views_follow_source_mutation_and_replacement(self):
        raw={100:[1,2,3]};arrays=RetainedPointerArrays(raw);view=arrays[108]
        raw[100][1]=9
        self.assertEqual(view[:],[9,3])
        raw[100]=[4,5,6]
        self.assertEqual(arrays[108][:],[5,6])
        self.assertEqual(view[-1],3)
        with self.assertRaises(KeyError):arrays[101]
        raw[108]=[7,8,9]
        with self.assertRaises(KeyError):arrays[116]

    def run_passes(self,bypass):
        _,services,events=worker_fixture(bypass)
        world=services['contexts'][400];world.extend(bytes(0x490-len(world)))
        arrays=services['arrays'];groups=services['groups'];settings=services['settings'][700]
        # Empty synthetic groups create enough work for two batches without
        # sharing physical bodies between groups.
        for token in range(2000,2030):groups[token]=bytearray(0xa8)
        arrays[10000]=[99]+list(range(2000,2030))
        for i,token in enumerate(arrays[10000]):struct.pack_into('<I',groups[token],0xc,i)
        struct.pack_into('<QII',world,0x418,10000,31,31)
        struct.pack_into('<QII',world,0x428,11000,0,32);arrays[11000]=[0]*32
        struct.pack_into('<QII',world,0x480,12000,0,64);arrays[12000]=[0]*64
        struct.pack_into('<QII',world,0x438,13000,0,8)
        services['batches']={13000+i*16:bytearray(16) for i in range(8)}
        world[0x44c]=1;settings[0x14]=1;struct.pack_into('<3f',settings,0x34,.1,100.,100.)
        initialize_pose_jobs(world,context_token=400)
        binding=bind_pose_jobs(world,context_token=400)
        jobs=binding['jobs'];arrays[binding['table_token']]=binding['arguments']
        dispatcher=bytearray(0x728);struct.pack_into('<I',dispatcher,0x10,2)
        cas,add=pose_dispatch_serial_atomics(dispatcher);queue=[]
        def no_growth(*args):self.fail('unexpected growth')
        kwargs=dict(dispatcher=dispatcher,scalar=.5,settings_token=700,
            worker_callback_token=88,jobs=jobs,worker_services=services,
            dispatch_services=dict(atomic_compare_exchange=cas,atomic_add=add,
                enqueue=queue.append,take=lambda:queue.pop(0) if queue else None,
                notify=lambda h:None,wait=lambda:self.fail('unexpected wait')),
            sort_prefix=lambda slots,n,cmp:slots.__setitem__(slice(0,n),sorted(slots[:n],key=cmp_to_key(cmp))),
            grow_batches=no_growth,grow_lists=no_growth)
        run_retained_pose_batch_pass(400,**kwargs)
        self.assertEqual(struct.unpack_from('<I',world,0x420)[0],0)
        self.assertEqual(struct.unpack_from('<I',world,0x430)[0],31)
        self.assertEqual(struct.unpack_from('<I',world,0x488)[0],2)
        self.assertEqual(struct.unpack_from('<I',world,0x440)[0],0)
        self.assertEqual(struct.unpack_from('<I',dispatcher,0x6a8)[0],0)
        snapshot={t:bytes(b) for t,b in services['bodies'].items()};count=len(events)
        run_retained_pose_batch_pass(400,**kwargs)
        self.assertEqual({t:bytes(b) for t,b in services['bodies'].items()},snapshot)
        self.assertEqual(len(events),count)
        return events

    def test_solve_through_dispatch_and_retirement(self):
        events=self.run_passes(False)
        self.assertEqual([e[0] for e in events],['allocate','release'])

    def test_free_motion_through_dispatch_and_retirement(self):
        self.assertEqual(self.run_passes(True),[])


if __name__=='__main__':unittest.main()
