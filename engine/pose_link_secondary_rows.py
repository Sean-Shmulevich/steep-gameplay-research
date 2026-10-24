"""Recovered refresh of retained primary rows for the secondary link pass.

Evidence: LINK_SOLVER.md, Secondary link row refresh.
"""
import struct
from reference.central_impulse import f32


def refresh_pose_secondary_link_rows(context, link_tokens, *, links, bodies, payloads):
    """Refresh response/cache fields; preserve existing row geometry and headers.

    context: field18, field1c, counts[2], rows[2], result_rows. Category0 rows
    have112 bytes; category1 rows have128. Records must remain valid and retained.
    No allocation, native pointer aliasing, exceptional arithmetic or locking.
    """
    context['counts'][:] = [0, 0]
    def xyz(raw,off):return struct.unpack_from('<3f',raw,off)
    def center(body,offset):
        b=[list(map(f32,r)) for r in body['frame']['basis']];t=body['frame']['translation']
        return [f32(f32(t[j])+f32(f32(b[2][j]*offset[2])+
                     f32(f32(b[1][j]*offset[1])+f32(b[0][j]*offset[0])))) for j in range(3)]
    def point(body,local,offset,origin):
        b=[list(map(f32,r)) for r in body['frame']['basis']]
        v=[f32(f32(x)-f32(y)) for x,y in zip(local,offset)]
        return [f32(f32(f32(f32(b[0][j]*v[0])+origin[j])+
                          f32(b[1][j]*v[1]))+f32(b[2][j]*v[2])) for j in range(3)]
    for token in link_tokens:
        link=links[token]
        if not link['flags84']&1:continue
        first=bodies[link['first_body']];second=bodies[link['second_body']]
        category=1 if second['metadata_flags50']&0x8000 else 0
        gain=-f32(context['field18']);offset_response=f32(f32(context['field1c'])*2.0)
        count=link['payload_count']
        for i in range(count):
            payload=payloads[link['payload_slots'][i]]
            if not payload[0x114]&1:continue
            n=struct.unpack_from('<I',payload,0x110)[0]
            if n>4:raise ValueError('At most four retained payload rows required')
            offset1=list(map(f32,first['offset128']));origin1=center(first,offset1)
            offset2=list(map(f32,second['offset128'])) if category else [0.0]*3
            origin2=center(second,offset2) if category else list(map(f32,second['frame']['translation']))
            for j in range(n):
                row=context['rows'][category][context['counts'][category]]
                context['counts'][category]=(context['counts'][category]+1)&0xffffffff
                if len(row)!=(128 if category else 112):raise ValueError('Complete retained solver row required')
                start=0x10+64*j
                normal=xyz(payload,start)
                a=point(first,xyz(payload,start+16),offset1,origin1)
                b=point(second,xyz(payload,start+32),offset2,origin2)
                products=[f32(-normal[k]*f32(b[k]-a[k])) for k in range(3)]
                projection=f32(f32(products[0]+products[1])+f32(products[2]+0.0))
                response=f32(gain*f32(projection+offset_response))
                response=response if response<0 else 0.0
                struct.pack_into('<4f',row,0x10,*([response]*4))
                struct.pack_into('<Q',row,0x50,0)
                result=struct.unpack_from('<I',row,4)[0]
                context['result_rows'][result][:]=bytes(16)
