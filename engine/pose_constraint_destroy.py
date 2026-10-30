"""Recovered base/kind4 constraint destruction and deleting flags.

Evidence: LINK_SOLVER.md, Constraint destructor and release flags.
"""
import struct
from .pose_endpoint_rings import detach_pose_endpoint_rings


def destroy_pose_constraint(token,flags,*,records,bodies,base_tables,final_tables,
        get_callback_manager,managers,invoke,release):
    """Run base destruction and the inspected deleting-wrapper policy.

    Tables are supplied build-specific identities for offsets0 and40.
    get_callback_manager() is queried only when byte5a is nonzero. Its manager28
    callback receives (token,1,userdata50), through invoke(fn,token,1,userdata).
    release(token) supplies the allocator's virtual free. It runs only when
    flags bit0 is set and bit2 is clear, after final table publication.
    Returns the token, including after release, matching the native wrapper.
    This is not idempotent and does not unregister provider list membership.
    """
    record=records[token]
    linked=struct.unpack_from('<Q',record,0x20)[0]!=0
    struct.pack_into('<Q',record,0,base_tables[0])
    struct.pack_into('<Q',record,0x40,base_tables[1])
    if linked:detach_pose_endpoint_rings(token,2,records=records,bodies=bodies)
    if record[0x5a]:
        userdata=struct.unpack_from('<Q',record,0x50)[0]
        manager=managers[get_callback_manager()]
        callback=struct.unpack_from('<Q',manager,0x28)[0]
        if callback:invoke(callback,token,1,userdata)
    # Both observed calls to the alternate cleanup target are return-only stubs.
    struct.pack_into('<Q',record,0x40,final_tables[1])
    struct.pack_into('<Q',record,0,final_tables[0])
    if flags&1 and not flags&4:release(token)
    return token
