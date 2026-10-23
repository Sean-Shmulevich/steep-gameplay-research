"""Normal-return retirement service with supplied synchronization and consumers.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, Post-unlock payload destruction service.
No native synchronization, destructor, allocator or scheduler drain is provided.
"""


def run_retirement_service(registry, *, lock, unlock, prepare, consume,
                           allocation_lookup, destroy_payload, free_storage):
    """Collect under locks, conditionally destroy payloads, then free owned output.

    consume(registry, output) fills slots/count/storage/flags. Initial output has
    20 inline slots, count zero and flags 0x80000014. Services must keep storage
    valid for the captured traversal; callback modifications to mode are allowed.
    Free takes (token, info). Array ownership is flags bit30, separate from mode.
    Normal-return only; no exception unlock or rollback guarantee is invented.
    """
    inline=[None]*20
    output=dict(slots=inline,storage=inline,count=0,flags=0x80000014)
    lock('registry_60');lock('global_1d8');lock('registry_b8')
    prepare(registry)
    consume(registry,output)
    unlock('global_1d8');unlock('registry_60');unlock('registry_b8')
    slots=output['slots']
    destroyed=0
    if registry['mode']==1:
        count=output['count']
        for i in range(count):
            payload=slots[i]
            if payload is not None:
                info=allocation_lookup(payload)
                destroy_payload(payload,0)
                free_storage(payload,info)
                destroyed+=1
    array_freed=False
    if output['flags'] & (1<<30) and output['storage'] is not None:
        info=allocation_lookup(output['storage'])
        free_storage(output['storage'],info)
        array_freed=True
    return dict(payloads_destroyed=destroyed,output_storage_freed=array_freed)
