import struct
import unittest
from engine.pose_group_transfer import transfer_completed_pose_groups, append_pose_group_bodies


def fixture(flags, enabled=1):
    context = bytearray(0x490)
    struct.pack_into('<QII', context, 0x418, 0x1000, len(flags), len(flags))
    struct.pack_into('<QII', context, 0x428, 0x2000, 0, 8)
    struct.pack_into('<QII', context, 0x480, 0x3000, 0, 16)
    context[0x44c] = enabled
    groups = {}; arrays = {0x1000:[], 0x2000:[0]*8, 0x3000:[0]*16}
    for i, flag in enumerate(flags):
        token=0x4000+i*0x100; g=bytearray(0xa8)
        struct.pack_into('<I',g,0xc,i);g[0xa0]=flag
        struct.pack_into('<QI',g,0x10,token+0xb0,2)
        arrays[token+0xb0]=[token+1,token+2];groups[token]=g;arrays[0x1000].append(token)
    return context,arrays,groups


class TransferTests(unittest.TestCase):
    def test_reverse_order_swap_repair_stale_tail_and_special_group(self):
        c,a,g=fixture([1,0,2,0])
        struct.pack_into('<QQ',c,0x408,0x4000,0x4200)
        transfer_completed_pose_groups(c,arrays=a,groups=g,grow=lambda *x:self.fail('growth'))
        self.assertEqual(a[0x1000], [0x4300,0x4100,0x4300,0x4300])
        self.assertEqual(a[0x2000][:2], [0x4200,0x4000])
        self.assertEqual(a[0x3000][:4], [0x4201,0x4202,0x4001,0x4002])
        self.assertEqual(struct.unpack_from('<I',c,0x420)[0],2)
        self.assertEqual(struct.unpack_from('<I',g[0x4300],0xc)[0],0)
        self.assertEqual(struct.unpack_from('<I',g[0x4000],0xc)[0],1)
        self.assertEqual([g[t][0xa0] for t in g],[1,0,2,0])
        snapshot=(bytes(c), {p:list(v) for p,v in a.items()})
        transfer_completed_pose_groups(c,arrays=a,groups=g,grow=lambda *x:self.fail('growth'))
        self.assertEqual((bytes(c),a),snapshot)

    def test_disabled_and_empty(self):
        for flags,enabled in [([1,1],0),([],1)]:
            c,a,g=fixture(flags,enabled); before=bytes(c)
            transfer_completed_pose_groups(c,arrays=a,groups=g,grow=lambda *x:self.fail('growth'))
            self.assertEqual(bytes(c),before)

    def test_growth_reloads_arrays_and_captures_body_count(self):
        c,a,g=fixture([1]);group=g[0x4000]
        struct.pack_into('<I',c,0x434,0)
        struct.pack_into('<II',c,0x488,1,1)
        a[0x3000][0]=99;events=[]
        def grow(ctx,offset,capacity):
            events.append((offset,capacity))
            old=struct.unpack_from('<Q',ctx,offset)[0];new=old+0x10000
            a[new]=a[old][:]+[0]*capacity
            struct.pack_into('<Q',ctx,offset,new)
            struct.pack_into('<I',ctx,offset+12,capacity)
            if offset==0x480:
                a[0x9999]=[77,88]
                struct.pack_into('<QI',group,0x10,0x9999,0)
        transfer_completed_pose_groups(c,arrays=a,groups=g,grow=grow)
        self.assertEqual(events,[(0x428,8),(0x480,4)])
        self.assertEqual(a[0x13000][:3],[99,77,88])
        self.assertEqual(a[0x12000][0],0x4000)

    def test_batch_finish_excludes_retired_groups_on_next_pass(self):
        from engine.pose_group_batches import run_pose_group_batches
        from functools import cmp_to_key
        c,a,g=fixture([0,0,0])
        struct.pack_into('<QII',c,0x438,0x9000,0,8)
        batches={0x9000+i*16:bytearray(16) for i in range(8)}
        for i,group in enumerate(g.values()):
            struct.pack_into('<I',group,0x98,25+i)
        visits=[]
        def dispatch(workers,table):
            # Synthetic solve outcome: one group becomes inactive in pass1.
            count=struct.unpack_from('<I',c,0x420)[0]
            visits.append(a[0x1000][:count])
            g[0x4100][0xa0]=1
        def finish(context):
            self.assertEqual(struct.unpack_from('<I',context,0x440)[0],0)
            transfer_completed_pose_groups(context,arrays=a,groups=g,
                grow=lambda *x:self.fail('growth'))
        def sort_prefix(slots,n,compare):
            slots[:n]=sorted(slots[:n],key=cmp_to_key(compare))
        for _ in range(2):
            run_pose_group_batches(c,context_token=0x8000,scalar=.125,
                settings_token=0xa000,worker_capacity=4,arrays=a,groups=g,
                batches=batches,sort_prefix=sort_prefix,
                grow=lambda *x:self.fail('growth'),dispatch=dispatch,finish=finish)
        self.assertEqual(visits,[[0x4200,0x4100,0x4000],[0x4200,0x4000]])
        self.assertEqual(struct.unpack_from('<I',c,0x430)[0],1)
        self.assertEqual(struct.unpack_from('<I',c,0x488)[0],2)

    def test_zero_capacity_uses_needed_and_empty_group_needs_no_array(self):
        c,a,g=fixture([1]);group=g[0x4000];struct.pack_into('<I',c,0x48c,0)
        requests=[]
        def grow(ctx,offset,capacity):
            requests.append((offset,capacity))
            struct.pack_into('<I',ctx,offset+12,capacity)
        append_pose_group_bodies(c,group,arrays=a,grow=grow)
        self.assertEqual(requests,[(0x480,2)])
        struct.pack_into('<QI',group,0x10,0,0)
        append_pose_group_bodies(c,group,arrays=a,grow=lambda *x:self.fail('growth'))


if __name__=='__main__':unittest.main()
