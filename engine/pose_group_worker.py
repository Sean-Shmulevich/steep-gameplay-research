"""Recovered batch worker dispatch around group solve/free-motion services.

Evidence: LINK_SOLVER.md, Group batch worker admission.
"""
import struct


def claim_pose_batch_serial(context):
    """Serial equivalent of fetch-add at448; not a thread-safe atomic primitive."""
    old=struct.unpack_from('<I',context,0x448)[0]
    struct.pack_into('<I',context,0x448,(old+1)&0xffffffff)
    return old


def run_pose_group_worker(owner_token, job, *, contexts, batches, arrays, groups,
                           bodies, metadata, settings, claim, solve, advance_motion,
                           poststep, release):
    """Run the worker with an explicit atomic-claim service and mutable scratch.

    job supplies source context at0, scalar atc and settings pointer at10. claim
    receives owner_token and returns the previous uint32 index. solve receives a
    group token and one reused request dict: scalar/settings_token/buffer/capacity.
    Native allocator growth and synchronization remain supplied services.
    """
    source=contexts[struct.unpack_from('<Q',job,0)[0]]
    settings_token=struct.unpack_from('<Q',job,0x10)[0]
    captured_settings=settings[settings_token]
    request=dict(scalar=struct.unpack_from('<f',job,0xc)[0],settings_token=settings_token,
                 buffer=0,capacity=0)
    while True:
        index=claim(owner_token)
        if type(index) is not int or not 0<=index<=0xffffffff:
            raise ValueError('Unsigned prior claim index required')
        if index>=struct.unpack_from('<I',source,0x440)[0]:break
        start=struct.unpack_from('<Q',source,0x438)[0]
        batch=batches[start+16*index]
        count=struct.unpack_from('<I',batch,0)[0]
        for i in range(count):
            pointer=struct.unpack_from('<Q',batch,8)[0]
            token=arrays[pointer][i];group=groups[token]
            contacts=struct.unpack_from('<I',group,0x48)[0]
            poses=struct.unpack_from('<I',group,0x98)[0]
            if not captured_settings[0x20] and (contacts+poses)&0xffffffff:
                solve(token,request)
                continue
            start,count_bodies=struct.unpack_from('<QI',group,0x10)
            skip=False
            if count_bodies==1:
                body=bodies[arrays[start][0]]
                meta=metadata[struct.unpack_from('<Q',body,0x30)[0]]
                skip=bool(meta[0x52]&8)
            if not skip:advance_motion(start,start+count_bodies*8,request,settings_token+8)
            current_settings=settings[request['settings_token']]
            duration,linear,angular=struct.unpack_from('<3f',current_settings,0x34)
            poststep(token,request['scalar'],current_settings[0x14],duration,linear,angular)
    if request['buffer']:release(request['buffer'])
