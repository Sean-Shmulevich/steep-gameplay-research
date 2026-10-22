"""Recovered hierarchy rank assignment from per-key overrides.

Evidence: CENTRAL_IMPULSE.md, Hierarchy rank producer.
Owner/type names and override-table semantics remain unresolved.
"""

def assign_hierarchy_ranks(flags, keys, overrides, owner_visible, owner_value):
    if type(owner_visible) is not bool or type(owner_value) is not int or not 0<=owner_value<=0xffffffff:
        raise ValueError('visible predicate and uint32 owner value required')
    if len(flags)!=len(keys):raise ValueError('one key per metadata flag required')
    default=5 if owner_visible and owner_value<=1 else 1
    result=[]
    for flag,key in zip(flags,keys):
        if type(flag) is not int or not 0<=flag<=255 or type(key) is not int or not 0<=key<=0xffffffff:
            raise ValueError('uint8 flags and uint32 keys required')
        value=overrides.get(key,default)
        if type(value) is not int or not 0<=value<=0xffffffff:raise ValueError('uint32 override required')
        result.append((flag&0x8f)|((value&7)<<4))
    return dict(default=default,flags=result,ranks=[(v>>4)&7 for v in result])


def choose_authority_preset(owner_visible, owner_value, toe_present, alternate_value):
    """Recovered predicates; numeric owner selectors remain unnamed."""
    if owner_visible and owner_value<=1:
        return 'extended' if toe_present else 'standard'
    return 'alternate' if alternate_value==2 else None


def mark_authority_channels(flags, selected_keys, lookup):
    """OR direction bit and collect resolved uint16 indices, in table order."""
    result=list(flags);selected=[]
    for key in selected_keys:
        index=lookup(key)
        if index==65535:continue
        if type(index) is not int or not 0<=index<len(result):
            raise ValueError('resolved channel outside supplied metadata')
        result[index] |= 8
        selected.append(index)
    return dict(flags=result,selected=selected)


def resolve_authority_channels(flags, runtime_entries, owner_entries,
                               owner_visible, owner_value, preset_keys):
    """Stable-owner selection through two distinct sorted lookup tables.

    Both lookups use unsigned lower_bound and the first equal key's low uint16.
    Owner data answers the toe-existence predicate; runtime data maps selected
    keys to assembled channel indices. The numeric selector is read from the
    same owner on the alternate branch, with 8 when no owner is visible.
    """
    from reference.ground_response_pose import pose_channel_index
    toe=owner_visible and pose_channel_index(owner_entries,0xb95094e1)!=65535
    preset=choose_authority_preset(owner_visible,owner_value,toe,
                                  owner_value if owner_visible else 8)
    keys=preset_keys[preset] if preset is not None else []
    result=mark_authority_channels(flags,keys,lambda key:pose_channel_index(runtime_entries,key))
    result['preset']=preset
    return result


def build_source_metadata(source_records, selector, initial_flags):
    """Initial empty-table builder's source-to-runtime metadata projection.

    Unknown record bytes remain outside this structured result. No asset parsing,
    allocation, merge/reindex path or semantic naming of link modes is implied.
    """
    if type(selector) is not int or not 0<=selector<=255 or len(source_records)!=len(initial_flags) or len(source_records)>65535:
        raise ValueError('uint8 selector and matching bounded record arrays required')
    rows=[]
    for i,(source,flag) in enumerate(zip(source_records,initial_flags)):
        for name in ('source_index','skip_span'):
            if type(source[name]) is not int or not 0<=source[name]<=65535:raise ValueError('uint16 source field required')
        for name in ('key','link_mode'):
            if type(source[name]) is not int or not 0<=source[name]<=0xffffffff:raise ValueError('uint32 source field required')
        if type(flag) is not int or not 0<=flag<=255:raise ValueError('uint8 flags required')
        parent=65535 if i==0 else source['parent_index']
        linked=source['linked_index']
        if type(parent) is not int or not 0<=parent<=65535:raise ValueError('uint16 parent index required')
        if linked is not None and (type(linked) is not int or not 0<=linked<=65535):raise ValueError('optional uint16 linked index required')
        packed=(flag&0xf8)|((source['link_mode']&7) if linked is not None else 0)
        rows.append(dict(parent=parent,skip_span=source['skip_span'],source_index=source['source_index'],
            linked_index=i if linked is None else linked,selector=selector,flags=packed,key=source['key']))
    return dict(rows=rows,keys=[r['key'] for r in rows])


def initialize_metadata_record(backing):
    """Initialize only the fields written by the recovered native leaf."""
    import struct
    backing=bytes(backing)
    if len(backing)!=32:raise ValueError('exactly 32 backing bytes required')
    result=bytearray(backing)
    struct.pack_into('<H',result,0,65535)
    struct.pack_into('<I',result,2,0)
    struct.pack_into('<I',result,6,0x0f00ffff)
    result[10]=(result[10]&0x90)|0x10
    struct.pack_into('<Q',result,16,0)
    return bytes(result)


def resize_metadata_in_capacity(backing_records, old_count, new_count):
    """Existing-capacity resize; shrink does not erase inactive records."""
    records=[bytes(r) for r in backing_records]
    if any(len(r)!=32 for r in records) or any(type(n) is not int or not 0<=n<=len(records) for n in (old_count,new_count)) or len(records)>16383:
        raise ValueError('bounded counts and 32-byte records required')
    for i in range(old_count,new_count):records[i]=initialize_metadata_record(records[i])
    return dict(records=records,count=new_count)
