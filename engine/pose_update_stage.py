"""Recovered phase3 orchestration around retained pose batches.

Evidence: LINK_SOLVER.md, Outer pose update stage.
"""
import struct


def _pointer(raw,offset):
    return struct.unpack_from('<Q',raw,offset)[0]


def run_pose_update_stage(owner_token, *, scalar, owners, contexts, collections,
                          arrays, prepare, get_body_source, update_bodies,
                          body_update_callback, begin_contacts, update_contacts,
                          finish_contacts, attach_links, publish_link,
                          get_settings, run_batches, notify_active):
    """Run native normal-return service order, reloading owner fields per use.

    Service contracts: prepare(owner_token, scalar); get_body_source(provider);
    update_bodies(source, scalar, callback); contact calls receive current contact
    owner (update additionally scalar); attach_links(context, array_token, count);
    publish_link(interface, link_plus8_or_null); get_settings(provider);
    run_batches(context, scalar, settings); notify_active(interface, null).
    The passed body_update_callback identifies the inspected callback, not a
    replacement implementation. No service runs implicitly outside this order.
    """
    owner=owners[owner_token]
    struct.pack_into('<I',owner,0x48,3)
    prepare(owner_token,scalar)
    source=get_body_source(_pointer(owner,0x20))
    update_bodies(source,scalar,body_update_callback)
    begin_contacts(_pointer(owner,0x40))
    update_contacts(_pointer(owner,0x40),scalar)
    finish_contacts(_pointer(owner,0x40))
    changed=collections[_pointer(owner,0x38)]
    attach_links(_pointer(owner,0x30),_pointer(changed,0x28),
                 struct.unpack_from('<I',changed,0x30)[0])
    context=contexts[_pointer(owner,0x30)]
    start,count=struct.unpack_from('<QI',context,0x490)
    for index in range(count):
        token=arrays[start][index]
        publish_link(_pointer(owner,0x28),(token+8)&0xffffffffffffffff if token else 0)
    settings=get_settings(_pointer(owner,0x20))
    run_batches(_pointer(owner,0x30),scalar,settings)
    context=contexts[_pointer(owner,0x30)]
    if struct.unpack_from('<I',context,0x420)[0]:
        notify_active(_pointer(owner,0x28),0)
    struct.pack_into('<I',owner,0x48,0)


def prepare_pose_constraint_collections(owner_token, *, scalar, owners,
                                        first_count, first_at, second_count,
                                        second_at, prepare_constraint):
    """Recovered two-collection preparation driver using float32 reciprocal dt.

    Count/getter services take the current owner20 provider. Counts are captured
    separately before each loop; provider is reloaded before every getter. The
    individual constraint preparation callback remains explicit. Floating-point
    status flags and NaN payloads are outside this arithmetic model.
    """
    import math
    value=struct.unpack('<f',struct.pack('<f',scalar))[0]
    if value==0:
        reciprocal=math.copysign(math.inf,value)
    else:
        result=1.0/value
        try:reciprocal=struct.unpack('<f',struct.pack('<f',result))[0]
        except OverflowError:reciprocal=math.copysign(math.inf,result)
    owner=owners[owner_token]
    count=first_count(_pointer(owner,0x20))
    for index in range(count):
        constraint=first_at(_pointer(owner,0x20),index)
        prepare_constraint(constraint,reciprocal)
    count=second_count(_pointer(owner,0x20))
    for index in range(count):
        constraint=second_at(_pointer(owner,0x20),index)
        prepare_constraint(constraint,reciprocal)
