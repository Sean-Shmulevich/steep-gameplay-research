"""Synthetic explicit-service allocation, release and reuse; no game access."""
import json
from reference.animation_bank_pool import acquire_pose_bank,release_pose_bank
from reference.animation_bank_copy import copy_pose_bank


def run():
    entries=[];events=[]
    profile=dict(total_size=85,bulk_boundaries=[32,48,85],group_count=1,
        group_words=[0,1,1,1,1,1,1,1,1],descriptors=[dict(offset=16,kind=4)])
    source=dict(parent_header=bytes([99])*32,data=bytes(range(85)),profile=profile)
    def reserve(count):events.append(['reserve',count]);return bytes(16)
    def allocate_bank(size,alignment):events.append(['allocate_bank',size,alignment]);return dict(flags=0)
    def allocate_data(size):events.append(['allocate_data',size]);return bytearray(size)
    def copy(dst,src,mode,mask):events.append(['copy',mask]);return copy_pose_bank(dst,src,mode,mask)
    services=dict(profile=profile,default_transform=bytes(32),reserve_slot=reserve,
        allocate_bank=allocate_bank,allocate_data=allocate_data,copy_selected=copy)
    first=acquire_pose_bank(entries,65535,0,0,source,**services)
    bank=first['bank']
    release_pose_bank(entries,bank,65535,lambda _:events.append('clear_auxiliary'))
    second=acquire_pose_bank(entries,1,0,0,source,**services)
    return dict(evidence='synthetic allocation services with reconstructed lifecycle',
        created_first=first['created'],created_second=second['created'],
        same_bank=second['bank'] is bank,data_matches=bytes(bank['data'])==source['data'],
        pool_count=len(entries),flags=bank['flags'],events=events)


if __name__=='__main__':print(json.dumps(run(),indent=2))
