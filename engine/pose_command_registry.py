"""Recovered provider registration for command preparation collections.

Evidence: LINK_SOLVER.md, Command registry population.
"""
import struct


def _u32(raw,offset):
    return struct.unpack_from('<I',raw,offset)[0]


def _pointer(raw,offset):
    return struct.unpack_from('<Q',raw,offset)[0]


def _append(provider,offset,token,arrays,grow):
    capacity=_u32(provider,offset+12)
    if _u32(provider,offset+8)==capacity:
        grow(provider,offset,(capacity*2)&0xffffffff if capacity else 8)
    count=_u32(provider,offset+8)
    arrays[_pointer(provider,offset)][count]=token
    struct.pack_into('<I',provider,offset+8,(count+1)&0xffffffff)


def register_pose_constraint(provider,token,*,arrays,grow,notify,get_kind):
    """Register one constraint, attach endpoint rings, then classify it.

    grow(provider,descriptor_offset,capacity) updates storage/pointer/capacity and
    preserves active entries. notify(token,2) supplies endpoint-ring insertion;
    the service name is retained for API compatibility.
    get_kind(token) supplies the virtual method's uint32 result. The first command
    list is70; the general constraint list is60. No inferred duplicate rejection.
    """
    _append(provider,0x60,token,arrays,grow)
    notify(token,2)
    if get_kind(token)==4:
        _append(provider,0x70,token,arrays,grow)


def register_pose_constraint_container(provider,token,*,containers,arrays,grow,get_kind):
    """Register an object and append kind4 children to the second command list.

    Child count60 is captured after the object append. Child pointer58 is reloaded
    on every iteration. The returned index is captured before storage growth.
    The registered object's semantic class remains unresolved.
    """
    original_count=_u32(provider,0x58)
    _append(provider,0x50,token,arrays,grow)
    container=containers[token]
    count=_u32(container,0x60)
    for index in range(count):
        child=arrays[_pointer(container,0x58)][index]
        if get_kind(child)==4:
            _append(provider,0x80,child,arrays,grow)
    return original_count


def unregister_pose_constraint(provider,token,*,arrays,get_kind,detach):
    """Remove an individual registration, detach rings, then remove general entry.

    Only the first matching entry is removed; slots are replaced by the last
    active entry and inactive tails remain untouched. detach(token,2) supplies
    endpoint-ring removal. No destructor or storage release is called here.
    Missing membership raises an authored ValueError instead of reproducing the
    native UINT32_MAX index and out-of-bounds write.
    """
    def locate(offset):
        slots=arrays[_pointer(provider,offset)]
        for index in range(_u32(provider,offset+8)):
            if slots[index]==token:return index
        raise ValueError('Constraint absent from required provider list')
    general_index=locate(0x60)
    if get_kind(token)==4:
        command_index=locate(0x70)
        count=(_u32(provider,0x78)-1)&0xffffffff
        struct.pack_into('<I',provider,0x78,count)
        slots=arrays[_pointer(provider,0x70)]
        slots[command_index]=slots[count]
    detach(token,2)
    count=(_u32(provider,0x68)-1)&0xffffffff
    struct.pack_into('<I',provider,0x68,count)
    slots=arrays[_pointer(provider,0x60)]
    slots[general_index]=slots[count]


def unregister_pose_constraint_container(provider,token,output,*,provider_token,
        containers,constraints,bodies,metadata,arrays,get_kind,remove_tree_body,
        process_body,grow_output):
    """Remove a container and queue eligible children.

    Evidence: LINK_SOLVER.md, Container removal and deferred children.
    remove_tree_body(tree_token,body) and process_body(provider_token,body,output)
    are unresolved services. grow_output(output,new_capacity) preserves entries
    and updates the pointer; this wrapper updates capacity and clamps count.
    This operation is serial and nontransactional, including on service failure.
    """
    container=containers[token]
    body_count=_u32(container,0x40)
    original_index=_u32(container,0x30)
    for index in range(body_count):
        body=arrays[_pointer(container,0x38)][index]
        if metadata[_pointer(bodies[body],0x30)][0x52]&8:
            remove_tree_body(provider_token+0xd0,body)
        process_body(provider_token,body,output)
    child_count=_u32(container,0x60)
    for index in range(child_count):
        child=arrays[_pointer(container,0x58)][index]
        first=_pointer(constraints[child],8)
        second=_pointer(constraints[child],0x10)
        if get_kind(child)==4:
            slots=arrays[_pointer(provider,0x80)]
            count=_u32(provider,0x88)
            found=next((i for i in range(count) if slots[i]==child),None)
            if found is None:
                raise ValueError('Child absent from second command list')
            count-=1
            struct.pack_into('<I',provider,0x88,count)
            slots[found]=slots[count]
        if metadata[_pointer(bodies[first],0x30)][0x52]&1:
            continue
        if second and metadata[_pointer(bodies[second],0x30)][0x52]&1:
            continue
        capacity=_u32(output,12)
        if _u32(output,8)==capacity:
            new_capacity=capacity*2 if capacity else 8
            if new_capacity>0x1fffffff:
                raise ValueError('Output allocation size exceeds uint32 byte size')
            grow_output(output,new_capacity)
            struct.pack_into('<I',output,12,new_capacity)
            if _u32(output,8)>new_capacity:
                struct.pack_into('<I',output,8,new_capacity)
        count=_u32(output,8)
        arrays[_pointer(output,0)][count]=child
        struct.pack_into('<I',output,8,count+1)
    count=_u32(provider,0x58)
    if not count or original_index>=count:
        raise ValueError('Invalid container membership index')
    count-=1
    struct.pack_into('<I',provider,0x58,count)
    slots=arrays[_pointer(provider,0x50)]
    slots[original_index]=slots[count]
    owner=_pointer(container,0x20)
    struct.pack_into('<Q',container,0x20,0)
    struct.pack_into('<I',container,0x30,0xffffffff)
    struct.pack_into('<Q',container,0x28,0)
    if original_index<_u32(provider,0x58):
        moved=containers[arrays[_pointer(provider,0x50)][original_index]]
        struct.pack_into('<Q',moved,0x20,owner)
        struct.pack_into('<I',moved,0x30,original_index)
        struct.pack_into('<Q',moved,0x28,provider_token+8)


def process_pose_body_constraints(provider,body_token,output,*,constraints,bodies,
        metadata,arrays,get_kind,destroy,grow_output):
    """Unregister cross-owner edges, queue or destroy, then restart at body90.

    Evidence: LINK_SOLVER.md, Cross-owner body ring processing.
    grow_output(descriptor,capacity) implements the full descriptor growth helper.
    destroy(token,1) supplies the virtual deleting destructor. None means no output.
    Owner comparison is asymmetric: a zero second owner prevents removal, while
    a zero first owner does not. Metadata flags are reread after unregistration.
    """
    from .pose_endpoint_rings import detach_pose_endpoint_rings
    current=anchor=_pointer(bodies[body_token],0x90)
    while current:
        record=constraints[current]
        first=_pointer(record,8);second=_pointer(record,0x10)
        first_owner=_pointer(metadata[_pointer(bodies[first],0x30)],0x20)
        second_owner=_pointer(metadata[_pointer(bodies[second],0x30)],0x20) if second else 0
        if not second_owner or first_owner==second_owner:
            current=_pointer(record,0x20 if body_token==first else 0x30)
            if current==anchor:return
            continue
        unregister_pose_constraint(provider,current,arrays=arrays,get_kind=get_kind,
            detach=lambda t,s:detach_pose_endpoint_rings(t,s,records=constraints,bodies=bodies))
        if (output is not None
                and not metadata[_pointer(bodies[first],0x30)][0x52]&1
                and not metadata[_pointer(bodies[second],0x30)][0x52]&1):
            capacity=_u32(output,12)
            if _u32(output,8)==capacity:
                new_capacity=capacity*2 if capacity else 8
                if new_capacity>0x1fffffff:
                    raise ValueError('Output allocation size exceeds uint32 byte size')
                grow_output(output,new_capacity)
            count=_u32(output,8)
            arrays[_pointer(output,0)][count]=current
            struct.pack_into('<I',output,8,count+1)
        else:
            destroy(current,1)
        current=anchor=_pointer(bodies[body_token],0x90)
