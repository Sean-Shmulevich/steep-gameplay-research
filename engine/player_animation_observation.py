"""Compose skeleton identity and bounded pose observations. No process access.

Caller supplies a verified player entity, build profile and read transport.
Matching endpoint reads neither pin lifetime nor exclude ABA or concurrent writes.
"""
import struct
from .scheduler_observation import _address
from .skeleton_observation import capture_skeleton_binding
from .pose_channel_observation import capture_pose_interval


def _capture_player_component(readv, entity, image_base, guards, profile, observe):
    """Return address-free skeleton/pose facts guarded across the combined read.

    At most 12 caller guards leave space for four retained binding guards.
    No game calls, debugger, writes, acquisition or scheduler control occurs.
    """
    guards=list(guards)
    if not 1<=len(guards)<=12:raise ValueError('provide 1..12 external identity guards')
    _address(entity,0x1fa)
    def read(plan):
        rows=list(readv(plan))
        if len(rows)!=len(plan) or any(type(row) is not bytes or len(row)!=size
                                      for row,(_,size) in zip(rows,plan)):
            raise ValueError('incomplete animation binding read')
        return rows
    header=read([(entity+0x88,12)])[0]
    binding_guards=guards+[(entity+0x88,header)]
    before=capture_skeleton_binding(readv,entity,image_base,binding_guards,profile,
                                     include_provider_bank=False)
    if before['binding_status']!='unique_exact_type' or not before['owner_backlink_matches']:
        raise ValueError('unique owned skeleton binding required')
    array=struct.unpack_from('<Q',header)[0];index=before['exact_type_indices'][0]
    slot=_address(array+index*8,8);slot_value=read([(slot,8)])[0]
    component=struct.unpack('<Q',slot_value)[0];_address(component,0xc5c)
    table,owner=read([(component,8),(component+0x10,8)])
    if struct.unpack('<Q',table)[0]!=image_base+profile['skeleton_table'] or struct.unpack('<Q',owner)[0]!=entity:
        raise ValueError('skeleton binding changed before pose observation')
    binding_guards.extend([(slot,slot_value),(component,table),(component+0x10,owner)])
    observation=observe(component,binding_guards)
    after=capture_skeleton_binding(readv,entity,image_base,binding_guards,profile,
                                    include_provider_bank=False)
    if before!=after:raise ValueError('skeleton binding changed across pose observation')
    return before,observation


def _result(schema, binding, key, observation):
    return dict(schema=schema,binding=binding,**{key:observation},
                guards_matched=True,atomic_snapshot=False,lifetime_pinned=False,
                animation_completion_established=False,live_player_acquisition=False,
                evidence='composed passive observation; caller-verified entity and build',
                suitable_for_animation_writes=False)


def capture_player_animation(readv, entity, image_base, keys, guards, profile,
                             record_count=None):
    binding,pose=_capture_player_component(readv,entity,image_base,guards,profile,
        lambda component,retained:capture_pose_interval(readv,component,keys,record_count,retained))
    return _result('player-animation-observation-v1',binding,'pose',pose)


def capture_player_cached_parent(readv, entity, image_base, guards, profile,
                                 code_ranges=()):
    """Resolve a unique owned skeleton and bracket callback/cached-parent reads.

    Caller must still supply a freshly verified player entity and read transport.
    No player acquisition, native invocation or lifetime retention is implemented.
    """
    from .cached_parent_observation import capture_cached_parent
    binding,observation=_capture_player_component(readv,entity,image_base,guards,profile,
        lambda component,retained:capture_cached_parent(readv,component,entity,
            image_base+profile['skeleton_table'],retained,code_ranges))
    return _result('player-cached-parent-observation-v1',binding,'cached_parent',observation)
