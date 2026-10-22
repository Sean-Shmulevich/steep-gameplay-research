import json
import struct
from pathlib import Path
import unittest
from reference.animation_bank_conversion import convert_relative_byte_bank


class ByteConversionTests(unittest.TestCase):
    def test_existing_original_instruction_receipt(self):
        receipt=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/relative_hierarchy_validation.json').read_text())
        self.assertEqual(receipt['cases'],192)
        def packed(records):return b''.join(struct.pack('<8f',*p,*q) for p,q in records)
        for sample in receipt['samples']:
            inputs=sample['inputs'];count=len(inputs['source'])
            source=dict(data=bytearray(packed(inputs['source'])+b'tail'),flags=0xabcdef12,
                parent_header=b'a'*32,profile=dict(primary_count=count,metadata=inputs['metadata']))
            dest=source if inputs['destination'] is None else dict(
                data=bytearray(packed(inputs['destination'])+b'tail'),flags=0x98765432,parent_header=b'b'*32)
            flags=dest['flags'];header=dest['parent_header'];seeds=iter(sample['rsqrt_seeds'])
            result=convert_relative_byte_bank(source,dest,inputs['mask'],lambda _:next(seeds))
            self.assertEqual(dest['data'],packed(sample['result']['records'])+b'tail')
            self.assertEqual(result,{k:sample['result'][k] for k in result})
            self.assertEqual(dest['flags'],(flags&~(1<<27))|(1<<26) if count else flags)
            self.assertEqual(dest['parent_header'],b'a'*32 if count else header)
            self.assertEqual(list(seeds),[])

    def test_empty_bank_does_not_require_storage(self):
        self.assertEqual(convert_relative_byte_bank(dict(profile=dict(primary_count=0)),{},0,None)['visited'],[])

    def test_shared_buffer_preserves_forward_parent_reads(self):
        data=bytearray(b''.join(struct.pack('<8f',x,0,0,0,0,0,0,1) for x in (2,5,9)))
        source=dict(data=data,parent_header=bytes(32),profile=dict(primary_count=3,
            metadata=[dict(parent=max(0,i-1),rank=0,skip_span=0) for i in range(3)]))
        destination=dict(data=data,flags=0)
        convert_relative_byte_bank(source,destination,0,lambda n:1.)
        self.assertEqual([struct.unpack_from('<f',data,32*i)[0] for i in range(3)],[2.,3.,6.])

    def test_joined_pose_uses_default_converter_for_new_alternates(self):
        from reference.animation_pose_blend import blend_regular_byte_pose
        profile=dict(primary_count=1,metadata=[dict(parent=0,rank=0,skip_span=0)],
            group_count=0,channel_count=1,descriptors=[dict(offset=0,kind=5)])
        def bank(x):return dict(data=bytearray(struct.pack('<8f',x,0,0,0,0,0,0,1)),
            profile=profile,flags=0,records=[],secondary_count=0,parent_header=bytes(32))
        def wrapper(x):return dict(primary=bank(x),alternate=None,index=65535,
            component=dict(pool='pool',flags16=0),request_byte=0)
        dst,src=wrapper(2),wrapper(8);allocated=[]
        def acquire(pool,index,mode):
            self.assertEqual((pool,index,mode),('pool',65535,0))
            b=bank(0);allocated.append(b);return b
        blend_regular_byte_pose(dst,src,.5,acquire=acquire,get_owner_scalar=lambda w:1.,
            reciprocal_sqrt=lambda n:1.)
        self.assertEqual(len(allocated),2)
        self.assertIs(src['alternate'],allocated[0]);self.assertIs(dst['alternate'],allocated[1])
        self.assertEqual(struct.unpack_from('<f',dst['primary']['data'])[0],5.)
        self.assertEqual(dst['primary']['flags'],1<<27)
        self.assertEqual(dst['alternate']['flags'],1<<26)
        self.assertEqual(src['request_byte'],0);self.assertEqual(dst['request_byte'],0)
