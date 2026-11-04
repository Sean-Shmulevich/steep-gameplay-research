import struct
import unittest
from engine.pose_body_connectivity_retire import retire_pose_body_connectivity,reserve_pose_pointer_vector
from engine.pose_body_connectivity_refresh import refresh_pose_body_connectivity
from engine.pose_endpoint_rings import attach_pose_endpoint_rings,detach_pose_endpoint_rings
from engine.pose_link_state_reset import reset_pose_link_state


class Allocator:
    """Authored deterministic allocator stand-in for the supplied vtable."""
    def __init__(self,arrays,start=0x9000):
        self.arrays=arrays;self.next=start;self.log=[]
    def allocate(self,size,align,tag):
        p=self.next;self.next+=0x1000;self.arrays[p]=bytearray(size);self.log.append(('allocate',size,align,tag));return p
    def reallocate(self,old,size,align,tag):
        p=self.next;self.next+=0x1000;src=self.arrays[old][:size]
        self.arrays[p]=bytearray(src)+bytearray(size-len(src));self.log.append(('reallocate',old,size,align,tag));return p
    def release(self,p):
        self.log.append(('release',p))


def owner(pointer,count,capacity):
    o=bytearray(0x40);struct.pack_into('<QII',o,0x28,pointer,count,capacity);return o


def vector(o):
    return struct.unpack_from('<QII',o,0x28)


class RetireTests(unittest.TestCase):
    def provider(self,*slots):
        p=bytearray(0x100)
        for i,s in enumerate(slots):struct.pack_into('<Q',p,0x70+8*i,s)
        return p

    def test_empty_output_calls_nothing_and_never_divides(self):
        p=self.provider(1);before=bytes(p)
        retire_pose_body_connectivity(p,[],0,queue_owners={},queue_arrays={},detach=None,reset=None,reserve=None)
        self.assertEqual(bytes(p),before)

    def test_order_round_robin_and_slot_captured_before_reset(self):
        owners={1:owner(100,0,4),2:owner(200,0,4)};arrays={100:bytearray(32),200:bytearray(32)}
        p=self.provider(1,2,1);events=[]
        def detach(link,selector):events.append(('detach',link,selector))
        def reset(link):
            events.append(('reset',link))
            struct.pack_into('<Q',p,0x70,2)  # redirect slot0 after it was read
        retire_pose_body_connectivity(p,[11,12,13,14],3,queue_owners=owners,queue_arrays=arrays,
            detach=detach,reset=reset,reserve=lambda *a:self.fail('growth'))
        self.assertEqual(events,[e for l in (11,12,13,14) for e in (('detach',l,1),('reset',l))])
        # Link11 used slot0 owner1 (read before redirect); link14 wrapped to slot0 now owner2.
        self.assertEqual(vector(owners[1])[1],2);self.assertEqual(vector(owners[2])[1],2)
        self.assertEqual(struct.unpack_from('<2Q',arrays[100]),(11,13))
        self.assertEqual(struct.unpack_from('<2Q',arrays[200]),(12,14))

    def test_growth_doubles_or_starts_at_eight_and_rereads_after_reset(self):
        arrays={100:bytearray(16)};owners={1:owner(0,0,0),2:owner(100,1,2)};alloc=Allocator(arrays)
        p=self.provider(1)
        reserve=lambda d,c:reserve_pose_pointer_vector(d,c,allocator=alloc)
        retire_pose_body_connectivity(p,[7],1,queue_owners=owners,queue_arrays=arrays,detach=lambda *a:None,reset=lambda l:None,reserve=reserve)
        self.assertEqual(alloc.log,[('allocate',64,0x10,0x28)]);self.assertEqual(vector(owners[1]),(0x9000,1,8))
        p=self.provider(2)
        def fill(link):struct.pack_into('<I',owners[2],0x30,2)  # count/capacity read after reset
        retire_pose_body_connectivity(p,[8],1,queue_owners=owners,queue_arrays=arrays,detach=lambda *a:None,reset=fill,reserve=reserve)
        self.assertEqual(alloc.log[1],('reallocate',100,32,0x10,0x28))
        self.assertEqual(vector(owners[2]),(0xa000,3,4));self.assertEqual(struct.unpack_from('<Q',arrays[0xa000],16)[0],8)

    def test_zero_divisor_faults_after_first_link_is_queued(self):
        owners={1:owner(100,0,4)};arrays={100:bytearray(32)};seen=[]
        with self.assertRaises(ZeroDivisionError):
            retire_pose_body_connectivity(self.provider(1),[5,6],0,queue_owners=owners,queue_arrays=arrays,
                detach=lambda l,s:seen.append(l),reset=lambda l:None,reserve=None)
        self.assertEqual(seen,[5]);self.assertEqual(vector(owners[1])[1],1)

    def test_length_captured_once_elements_reread(self):
        owners={1:owner(100,0,8)};arrays={100:bytearray(64)};out=[1,2]
        def reset(link):
            if link==1:out[1]=9;out.append(3)
        retire_pose_body_connectivity(self.provider(1),out,1,queue_owners=owners,queue_arrays=arrays,
            detach=lambda *a:None,reset=reset,reserve=None)
        self.assertEqual(struct.unpack_from('<3Q',arrays[100]),(1,9,0))

    def test_reserve_leaf_paths(self):
        arrays={100:bytearray(range(32))};alloc=Allocator(arrays)
        d=bytearray(struct.pack('<QII',100,3,4));reserve_pose_pointer_vector(d,4,allocator=alloc);self.assertEqual(alloc.log,[])
        reserve_pose_pointer_vector(d,2,allocator=alloc)
        self.assertEqual(struct.unpack('<QII',d),(0x9000,2,2));self.assertEqual(arrays[0x9000],bytearray(range(16)))
        reserve_pose_pointer_vector(d,0,allocator=alloc)
        self.assertEqual(alloc.log[-1],('release',0x9000));self.assertEqual(struct.unpack('<QII',d),(0,0,0))
        reserve_pose_pointer_vector(d,0x20000001,allocator=alloc)  # 32-bit byte-size truncation
        self.assertEqual(alloc.log[-1],('allocate',8,0x10,0x28));self.assertEqual(struct.unpack('<QII',d)[2],0x20000001)

    def test_composition_with_rings_link_reset_and_refresh(self):
        bodies={b:bytearray(0xa0) for b in (1,2,3)};records={}
        for t,a,b in ((10,1,2),(20,3,1),(30,1,3),(40,2,3)):
            r=bytearray(0x90);struct.pack_into('<2Q',r,8,a,b);struct.pack_into('<QI',r,0x58,500+t,1)
            struct.pack_into('<Q',r,0x78,t+1);records[t]=r
        for t in records:attach_pose_endpoint_rings(t,1,records=records,bodies=bodies)
        entries={500+t:bytearray(struct.pack('<QQ',0,t+2)) for t in records}
        released=[];arrays={};alloc=Allocator(arrays)
        meta=bytearray(0x60);own=bytearray(0x40);ctl=bytearray(0x80);prov=self.provider(77);owners={77:owner(0,0,0)}
        struct.pack_into('<Q',bodies[1],0x30,3000);struct.pack_into('<Q',meta,0x20,4000);struct.pack_into('<Q',own,0x20,5000)
        struct.pack_into('<QQ',ctl,0x30,6000,7000)
        def retire(provider,output,divisor):
            self.assertEqual(provider,7000)
            retire_pose_body_connectivity(prov,output,divisor,queue_owners=owners,queue_arrays=arrays,
                detach=lambda t,s:detach_pose_endpoint_rings(t,s,records=records,bodies=bodies),
                reset=lambda t:reset_pose_link_state(records[t],entry_arrays=entries,release_contact=released.append,release_held=released.append),
                reserve=lambda d,c:reserve_pose_pointer_vector(d,c,allocator=alloc))
        refresh_pose_body_connectivity(bodies[1],body_token=1,metadata={3000:meta},owners={4000:own},controllers={5000:ctl},
            links=records,collect=lambda p,rows:[30,10],rebuild=lambda c,o:None,retire=retire)
        self.assertEqual(released,[32,31,12,11])
        self.assertEqual(vector(owners[77]),(0x9000,2,8));self.assertEqual(struct.unpack_from('<2Q',arrays[0x9000]),(30,10))
        for t in (10,30):
            self.assertEqual(records[t][8:0x40],bytes(0x38));self.assertEqual(struct.unpack_from('<I',records[t],0x60)[0],0)
        # Only link20 remains on body1's selector1 ring; body2/body3 keep 40 and 20/40.
        self.assertEqual(struct.unpack_from('<Q',bodies[1],0x80)[0],20)
        self.assertEqual(struct.unpack_from('<2Q',records[20],0x30),(20,20))
        self.assertEqual(struct.unpack_from('<Q',bodies[2],0x80)[0],40)
        self.assertIn(struct.unpack_from('<Q',bodies[3],0x80)[0],(20,40))


if __name__=='__main__':
    unittest.main()
