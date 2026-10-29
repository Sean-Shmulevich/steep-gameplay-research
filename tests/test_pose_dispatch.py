import struct
import unittest
from engine.pose_dispatch import dispatch_pose_workers, pose_dispatch_serial_atomics


class DispatchTests(unittest.TestCase):
    def fixture(self,capacity=4):
        d=bytearray(0x728);struct.pack_into('<I',d,0x10,capacity)
        for i in range(capacity):struct.pack_into('<Q',d,0x118+8*i,100+i)
        cas,add=pose_dispatch_serial_atomics(d)
        return d,cas,add

    def test_single_and_null_arguments_skip_queue(self):
        d,cas,add=self.fixture(1);events=[]
        def forbidden(*args):self.fail('unexpected queue operation')
        dispatch_pose_workers(d,20,7,None,atomic_compare_exchange=forbidden,
            atomic_add=forbidden,enqueue=forbidden,take=forbidden,
            invoke=lambda *x:events.append(x),notify=forbidden,wait=forbidden)
        self.assertEqual(events,[(7,0,True)])

    def test_caller_help_and_counter_order(self):
        d,cas,add=self.fixture();queue=[];events=[]
        struct.pack_into('<I',d,0x6a8,9) # owned by unrelated dispatch
        def invoke(fn,arg,caller):
            events.append((arg,struct.unpack_from('<I',d,0x62c)[0],
                           struct.unpack_from('<I',d,0x6ac)[0]))
        dispatch_pose_workers(d,3,7,[10,11,12],atomic_compare_exchange=cas,
            atomic_add=add,enqueue=queue.append,take=lambda:queue.pop(0) if queue else None,
            invoke=invoke,notify=lambda h:None,wait=lambda:self.fail('wait'))
        self.assertEqual(events,[(10,2,2),(11,1,2),(12,0,1)])
        self.assertEqual(struct.unpack_from('<I',d,0x6a8)[0],9)
        self.assertEqual(struct.unpack_from('<I',d,0x6ac)[0],0)

    def test_claimed_callbacks_still_require_completion_wait(self):
        d,cas,add=self.fixture(3);queue=[];pending=[];events=[]
        def notify(handle):
            record=queue.pop(0);add(0x628+record[1]*4,-1);pending.append(record)
        def wait():
            events.append('wait');record=pending.pop(0)
            events.append(record[3]);add(0x6a8+record[1]*4,-1)
        dispatch_pose_workers(d,3,7,[10,11,12],atomic_compare_exchange=cas,
            atomic_add=add,enqueue=queue.append,take=lambda:self.fail('already claimed'),
            invoke=lambda fn,arg,caller:events.append(arg),notify=notify,wait=wait)
        self.assertEqual(events,[10,'wait',11,'wait',12])

    def test_help_other_slot_and_empty_queue_wait(self):
        d,cas,add=self.fixture(2);queue=[(123,3,8,99)];events=[]
        struct.pack_into('<I',d,0x634,1);struct.pack_into('<I',d,0x6b4,1)
        def take():return queue.pop(0) if queue else None
        def wait():events.append('wait');add(0x628,-1);add(0x6a8,-1)
        dispatch_pose_workers(d,2,7,[10,11],atomic_compare_exchange=cas,
            atomic_add=add,enqueue=lambda r:None,take=take,
            invoke=lambda f,a,c:events.append(a),notify=lambda h:None,wait=wait)
        self.assertEqual(events,[10,99,'wait'])
        self.assertEqual(struct.unpack_from('<I',d,0x6b4)[0],0)

    def test_invalid_admission(self):
        d,cas,add=self.fixture(2)
        kwargs=dict(atomic_compare_exchange=cas,atomic_add=add,enqueue=lambda r:None,
                    take=lambda:None,invoke=lambda *x:None,notify=lambda h:None,wait=lambda:None)
        with self.assertRaises(ValueError):dispatch_pose_workers(d,0,7,None,**kwargs)
        for i in range(32):struct.pack_into('<I',d,0x6a8+i*4,1)
        with self.assertRaises(ValueError):dispatch_pose_workers(d,2,7,None,**kwargs)


if __name__=='__main__':unittest.main()
