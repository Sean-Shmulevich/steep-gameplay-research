import struct
import unittest
from tests.test_pose_group_runtime import fixture
from tests.test_pose_poststep_runtime import bind
from engine.pose_worker_runtime import run_retained_pose_worker
from engine.pose_group_worker import claim_pose_batch_serial


def worker_fixture(bypass=False):
    _,_,group_args,_=fixture();poststep=bind(group_args)
    world=bytearray(0x450);struct.pack_into('<QI',world,0x438,500,1)
    batch=bytearray(16);struct.pack_into('<I',batch,0,2);struct.pack_into('<Q',batch,8,600)
    job=bytearray(24);struct.pack_into('<Q',job,0,400);struct.pack_into('<fQ',job,0xc,.5,700)
    settings=bytearray(64);struct.pack_into('<H',settings,0x28,2);settings[0x20]=int(bypass)
    if bypass:struct.pack_into('<3f',settings,8,2,0,0)
    arrays=dict(group_args['arrays']);arrays[600]=[99,99]
    buffers={};events=[]
    def allocate(size):
        token=900+len(buffers);buffers[token]=bytearray(size);events.append(('allocate',token,size));return token
    args=dict(contexts={400:world},batches={500:batch},arrays=arrays,groups=group_args['groups'],
        bodies=group_args['bodies'],metadata=group_args['metadata'],settings={700:settings},
        links={},entry_arrays={},constraints=group_args['constraints'],get_kind=group_args['get_kind'],
        payloads={},resources={},profiles={},modes={},buffers=buffers,allocate=allocate,
        release=lambda token:events.append(('release',token)),claim=lambda _:claim_pose_batch_serial(world),
        poststep=poststep,atan2=group_args['atan2'])
    return job,args,events


class NumericalWorkerTests(unittest.TestCase):
    def test_solver_reuses_buffer_and_releases_after_batch(self):
        job,args,events=worker_fixture()
        run_retained_pose_worker(400,job,**args)
        self.assertEqual([e[0] for e in events],['allocate','release'])
        self.assertEqual(events[-1],('release',900))
        self.assertNotEqual(struct.unpack_from('<f',args['bodies'][1],0x70)[0],0)

    def test_bypass_advances_motion_without_solver_allocation(self):
        job,args,events=worker_fixture(True)
        run_retained_pose_worker(400,job,**args)
        self.assertEqual(events,[])
        self.assertEqual(struct.unpack_from('<f',args['bodies'][1],0x1a0)[0],2.)
        self.assertEqual(struct.unpack_from('<f',args['bodies'][1],0x70)[0],1.5)

    def test_larger_later_group_releases_before_growing(self):
        job,args,events=worker_fixture()
        second=bytearray(args['groups'][99]);struct.pack_into('<QI',second,0x90,301,2)
        args['groups'][98]=second;args['arrays'][301]=[3,3];args['arrays'][600]=[99,98]
        # Poststep binding uses the original array mapping; add the new group only.
        run_retained_pose_worker(400,job,**args)
        self.assertEqual([e[0] for e in events],['allocate','release','allocate','release'])
        self.assertGreater(events[2][2],events[0][2])
        self.assertEqual(events[1],('release',900));self.assertEqual(events[3],('release',901))
