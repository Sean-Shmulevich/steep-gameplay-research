import struct
import unittest
from engine.pose_group_lifecycle import construct_pose_group,return_pose_group_storage
from engine.pose_group_pool import acquire_pose_group_storage


class LifecycleTests(unittest.TestCase):
    def test_constructor_preserves_inactive_storage_and_unknown_fields(self):
        before=bytes([0xa5])*168
        result=construct_pose_group(before,token=0x1000,index=7,table=0x2000)
        self.assertEqual(struct.unpack_from('<QII',result,0x10),(0x1020,0,4))
        self.assertEqual(struct.unpack_from('<QII',result,0x40),(0x1050,0,8))
        self.assertEqual(result[8:12],before[8:12])
        self.assertEqual(result[0x20:0x40],before[0x20:0x40])
        self.assertEqual(result[0x50:0x90],before[0x50:0x90])
        self.assertEqual(result[0xa2:],before[0xa2:])
        self.assertEqual(result[0x90:0xa2],bytes(18))

    def test_return_acquire_construct_reuses_token_without_retaining_table(self):
        pool=dict(free_head=0x9000,used=1)
        storage={0x1000:bytearray([0xa5])*168}
        def write(token,next_token):struct.pack_into('<Q',storage[token],0,next_token)
        return_pose_group_storage(pool,0x1000,write_next=write)
        self.assertEqual(struct.unpack_from('<Q',storage[0x1000])[0],0x9000)
        self.assertEqual(pool,dict(free_head=0x1000,used=0))
        token=acquire_pose_group_storage(pool,
            read_next=lambda t:struct.unpack_from('<Q',storage[t])[0],
            allocate=lambda *a:self.fail('allocate'),grow=lambda *a:self.fail('grow'))
        self.assertEqual((token,pool['free_head'],pool['used']),(0x1000,0x9000,1))
        result=construct_pose_group(storage[token],token=token,index=3,table=0x2000)
        self.assertEqual(struct.unpack_from('<Q',result)[0],0x2000)
        self.assertEqual(result[0x20:0x40],bytes([0xa5])*32)

    def test_return_wrap_and_publication_order(self):
        pool=dict(free_head=4,used=0);seen=[]
        return_pose_group_storage(pool,8,write_next=lambda *a:seen.append((a,pool.copy())))
        self.assertEqual(seen,[((8,4),dict(free_head=4,used=0))])
        self.assertEqual(pool,dict(free_head=8,used=0xffffffff))

    def test_invalid_storage_does_not_mutate_input(self):
        storage=bytearray(167)
        with self.assertRaises(ValueError):construct_pose_group(storage,token=0,index=0,table=0)
        self.assertEqual(storage,bytearray(167))
