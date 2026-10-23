"""Inspectable synthetic allocation-metadata lifecycle, with no game dependencies.

The driver orders registration, authored tag placement, retirement and removal.
That schedule and the fallback metadata are fixtures, not a recovered allocator.
"""
import json
from engine.allocation_metadata_registry import register_metadata
from engine.allocation_metadata_lookup import lookup_allocation_metadata
from engine.allocation_region_retirement import retire_metadata_regions
from engine.allocation_region_release import release_metadata_region
from engine.allocation_context_release import release_context_region
from engine.allocation_metadata_removal import unregister_metadata


def run_probe(*, target_result=1):
    events=[];depth=0;maximum=0
    fallback_record=dict(name='fallback',index=0,field10=0)
    record=dict(name='selected',index=255,field10=131072)
    a=bytearray([255])*65536;b=bytearray([255])*65536
    registry=dict(entries=[fallback_record]+[None]*126,default=0,observers=[],
                  regions={0:a,1:b},override=None)
    def lock(_):
        nonlocal depth,maximum
        depth+=1;maximum=max(maximum,depth);events.append(dict(event='lock',depth=depth))
    def unlock(_):
        nonlocal depth
        depth-=1;events.append(dict(event='unlock',depth=depth))
    services=dict(lock=lock,unlock=unlock,notify_object=lambda *_:0,notify_function=lambda *_:0)
    registered=register_metadata(registry,record,**services)
    # Region assignment is an authored fixture; its native producer is not used.
    a[-1]=record['index'];b[0]=record['index']|128
    address=65535<<16
    def lookup():
        value=lookup_allocation_metadata(address,read_region=lambda high:registry['regions'].get(high),
            read_entry=lambda index:registry['entries'][index],default_index=lambda:registry['default'])
        return None if value is None else value['name']
    before=dict(lookup=lookup(),index=record['index'],accounting=record['field10'],tags=[a[-1],b[0]])
    def target(addr,size,operation):
        events.append(dict(event='external_target',address=addr,size=size,operation=operation,
            returned=target_result,depth=depth,tags=[a[-1],b[0]],accounting=record['field10']))
        return target_result
    def context(_,addr,size,flags):
        return release_context_region(addr,size,flags,invoke=target)
    def release(*args):
        return release_metadata_region(*args,lock=lock,unlock=unlock,release_context=context)
    retired=retire_metadata_regions(registry,record,'synthetic-context',lock=lock,unlock=unlock,
        ensure_initialized=lambda:None,address_limit=lambda:2<<32,fallback=release)
    after_retirement=dict(lookup=lookup(),index=record['index'],accounting=record['field10'],tags=[a[-1],b[0]])
    unregister_metadata(registry,record,**services)
    return dict(evidence='Synthetic serial composition of reconstructed local routines',
        assumptions=['Authored region tags and registration/retirement/removal schedule.',
                     'Retained tables, metadata, observer list and context; supplied recursive locks.',
                     'External target only records calls and returns a supplied value.'],
        registered=registered,before=before,retirement=retired,after_retirement=after_retirement,
        after_removal=dict(lookup=lookup(),index=record['index'],entry_cleared=registry['entries'][1] is None),
        maximum_lock_depth=maximum,final_lock_depth=depth,events=events,
        native_release_proved=False,safe_unload_proved=False)


if __name__=='__main__':
    print(json.dumps({str(value):run_probe(target_result=value) for value in (0,1)},indent=2))
