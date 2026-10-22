"""Recovered typed animation-bank copy; supplied synthetic storage only."""


def copy_typed_channels(storage, source_base, destination_base, entries, first, count, flags):
    """Copy an ordered descriptor range and set destination flag bit 27.

    Entries are (uint16 byte_offset, uint16 type_word). Low type nibble selects
    width: 0 -> 1 byte, 1..3 -> 4, 4 -> three ordered 4-byte copies, 5..15 -> 16.
    Shared storage preserves overlapping source/destination behavior. Validation
    and immutable input are authored API policy; the native routine has no bounds
    checks and mutates the destination as it goes. Type names remain unproven.
    """
    if type(storage) is not bytes or len(storage) > 1048576:
        raise ValueError('at most 1 MiB supplied byte storage required')
    if any(type(v) is not int or v < 0 for v in (source_base, destination_base, first, count)):
        raise ValueError('nonnegative integer ranges required')
    if first >= 2**32 or count >= 2**32:
        raise ValueError('uint32 descriptor range required')
    if type(flags) is not int or not 0 <= flags < 2**32:
        raise ValueError('uint32 destination flags required')
    if not isinstance(entries, (list, tuple)) or len(entries) > 65535:
        raise ValueError('bounded descriptor list required')
    if first + count > len(entries):
        raise ValueError('descriptor range exceeds supplied list')
    plan = []
    for row in entries[first:first + count]:
        if not isinstance(row, (list, tuple)) or len(row) != 2 or any(
                type(v) is not int or not 0 <= v <= 65535 for v in row):
            raise ValueError('uint16 offset/type pairs required')
        offset, kind = row[0], row[1] & 15
        widths = [1] if kind == 0 else [4] if kind < 4 else [4, 4, 4] if kind == 4 else [16]
        size = sum(widths)
        if max(source_base, destination_base) + offset + size > len(storage):
            raise ValueError('channel exceeds supplied storage')
        if kind >= 5 and ((source_base + offset) % 16 or (destination_base + offset) % 16):
            raise ValueError('16-byte channel requires aligned logical bases and offset')
        plan.append((offset, widths))
    output = bytearray(storage)
    for offset, widths in plan:
        for width in widths:
            src, dst = source_base + offset, destination_base + offset
            output[dst:dst + width] = output[src:src + width]
            offset += width
    return dict(storage=bytes(output), flags=flags | (1 << 27), copied_channels=count)


def select_channel_copy(mode, weight, group_mask, selector, total_count, groups):
    """Recovered copy branches of the bank-combination routine, modes 1..3.

    Source labels refer to first/second input bank. Other modes perform arithmetic
    and are deliberately outside this selector. Group mask chooses its highest
    set bit, with zero also selecting row zero; 0xffff means the entire table.
    Each supplied group is (first, six selector counts). Shape bounds are authored.
    """
    import math
    from reference.central_impulse import f32
    if type(mode) is not int or mode not in (1, 2, 3):
        raise ValueError('copy mode 1, 2 or 3 required')
    if type(group_mask) is not int or not 0 <= group_mask <= 65535:
        raise ValueError('uint16 group mask required')
    if type(total_count) is not int or not 0 <= total_count <= 65535:
        raise ValueError('uint16 total descriptor count required')
    if type(weight) not in (int, float):
        raise ValueError('numeric weight required')
    weight = f32(weight)
    source = 'first' if mode == 2 or (mode == 1 and not math.isnan(weight) and weight < 0.5) else 'second'
    if group_mask == 65535:
        return dict(source=source, first=0, count=total_count, group_index=None)
    if type(selector) is not int or not 0 <= selector <= 5:
        raise ValueError('selector must address one of six group counts')
    index = max(0, group_mask.bit_length() - 1)
    if not isinstance(groups, (list, tuple)) or index >= len(groups):
        raise ValueError('missing selected group row')
    row = groups[index]
    if not isinstance(row, (list, tuple)) or len(row) != 7 or any(
            type(v) is not int or not 0 <= v <= 65535 for v in row):
        raise ValueError('seven uint16 values required per group row')
    first, count = row[0], row[selector + 1]
    if first + count > total_count:
        raise ValueError('selected group exceeds supplied descriptor count')
    return dict(source=source, first=first, count=count, group_index=index)


def combine_float_channel(first, second, weight, kind, mode):
    """Recovered float branches of mode-0/4 helpers, supplied channel values.

    Evidence: CENTRAL_IMPULSE.md, Float channel arithmetic in bank combination.
    Kind 1 is scalar; kind 5 has four lanes. Other kinds are not decoded here.
    Caller routing, descriptor traversal and bank flags remain external.
    """
    import math
    from reference.central_impulse import f32
    if type(kind) is not int or kind not in (1, 5):
        raise ValueError('only recovered float kinds 1 and 5 supported')
    if type(mode) is not int or mode not in (0, 4):
        raise ValueError('only arithmetic modes 0 and 4 supported')
    width = 1 if kind == 1 else 4
    if len(first) != width or len(second) != width:
        raise ValueError('channel lane count does not match kind')
    a, b = tuple(map(f32, first)), tuple(map(f32, second))
    w = f32(weight)
    if not all(math.isfinite(x) for x in (*a, *b, w)):
        raise ValueError('finite channel inputs required')
    if mode == 4 and kind == 5:
        return tuple(f32(f32(w*y)+x) for x,y in zip(a,b))
    return tuple(f32(f32(f32(y-x)*w)+x) for x,y in zip(a,b))


def plan_arithmetic_channel_route(mode, weight, swap, type_words, exclusion_mask=0):
    """Recovered selector-2 routing over an already selected descriptor range.

    Evidence: CENTRAL_IMPULSE.md, Arithmetic near-one routing.
    Labels describe helper calls, not animation states. No storage is changed.
    """
    import math
    from reference.central_impulse import f32
    if type(mode) is not int or mode not in (0, 4) or type(swap) is not bool:
        raise ValueError('mode 0/4 and boolean swap required')
    if type(exclusion_mask) is not int or not 0 <= exclusion_mask < 2**32:
        raise ValueError('uint32 exclusion mask required')
    if any(type(t) is not int or not 0 <= t <= 65535 for t in type_words):
        raise ValueError('uint16 type words required')
    w = f32(weight)
    if not math.isfinite(w): raise ValueError('finite weight required')
    near = abs(f32(w - 1.0)) <= f32(1e-5)
    if mode == 0:
        helper = 'copy_second' if near else 'interpolate'
        sources = ['second'] if near else ['first', 'second']
    else:
        helper = 'unweighted_combine' if near else 'weighted_combine'
        sources = ['first', 'second'] if swap else ['second', 'first']
    return dict(near_one=near, helper=helper, sources=sources,
                indices=[i for i,t in enumerate(type_words)
                         if not (exclusion_mask & (1 << (t & 15)))])


def combine_unweighted_channel(first, second, previous, kind):
    """Recovered near-one mode-4 helper on supplied channel values.

    Evidence: CENTRAL_IMPULSE.md, Unweighted typed channel combination.
    Unsupported native kinds leave destination unchanged; no normalization.
    Shape checks are authored. Caller routing and storage aliasing are external.
    """
    import math
    from reference.central_impulse import f32
    if type(kind) is not int or not 0 <= kind <= 15:
        raise ValueError('decoded low-nibble kind required')
    if kind not in (0, 1, 5, 6): return tuple(previous)
    width = 1 if kind in (0, 1) else 4
    if len(first) != width or len(second) != width:
        raise ValueError('channel lane count mismatch')
    if kind == 0:
        if any(type(x) is not int or not 0 <= x <= 255 for x in (*first, *second)):
            raise ValueError('uint8 channel required')
        return ((first[0] + second[0]) & 255,)
    a, b = tuple(map(f32, first)), tuple(map(f32, second))
    if not all(math.isfinite(x) for x in (*a, *b)):
        raise ValueError('finite channel inputs required')
    if kind in (1, 5): return tuple(f32(x+y) for x,y in zip(a,b))
    x,y,z,w = a
    result = tuple(f32(w*n) for n in b)
    for coefficients, values in [((x,-x,x,-x),(b[3],b[2],b[1],b[0])),
                                  ((y,y,-y,-y),(b[2],b[3],b[0],b[1])),
                                  ((-z,z,z,-z),(b[1],b[0],b[3],b[2]))]:
        result = tuple(f32(old+f32(c*n)) for old,c,n in zip(result,coefficients,values))
    return result


def combine_float_channel_batch(first, second, previous, kinds, mode, weight,
                                swap=False, exclusion_mask=0):
    """Float-only compatibility API; see Joined float bank update evidence."""
    if any(type(k) is not int or k not in (1,5) for k in kinds):
        raise ValueError('float kinds 1 and 5 required')
    return combine_numeric_channel_batch(first,second,previous,kinds,mode,weight,
                                         swap,exclusion_mask)


def combine_numeric_channel_batch(first, second, previous, kinds, mode, weight,
                                swap=False, exclusion_mask=0, reciprocal_sqrt=None):
    """Compose recovered selector-2 routing and float-kind helpers.

    Evidence: CENTRAL_IMPULSE.md, Joined mixed numeric bank update.
    Supplied nonaliasing value arrays; descriptor range is already selected.
    Supplemental records and bank status effects are outside this value API.
    """
    if not (len(first) == len(second) == len(previous) == len(kinds)):
        raise ValueError('matching channel arrays required')
    if any(type(k) is not int or k not in (1, 5, 6) for k in kinds):
        raise ValueError('joined path currently supports numeric kinds 1, 5 and 6')
    route = plan_arithmetic_channel_route(mode, weight, swap, kinds, exclusion_mask)
    output = [tuple(x) for x in previous]
    banks = dict(first=first, second=second)
    for i in route['indices']:
        sources = [banks[name][i] for name in route['sources']]
        if route['helper'] == 'copy_second':
            from reference.central_impulse import f32
            output[i] = tuple(map(f32, sources[0]))
        elif route['helper'] == 'unweighted_combine':
            output[i] = combine_unweighted_channel(*sources, previous[i], kinds[i])
        elif kinds[i] == 6:
            if not callable(reciprocal_sqrt):
                raise ValueError('weighted quaternion requires an explicit seed service')
            output[i] = combine_rotation_channel(*sources,weight,mode,reciprocal_sqrt)
        else:
            output[i] = combine_float_channel(*sources, weight, kinds[i], mode)
    return dict(channels=output, route=route)


def combine_rotation_channel(first, second, weight, mode, reciprocal_sqrt):
    """Recovered weighted kind-6 helpers with explicit normalization seed service.

    Evidence: CENTRAL_IMPULSE.md, Weighted quaternion bank channels.
    Outer near-one routing and source swapping must be applied by the caller.
    """
    from reference.supplemental_pose_records import (
        blend_supplemental_rotation, polynomial_rotation_blend)
    if type(mode) is not int or mode not in (0,4):
        raise ValueError('weighted mode 0 or 4 required')
    if mode==0:
        return tuple(blend_supplemental_rotation(first,second,weight,reciprocal_sqrt,
            lambda a,b,w: polynomial_rotation_blend(a,b,w,reciprocal_sqrt))['rotation'])
    weighted=polynomial_rotation_blend([0,0,0,1],second,weight,reciprocal_sqrt)
    return combine_unweighted_channel(first,weighted,[],6)


def evaluate_numeric_pose_bank(first, second, previous, kinds, mode, weight,
                               first_records, second_records, previous_records,
                               swap=False, exclusion_mask=0, reciprocal_sqrt=None, flags=0, group_mask=65535,
                               groups=None, range_selector=0):
    """Joined selector-2 modes 0/4 numeric channels and supplemental records.

    Evidence: CENTRAL_IMPULSE.md, Mixed channels with supplemental evaluation.
    Inputs are supplied nonaliasing values; allocation and status flags external.
    """
    from copy import deepcopy
    from reference.supplemental_pose_records import evaluate_supplemental_records
    if not len(first)==len(second)==len(previous)==len(kinds):
        raise ValueError('matching full channel arrays required')
    selection=select_channel_copy(2,0,group_mask,range_selector,len(kinds),groups)
    start=selection['first'];end=start+selection['count']
    result=combine_numeric_channel_batch(first[start:end],second[start:end],
        previous[start:end],kinds[start:end],mode,weight,swap,exclusion_mask,reciprocal_sqrt)
    channels=[tuple(x) for x in previous]
    channels[start:end]=result['channels'];result['channels']=channels
    result['route']['indices']=[start+i for i in result['route']['indices']]
    result['range']={key:selection[key] for key in ('first','count','group_index')}
    result['flags']=numeric_bank_status_after(flags,result['route'])
    result['records']=(evaluate_supplemental_records(first_records,second_records,
        previous_records,weight,reciprocal_sqrt) if mode==0 else deepcopy(previous_records))
    return result


def numeric_bank_status_after(flags, route):
    """Recovered selector-2 mode-0/4 status effect, excluding other entry modes.

    Evidence: CENTRAL_IMPULSE.md, Numeric bank status is path dependent.
    Route must come from plan_arithmetic_channel_route for this operation.
    """
    if type(flags) is not int or not 0<=flags<2**32:
        raise ValueError('uint32 status required')
    return flags | (1<<27) if route['helper']=='copy_second' and route['indices'] else flags


def evaluate_float_bank_storage(storage, first_base, second_base, destination_base,
                                descriptors, mode, weight, swap=False,
                                exclusion_mask=0, flags=0):
    """Recovered ordered scalar/vector bank writes over shared synthetic storage.

    Evidence: CENTRAL_IMPULSE.md, Aliased float bank storage.
    Descriptors are preselected (offset, kind) pairs. No supplemental records.
    """
    import struct
    if type(storage) is not bytes:raise ValueError('immutable supplied bytes required')
    bases=(first_base,second_base,destination_base)
    if any(type(b) is not int or b<0 for b in bases):raise ValueError('nonnegative bases required')
    for offset,kind in descriptors:
        if type(offset) is not int or not 0<=offset<=65535 or kind not in (1,5):
            raise ValueError('uint16 offsets and float kinds 1/5 required')
        width=4 if kind==1 else 16
        if max(bases)+offset+width>len(storage):raise ValueError('descriptor outside supplied storage')
        if kind==5 and any((base+offset)%16 for base in bases):raise ValueError('aligned vector storage required')
    route=plan_arithmetic_channel_route(mode,weight,swap,[k for _,k in descriptors],exclusion_mask)
    output=bytearray(storage);source_bases=dict(first=first_base,second=second_base)
    for i in route['indices']:
        offset,kind=descriptors[i];fmt='<f' if kind==1 else '<4f';width=struct.calcsize(fmt)
        sources=[struct.unpack_from(fmt,output,source_bases[name]+offset) for name in route['sources']]
        if route['helper']=='copy_second':
            # Copy bit patterns without a float round trip.
            src=second_base+offset;output[destination_base+offset:destination_base+offset+width]=output[src:src+width];continue
        if route['helper']=='unweighted_combine':values=combine_unweighted_channel(*sources,[],kind)
        else:values=combine_float_channel(*sources,weight,kind,mode)
        struct.pack_into(fmt,output,destination_base+offset,*values)
    return dict(storage=bytes(output),flags=numeric_bank_status_after(flags,route),route=route)


def plan_bank_group_calls(mode, group_mask, group_count, weight, range_selector,
                          exclusion_mask=0, swap=False):
    """Recovered mode-0/4 wrappers expanding masks into ordered inner calls.

    Evidence: CENTRAL_IMPULSE.md, Outer wrappers expand group masks.
    Group count <=16 is an authored domain bound; metadata mutation unmodeled.
    """
    from reference.central_impulse import f32
    if type(mode) is not int or mode not in (0,4):raise ValueError('mode 0/4 required')
    if type(group_mask) is not int or not 0<=group_mask<=65535:raise ValueError('uint16 mask required')
    if type(group_count) is not int or not 0<=group_count<=16:raise ValueError('bounded group count required')
    if type(range_selector) is not int or not 0<=range_selector<=5:raise ValueError('range selector 0..5 required')
    if type(exclusion_mask) is not int or not 0<=exclusion_mask<2**32:raise ValueError('uint32 exclusion required')
    if type(swap) is not bool:raise ValueError('boolean swap required')
    masks=[65535] if group_mask==65535 else [1<<i for i in range(group_count) if group_mask&(1<<i)]
    return [dict(mode=mode,group_mask=m,weight=f32(weight),range_selector=range_selector,
                 exclusion_mask=exclusion_mask,arithmetic_selector=2,
                 swap_control=2 if mode==0 else int(swap)) for m in masks]


def evaluate_grouped_pose_bank(first, second, previous, kinds, mode, weight,
                               first_records, second_records, previous_records,
                               group_mask, group_count, groups, range_selector=0,
                               swap=False, exclusion_mask=0, flags=0, reciprocal_sqrt=None):
    """Recovered stable-metadata outer wrapper with sequential inner updates.

    Evidence: CENTRAL_IMPULSE.md, Complete grouped wrapper evaluation.
    Supplied value arrays do not represent native storage aliases.
    """
    from copy import deepcopy
    calls=plan_bank_group_calls(mode,group_mask,group_count,weight,range_selector,
                                exclusion_mask,swap)
    channels=deepcopy(previous);records=deepcopy(previous_records);trace=[]
    for call in calls:
        result=evaluate_numeric_pose_bank(first,second,channels,kinds,mode,weight,
            first_records,second_records,records,swap,exclusion_mask,reciprocal_sqrt,
            flags,call['group_mask'],groups,range_selector)
        channels=result['channels'];records=result['records'];flags=result['flags']
        trace.append(dict(group_mask=call['group_mask'],range=result['range'],route=result['route']))
    return dict(channels=channels,records=records,flags=flags,calls=trace)


def plan_pose_operation_route(operation_kind, special_ready, stored_mask, requested_mask,
                              first_kind, second_kind, component_flags, weight):
    """Recovered caller routing before bank wrapper and operation-specific tail.

    Evidence: CENTRAL_IMPULSE.md, Pose operation selects blend family.
    Logical kind labels are unknown; special service remains external.
    """
    from reference.central_impulse import f32
    if any(type(x) is not int or not 0<=x<=255 for x in (operation_kind,first_kind,second_kind)):
        raise ValueError('uint8 operation and source kinds required')
    if any(type(x) is not int or not 0<=x<=65535 for x in (stored_mask,requested_mask,component_flags)):
        raise ValueError('uint16 masks and component flags required')
    if type(special_ready) is not bool:raise ValueError('boolean readiness required')
    mask=stored_mask & requested_mask;w=f32(weight)
    if operation_kind & 7 == 5 and special_ready:
        return dict(route='special',weight=w,group_mask=mask,weight_written=False)
    selector=(component_flags>>3)&7
    if first_kind==second_kind:
        return dict(route='mode_0',weight=w,group_mask=mask,range_selector=selector,
                    weight_written=False,exclusion_mask=0)
    changed=first_kind!=0 and second_kind==0
    if changed:w=f32(1-w)
    return dict(route='mode_4',weight=w,group_mask=mask,range_selector=selector,
                swap=not changed,weight_written=changed,exclusion_mask=0)


def pose_command_source_kinds(flags):
    """Recovered type-1 command's two source-kind bits.

    Evidence: CENTRAL_IMPULSE.md, Pose command record reaches blend routing.
    Names describe call positions, not established gameplay semantics.
    """
    if type(flags) is not int or not 0<=flags<=255:raise ValueError('uint8 command flags required')
    return dict(first_kind=flags & 1,second_kind=(flags>>1)&1)


def release_pose_bank_groups(entry_masks, entry_banks, target, requested_mask,
                             bank_flags, supplemental_mask, supplemental_counter):
    """Recovered manager match/mask/counter transition; storage reset is an effect.

    Evidence: CENTRAL_IMPULSE.md, Manager group release sets provider conversion flag.
    Logical identities and effect output are authored API; no native release occurs.
    """
    if len(entry_masks)!=len(entry_banks):raise ValueError('matching entry arrays required')
    if any(type(x) is not int or not 0<=x<=65535
           for x in [*entry_masks,requested_mask,supplemental_mask,supplemental_counter]):
        raise ValueError('uint16 masks and counter required')
    if type(bank_flags) is not int or not 0<=bank_flags<2**32:raise ValueError('uint32 flags required')
    masks=list(entry_masks);index=next((i for i,b in enumerate(entry_banks) if b==target),None)
    reset=False
    if index is not None:
        bank_flags |= 1<<26
        masks[index] &= ((~requested_mask)&65535)|0x8000
        if supplemental_mask & requested_mask and supplemental_counter:
            supplemental_mask &= (~requested_mask)&65535
            supplemental_counter-=1
            reset=supplemental_counter==0
    return dict(entry_masks=masks,matched_index=index,bank_flags=bank_flags,
                supplemental_mask=supplemental_mask,supplemental_counter=supplemental_counter,
                reset_storage=reset)


def blend_auxiliary_pose_triplet(first, second, previous, requested_mask, weight, rotate):
    """Recovered keyed-helper triplet branches with external rotation service.

    Evidence: CENTRAL_IMPULSE.md, Keyed helper blends three auxiliary poses.
    Semantic role of poses and scalar weights remains unknown.
    """
    from copy import deepcopy
    from reference.central_impulse import f32
    if type(requested_mask) is not int or not 0<=requested_mask<=65535:
        raise ValueError('uint16 requested mask required')
    output=deepcopy(previous)
    if first is None or second is None or previous is None:return output
    # Authored input contract, not checks recovered from the native routine.
    import math
    for bank in (first, second, previous):
        if type(bank['flags']) is not int or not 0 <= bank['flags'] < 2**32:
            raise ValueError('uint32 bank flags required')
        if len(bank['poses']) != 3 or len(bank['weights']) != 3:
            raise ValueError('exactly three poses and weights required')
        values = list(bank['weights'])
        for pose in bank['poses']:
            if len(pose['vector']) != 4 or len(pose['rotation']) != 4:
                raise ValueError('four-lane vectors and rotations required')
            values.extend(pose['vector']); values.extend(pose['rotation'])
        if not all(math.isfinite(float(value)) for value in values):
            raise ValueError('finite pose data required')
    if not math.isfinite(float(weight)):
        raise ValueError('finite blend weight required')
    left=bool(first['flags'] & requested_mask);right=bool(second['flags'] & requested_mask)
    if not left and not right:return output
    t=f32(weight);output['flags'] |= requested_mask
    if left and right:
        output['weights']=[1.,1.,1.]
        output['poses']=[]
        for a,b in zip(first['poses'],second['poses']):
            av,bv=tuple(map(f32,a['vector'])),tuple(map(f32,b['vector']))
            output['poses'].append(dict(vector=[f32(f32(f32(y-x)*t)+x) for x,y in zip(av,bv)],
                                        rotation=list(rotate(a['rotation'],b['rotation'],t))))
    else:
        selected=first if left else second;scale=f32(1-t) if left else t
        output['poses']=deepcopy(selected['poses'])
        output['weights']=[min(1.,max(0.,f32(f32(x)*scale))) for x in selected['weights']]
    return output


def evaluate_auxiliary_pose_triplet(first, second, previous, requested_mask, weight,
                                    arccos, sine, reciprocal_sqrt):
    """Joined keyed helper and reconstructed rotations with supplied math services.

    Evidence: CENTRAL_IMPULSE.md, Complete auxiliary triplet evaluation.
    Separate source/destination storage and finite data define the proved domain.
    """
    from reference.supplemental_pose_records import blend_auxiliary_rotation
    def rotate(a,b,t):
        return blend_auxiliary_rotation(a,b,t,arccos,sine,reciprocal_sqrt)['rotation']
    return blend_auxiliary_pose_triplet(first,second,previous,requested_mask,weight,rotate)


def plan_pose_operation_tail(effective_mask, completed_mask, resource_present,
                             resource_index, descriptor_group, first_cached, second_cached):
    """Recovered post-blend dispatch and completion order; services remain external.

    Evidence: CENTRAL_IMPULSE.md, Pose operation tail orders keyed blend and releases.
    Cache booleans represent pointer equality, not ownership or semantic identity.
    """
    if any(type(x) is not int or not 0<=x<=65535
           for x in (effective_mask,completed_mask,resource_index)):
        raise ValueError('uint16 masks and resource index required')
    if type(descriptor_group) is not int or not 0<=descriptor_group<=255:
        raise ValueError('uint8 descriptor group required')
    if any(type(x) is not bool for x in (resource_present,first_cached,second_cached)):
        raise ValueError('boolean presence and cache matches required')
    keyed=resource_present and resource_index!=65535 and bool(effective_mask & (1 << (descriptor_group & 31)))
    events=[]
    if resource_present:events.append('lookup_key')
    if keyed:events.append('blend_auxiliary_triplet')
    events.append('mark_completed_mask')
    if not first_cached:events.append('release_first')
    if not second_cached:events.append('release_second')
    return dict(keyed_blend=keyed,completed_mask=completed_mask|effective_mask,events=events)


def apply_pose_source_releases(entry_masks, entry_banks, banks, first, second,
                               first_cached, second_cached, effective_mask):
    """Sequential post-operation releases with shared logical source identity.

    Evidence: CENTRAL_IMPULSE.md, Shared source releases consume the mask once.
    Bank dictionaries contain flags, supplemental_mask and supplemental_counter.
    Reset is reported as an effect; native heap ownership is not reconstructed.
    """
    from copy import deepcopy
    if any(type(x) is not bool for x in (first_cached,second_cached)):
        raise ValueError('boolean cache matches required')
    if len(entry_masks)!=len(entry_banks):raise ValueError('matching entry arrays required')
    state=deepcopy(banks);masks=list(entry_masks);effects=[]
    for source,cached in ((first,first_cached),(second,second_cached)):
        if cached:continue
        bank=state[source]
        result=release_pose_bank_groups(masks,entry_banks,source,effective_mask,
            bank['flags'],bank['supplemental_mask'],bank['supplemental_counter'])
        masks=result['entry_masks']
        bank.update(flags=result['bank_flags'],supplemental_mask=result['supplemental_mask'],
                    supplemental_counter=result['supplemental_counter'])
        effects.append(dict(source=source,matched_index=result['matched_index'],
                            reset_storage=result['reset_storage']))
    return dict(entry_masks=masks,banks=state,effects=effects)


def evaluate_pose_operation_tail(entry_masks, entry_banks, banks, destination,
                                  first, second, effective_mask, completed_mask,
                                  resource_present, resource_index, descriptor_group,
                                  first_cached, second_cached, weight,
                                  arccos, sine, reciprocal_sqrt):
    """Compose keyed auxiliary update and ordered source releases.

    Evidence: CENTRAL_IMPULSE.md, Keyed blend and releases composed.
    Lookup is supplied. Destination must be distinct; source sharing is modeled.
    Reset effects remain explicit rather than pretending to own native storage.
    """
    from copy import deepcopy
    if destination in (first,second):
        raise ValueError('destination/source aliasing is outside the validated contract')
    plan=plan_pose_operation_tail(effective_mask,completed_mask,resource_present,
        resource_index,descriptor_group,first_cached,second_cached)
    state=deepcopy(banks)
    if plan['keyed_blend']:
        state[destination]=evaluate_auxiliary_pose_triplet(state[first],state[second],
            state[destination],effective_mask,weight,arccos,sine,reciprocal_sqrt)
    result=apply_pose_source_releases(entry_masks,entry_banks,state,first,second,
                                     first_cached,second_cached,effective_mask)
    result.update(completed_mask=plan['completed_mask'],events=plan['events'])
    return result


def evaluate_ordinary_pose_operation(operation, entry_masks, entry_banks, banks,
                                     destination, first, second, kinds, groups,
                                     group_count, completed_mask, resource_present,
                                     resource_index, descriptor_group, first_cached,
                                     second_cached, arccos, sine, reciprocal_sqrt):
    """Ordinary operation prefix, grouped bank blend, keyed tail and releases.

    Evidence: CENTRAL_IMPULSE.md, Ordinary pose operation composition.
    Stable metadata, nonnull component and distinct destination are required.
    Special service is deliberately unsupported rather than substituted.
    """
    from copy import deepcopy
    if destination in (first,second):raise ValueError('destination/source aliasing unsupported')
    route=plan_pose_operation_route(**operation)
    if route['route']=='special':raise NotImplementedError('special pose service remains unresolved')
    state=deepcopy(banks);a,b,d=state[first],state[second],state[destination]
    blend=evaluate_grouped_pose_bank(a['channels'],b['channels'],d['channels'],kinds,
        0 if route['route']=='mode_0' else 4,route['weight'],a['records'],b['records'],
        d['records'],route['group_mask'],group_count,groups,route['range_selector'],
        route.get('swap',False),0,d['flags'],reciprocal_sqrt)
    d.update(channels=blend['channels'],records=blend['records'],flags=blend['flags'])
    result=evaluate_pose_operation_tail(entry_masks,entry_banks,state,destination,first,
        second,route['group_mask'],completed_mask,resource_present,resource_index,
        descriptor_group,first_cached,second_cached,route['weight'],arccos,sine,reciprocal_sqrt)
    for effect in result['effects']:
        if effect['reset_storage']:result['banks'][effect['source']]['records']=[]
    result.update(route=route,group_calls=blend['calls'])
    return result


def lookup_pose_resource(entries, key):
    """Recovered unsigned lower-bound lookup returning the first matching index.

    Evidence: CENTRAL_IMPULSE.md, Pose resource lookup is an unsigned lower bound.
    Sortedness and range validation are authored guards; native trusts the table.
    Entries are (uint32 key, uint16 descriptor index), with padding omitted.
    """
    if type(key) is not int or not 0<=key<2**32:raise ValueError('uint32 key required')
    if len(entries)>65535:raise ValueError('uint16 table count required')
    previous=-1
    for item in entries:
        if len(item)!=2:raise ValueError('key/index pairs required')
        k,index=item
        if type(k) is not int or not 0<=k<2**32 or type(index) is not int or not 0<=index<=65535:
            raise ValueError('uint32 key and uint16 index required')
        if k<previous:raise ValueError('unsigned sorted resource keys required')
        previous=k
    start,count=0,len(entries)
    while count:
        half=count//2;middle=start+half
        if entries[middle][0]<key:start=middle+1;count-=half+1
        else:count=half
    return entries[start][1] if start<len(entries) and entries[start][0]==key else 65535


def hermite_pose_pair(first, second, first_tangent, second_tangent, previous_vector,
                      weight, tangent_scale, vector_key_matches, reciprocal_sqrt):
    """Recovered special-route contiguous kind-5/6 pair arithmetic.

    Evidence: CENTRAL_IMPULSE.md, Special pose route uses cubic Hermite terms.
    Tangent naming follows mathematics; producer and units remain unproved.
    """
    import math
    from reference.central_impulse import f32
    t,s=f32(weight),f32(tangent_scale)
    values=[t,s,*previous_vector]
    for record in (first,second,first_tangent,second_tangent):
        for key in ('vector','rotation'):
            if len(record[key])!=4:raise ValueError('four-lane pair data required')
            values.extend(record[key])
    if len(previous_vector)!=4 or not all(math.isfinite(float(x)) for x in values):
        raise ValueError('finite four-lane data required')
    if type(vector_key_matches) is not bool:raise ValueError('boolean key match required')
    coefficients=_hermite_coefficients(t,s)
    def mix(a,b,c,d):return _hermite_mix(a,b,c,d,coefficients)
    vector=mix(first['vector'],second['vector'],first_tangent['vector'],second_tangent['vector']) if vector_key_matches else list(previous_vector)
    a,b=list(map(f32,first['rotation'])),list(map(f32,second['rotation']))
    products=[f32(x*y) for x,y in zip(a,b)]
    dot=f32(f32(products[1]+products[3])+f32(products[0]+products[2]))
    adjusted=[-x for x in b] if a!=b and dot<0 else b
    rotation=mix(a,adjusted,first_tangent['rotation'],second_tangent['rotation'])
    if all(x==0 for x in rotation):rotation=b
    else:
        squares=[f32(x*x) for x in rotation]
        n=f32(f32(squares[1]+squares[3])+f32(squares[0]+squares[2]))
        if not math.isfinite(n) or n<=0:raise ValueError('positive finite normalization length required')
        seed=f32(reciprocal_sqrt(n))
        factor=f32(f32(3-f32(f32(seed*n)*seed))*f32(.5*seed))
        rotation=[f32(x*factor) for x in rotation]
    return dict(vector=vector,rotation=rotation,coefficients=coefficients)


def plan_special_pose_walk(descriptors, total_end, group_mask, groups):
    """Recovered special-helper range and ordered vector/quaternion writes.

    Evidence: CENTRAL_IMPULSE.md, Special helper traversal and tangent indexing.
    Descriptors are (uint32 key, uint16 type_word). Bounds guards are authored;
    native lookahead can process the quaternion at the exclusive loop end.
    """
    if any(type(x) is not int or not 0<=x<=65535 for x in (total_end,group_mask)):
        raise ValueError('uint16 range end and mask required')
    for key,kind in descriptors:
        if type(key) is not int or not 0<=key<2**32 or type(kind) is not int or not 0<=kind<=65535:
            raise ValueError('uint32 keys and uint16 type words required')
    group=None
    if group_mask==65535:start,end=0,total_end
    else:
        group=max(0,group_mask.bit_length()-1)
        if group>=len(groups) or len(groups[group])!=7:raise ValueError('selected seven-word group required')
        row=groups[group]
        if any(type(x) is not int or not 0<=x<=65535 for x in row):raise ValueError('uint16 group fields required')
        start=0 if group_mask&1 else row[0];end=row[6]
    if max(start,end)>len(descriptors):raise ValueError('range exceeds supplied descriptors')
    index=start;tangent=0;writes=[]
    while index<end:
        key,kind=descriptors[index]
        if kind&15==5:
            if key==0x2c52cbb0:writes.append(dict(channel=index,kind='vector',tangent=tangent))
            index+=1
            if index>=len(descriptors):raise ValueError('native lookahead needs another descriptor')
            if descriptors[index][1]&15==6:
                writes.append(dict(channel=index,kind='rotation',tangent=tangent));tangent+=1
        index+=1
    return dict(first=start,end=end,group_index=group,writes=writes,tangent_records=tangent)


def _hermite_coefficients(t, s):
    from reference.central_impulse import f32
    t2=f32(t*t);t3=f32(t2*t);twice=f32(t3+t3);three=f32(t2*3)
    return [f32(f32(twice-three)+1),f32(three-twice),
            f32(f32(f32(t3-f32(t2+t2))+t)*s),f32(f32(t3-t2)*s)]


def _hermite_mix(a,b,c,d,coefficients):
    from reference.central_impulse import f32
    out=[]
    for lanes in zip(a,b,c,d):
        terms=[f32(f32(x)*k) for x,k in zip(lanes,coefficients)]
        out.append(f32(f32(f32(terms[0]+terms[1])+terms[2])+terms[3]))
    return out


def evaluate_special_pose_bank(first, second, previous, descriptors, total_end,
                                group_mask, groups, first_tangents, second_tangents,
                                weight, tangent_scale, reciprocal_sqrt):
    """Joined special-helper walk and Hermite math for separate value storage.

    Evidence: CENTRAL_IMPULSE.md, Special bank traversal and arithmetic composed.
    Returned channels preserve untouched values; no supplemental/status effects.
    """
    from copy import deepcopy
    import math
    from reference.central_impulse import f32
    if any(len(rows)!=len(descriptors) for rows in (first,second,previous)):
        raise ValueError('one supplied channel per descriptor required')
    t,scale=f32(weight),f32(tangent_scale)
    if not all(math.isfinite(x) for x in (t,scale)):raise ValueError('finite parameters required')
    plan=plan_special_pose_walk(descriptors,total_end,group_mask,groups)
    out=deepcopy(previous);coefficients=_hermite_coefficients(t,scale)
    for write in plan['writes']:
        i,j=write['channel'],write['tangent'];kind=write['kind']
        if j>=min(len(first_tangents),len(second_tangents)):
            raise ValueError('missing tangent record')
        a,b=first[i],second[i];c,d=first_tangents[j][kind],second_tangents[j][kind]
        if any(len(row)!=4 for row in (a,b,c,d)) or not all(math.isfinite(float(x)) for row in (a,b,c,d) for x in row):
            raise ValueError('finite four-lane channels and tangents required')
        if kind=='vector':out[i]=_hermite_mix(a,b,c,d,coefficients)
        else:
            pair=lambda q:dict(vector=[0.]*4,rotation=q)
            out[i]=hermite_pose_pair(pair(a),pair(b),pair(c),pair(d),[0.]*4,
                                     t,scale,False,reciprocal_sqrt)['rotation']
    return dict(channels=out,walk=plan,coefficients=coefficients)


def evaluate_special_pose_operation(operation, entry_masks, entry_banks, banks,
                                    destination, first, second, descriptors, total_end,
                                    groups, first_tangents, second_tangents, tangent_scale,
                                    completed_mask, resource_present, resource_index,
                                    descriptor_group, first_cached, second_cached,
                                    arccos, sine, reciprocal_sqrt):
    """Special Hermite bank evaluation followed by the common operation tail.

    Evidence: CENTRAL_IMPULSE.md, Complete special pose operation.
    Tangents and their scale are supplied; no producer or timestep is invented.
    """
    from copy import deepcopy
    if destination in (first,second):raise ValueError('destination/source aliasing unsupported')
    route=plan_pose_operation_route(**operation)
    if route['route']!='special':raise ValueError('special operation route required')
    state=deepcopy(banks)
    result=evaluate_special_pose_bank(state[first]['channels'],state[second]['channels'],
        state[destination]['channels'],descriptors,total_end,route['group_mask'],groups,
        first_tangents,second_tangents,route['weight'],tangent_scale,reciprocal_sqrt)
    state[destination]['channels']=result['channels']
    tail=evaluate_pose_operation_tail(entry_masks,entry_banks,state,destination,first,second,
        route['group_mask'],completed_mask,resource_present,resource_index,descriptor_group,
        first_cached,second_cached,route['weight'],arccos,sine,reciprocal_sqrt)
    for effect in tail['effects']:
        if effect['reset_storage']:tail['banks'][effect['source']]['records']=[]
    tail.update(route=route,special_walk=result['walk'],coefficients=result['coefficients'])
    return tail


def plan_tangent_storage_clone(source_present, destination_present, source_count, destination_count):
    """Recovered operation-copy tangent allocation and bulk-copy plan.

    Evidence: CENTRAL_IMPULSE.md, Tangent storage cloning and record count.
    Presence lists have two slots; allocator success is assumed for nonzero counts.
    Allocation is not tangent generation, and existing capacities are unknown.
    """
    if len(source_present)!=2 or len(destination_present)!=2 or any(type(x) is not bool for x in (*source_present,*destination_present)):
        raise ValueError('two boolean source and destination slots required')
    if any(type(x) is not int or not 0<=x<2**32 for x in (source_count,destination_count)):
        raise ValueError('uint32 record counts required')
    present=list(destination_present);count=destination_count;events=[]
    for slot in range(2):
        if source_present[slot] and not present[slot]:
            count=source_count
            events.append(dict(action='allocate',slot=slot,records=count,bytes=(count<<5)&0xffffffff))
            present[slot]=count!=0
    for slot in range(2):
        if source_present[slot]:events.append(dict(action='copy',slot=slot,bytes=count<<5))
    return dict(destination_present=present,record_count=count,events=events)


def pose_operation_copy_guard(operation_kind, flags, progress_value, scale_value):
    """Recovered boolean predicate whose true result skips operation copying.

    Evidence: CENTRAL_IMPULSE.md, Clone callers tie Hermite scale to progress bound.
    Field names are neutral; time units and actual progress producer remain open.
    """
    import math
    from reference.central_impulse import f32
    if type(operation_kind) is not int or not 0<=operation_kind<=65535:
        raise ValueError('uint16 kind word required')
    if type(flags) is not int or not 0<=flags<=255:raise ValueError('uint8 flags required')
    current,limit=f32(progress_value),f32(scale_value)
    if not math.isfinite(current) or not math.isfinite(limit):raise ValueError('finite scalar fields required')
    kind=operation_kind&7
    if kind==0:return True
    if kind==5 and not flags&4:return False
    return bool(flags&2) or current>limit or abs(f32(current-limit))<=f32(1e-5)
