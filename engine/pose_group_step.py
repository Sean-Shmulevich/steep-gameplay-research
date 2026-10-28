"""Recovered group-step orchestration around explicit numerical services.

Evidence: LINK_SOLVER.md, Group-step orchestration and phase transitions.
"""
import struct


def run_pose_group_step(context, *, base_token, groups, services):
    """Run the recovered call/gate sequence with native-shaped opaque tokens.

    groups maps tokens to retained raw group headers. Services receive the native
    argument order and must implement each named operation. No no-op defaults,
    pointer dereference, allocator, synchronization or implicit numerical solver.
    Context storage must contain every reached zero-fill block. Normal returns,
    nonwrapping tokens and valid retained group headers define the API domain.
    """
    if len(context)<0x17c:raise ValueError('Complete retained context required')
    u32=lambda off:struct.unpack_from('<I',context,off)[0]
    flags=lambda:u32(0x38)
    def put_flags(value):struct.pack_into('<I',context,0x38,value)
    group_token=struct.unpack_from('<Q',context,0x30)[0]
    group=groups[group_token]
    def span(offset):
        start,count=struct.unpack_from('<QI',group,offset)
        return start,start+count*8
    data_offset,state_offset=u32(0x170),u32(0x174)
    capacity=((state_offset-data_offset)&0xffffffff)>>6
    count=struct.unpack_from('<I',group,0x18)[0]
    signed=count if count<0x80000000 else count-0x100000000
    selected=count if signed<capacity else capacity
    bodies_start=struct.unpack_from('<Q',group,0x10)[0]
    services['build_body_buffers'](base_token+data_offset,base_token+state_offset,
                                  bodies_start,selected,base_token+0x10,base_token)
    services['build_link_rows'](base_token,*span(0x40))
    put_flags((flags()&~0x10000000)|0x08000000)
    services['build_pose_rows'](base_token,*span(0x90))
    services['solve'](base_token)
    services['link_feedback'](base_token,*span(0x40))
    services['body_feedback'](base_token,*span(0x10))
    services['pose_feedback'](base_token,*span(0x90))
    if flags()&0x07ff0000:
        put_flags((flags()&~0x08000000)|0x10000000)
        start,end=u32(0x174),u32(0x178)
        for offset in range(start,end,32):
            if offset+32>len(context):raise ValueError('Complete retained zero-fill blocks required')
            context[offset:offset+32]=bytes(32)
        services['refresh_secondary_rows'](base_token,*span(0x40))
        services['solve'](base_token)
    if flags()&0x07ff0000:
        services['apply_secondary_state'](base_token,*span(0x10))
    scalar=struct.unpack_from('<f',context,0x10)[0]
    a,b,c=struct.unpack_from('<3f',context,0x24)
    services['poststep'](group_token,scalar,(flags()>>30)&1,a,b,c)
