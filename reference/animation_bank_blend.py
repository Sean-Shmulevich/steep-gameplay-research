"""Regular unmasked bank blend over caller-supplied byte storage/profile.

Evidence: CENTRAL_IMPULSE.md, Regular byte-bank traversal.
Supplemental records use the reconstructed evaluator by default; normalization
seeds remain an explicit dependency. A supplied tail callback may override it.
"""
import math
import struct
from reference.animation_channels import plan_arithmetic_channel_route
from reference.animation_channel_blend import blend_channel
from reference.animation_flat_conversion import _f32
from reference.animation_bank_copy import _layout


def blend_regular_pose_bank(destination, first, second, weight, selector, request_mask,
                            *, supplemental=None, exclusion_mask=0, reciprocal_sqrt=None):
    if supplemental is None:
        from reference.supplemental_pose_records import evaluate_supplemental_records
        if any('records' not in bank for bank in (destination,first,second)):
            raise ValueError('explicit supplemental record lists required')
        def supplemental(dst,a,b,mask,weight,mode):
            dst['records']=evaluate_supplemental_records(
                a['records'],b['records'],dst['records'],weight,reciprocal_sqrt)
    if not 0<=request_mask<=65535 or not 0<=selector<=7:
        raise ValueError('uint16 mask and three-bit selector required')
    w=_f32(weight)
    if not math.isfinite(w):raise ValueError('finite weight required by this adapter')
    profile=_layout(first);count=profile['group_count']
    if not 0<=count<=16:raise ValueError('bounded group count required')
    masks=[65535] if request_mask==65535 else [1<<i for i in range(count) if request_mask&(1<<i)]
    visited=[]
    for mask in masks:
        if mask==65535:start=0;length=profile['channel_count']
        else:
            base=(mask.bit_length()-1)*7
            start=profile['group_words'][base];length=profile['group_words'][base+selector+1]
        descriptors=_layout(destination)['descriptors']
        if start<0 or length<0 or start+length>len(descriptors):
            raise ValueError('channel range outside supplied descriptors')
        selected=descriptors[start:start+length]
        route=plan_arithmetic_channel_route(0,w,False,[d['kind'] for d in selected],exclusion_mask)
        scaled=_f32(w*255)
        if not math.isfinite(scaled) or not -(2**63)<=scaled<2**63:
            raise ValueError('integer-weight conversion outside supported range')
        integer=math.trunc(scaled)&0xffffffff
        for i in route['indices']:
            d=selected[i];offset=d['offset'];kind=d['kind']&15
            if route['helper']=='copy_second':
                width=1 if kind==0 else 4 if kind<4 else 12 if kind==4 else 16
                if offset<0 or offset+width>min(len(destination['data']),len(second['data'])):
                    raise ValueError('copy channel outside supplied storage')
                destination['data'][offset:offset+width]=second['data'][offset:offset+width]
                destination['flags'] |= 1<<27
            else:
                blend_channel(destination['data'],first['data'],second['data'],
                    struct.pack('<IHH',0,offset,d['kind']),w,[w]*4,integer,
                    reciprocal_sqrt=reciprocal_sqrt)
        supplemental(destination,first,second,mask,w,0)
        visited.append(dict(mask=mask,start=start,count=length,helper=route['helper']))
    return visited


def blend_masked_pose_bank(destination, first, second, weight, selector, request_mask,
                           *, weight_mode=1, uniform_groups=0, exclusion_mask=0,
                           reciprocal_sqrt=None, supplemental=None):
    """Regular masked router and keyed channel loop.

    Evidence: CENTRAL_IMPULSE.md, Masked bank blend output.
    Full-mask requests bypass uniform_groups. Partial groups with override bits
    use the existing uniform kernel. Supplemental evaluation uses global weight.
    """
    from reference.animation_mask_weights import iter_masked_channel_weights
    from reference.supplemental_pose_records import evaluate_supplemental_records
    if weight_mode not in (0,1) or not 0<=selector<=7:
        raise ValueError('masked mode zero/one and three-bit selector required')
    if not 0<=request_mask<=65535 or not 0<=uniform_groups<=65535:
        raise ValueError('uint16 masks required')
    if supplemental is None:
        if any('records' not in b for b in (destination,first,second)):
            raise ValueError('explicit supplemental record lists required')
        def supplemental(d,a,b,m,w,mode):
            d['records']=evaluate_supplemental_records(a['records'],b['records'],d['records'],w,reciprocal_sqrt)
    profile=_layout(first)
    if not 0<=profile['group_count']<=16:raise ValueError('bounded group count required')
    masks=[65535] if request_mask==65535 else [1<<i for i in range(profile['group_count']) if request_mask&(1<<i)]
    visits=[];weight=_f32(weight)
    for mask in masks:
        if mask!=65535 and mask&uniform_groups:
            blend_regular_pose_bank(destination,first,second,weight,selector,mask,
                supplemental=supplemental,exclusion_mask=exclusion_mask,reciprocal_sqrt=reciprocal_sqrt)
            visits.append(dict(mask=mask,mode=2));continue
        if mask==65535:start=0;count=profile['channel_count']
        else:
            base=(mask.bit_length()-1)*7
            start=profile['group_words'][base];count=profile['group_words'][base+selector+1]
        descriptors=_layout(destination)['descriptors']
        if start<0 or count<0 or start+count>len(descriptors):raise ValueError('descriptor range outside profile')
        selected=descriptors[start:start+count]
        values=(first if weight_mode==0 else second)['data']
        for row in iter_masked_channel_weights(selected,lambda o:values[o],weight,weight_mode):
            d=selected[row['index']];kind=d['kind']&15;offset=d['offset']
            if exclusion_mask&(1<<kind):continue
            if row['integer_weight']==255:
                width={0:1,1:4,2:4,4:12,5:16,6:16}.get(kind,0)
                source=first['data'] if kind==4 else second['data']
                if offset<0 or offset+width>min(len(source),len(destination['data'])):
                    raise ValueError('copy channel outside supplied buffers')
                if kind==4:
                    for lane in range(3):
                        pos=offset+lane*4;destination['data'][pos:pos+4]=source[pos:pos+4]
                elif width:destination['data'][offset:offset+width]=source[offset:offset+width]
            else:
                w=row['weight']
                blend_channel(destination['data'],first['data'],second['data'],
                    struct.pack('<IHH',d['key'],offset,d['kind']),w,[w]*4,row['integer_weight'],
                    reciprocal_sqrt=reciprocal_sqrt)
        supplemental(destination,first,second,mask,weight,0)
        visits.append(dict(mask=mask,mode=weight_mode))
    return visits


def blend_additive_pose_bank(destination, first, second, weight, selector, request_mask,
                             *, swap=False, exclusion_mask=0, reciprocal_sqrt=None, weight_mode=2):
    """Uniform additive bank router; supplemental records and flags are unchanged.

    Evidence: CENTRAL_IMPULSE.md, Additive byte-bank traversal.
    Source order follows the recovered mode-four route, not argument order.
    """
    from reference.animation_channel_blend import blend_additive_channel, combine_unweighted_byte_channel
    if not 0<=request_mask<=65535 or not 0<=selector<=7:
        raise ValueError('uint16 mask and three-bit selector required')
    if weight_mode not in (0,1,2):raise ValueError('weight mode zero, one or two required')
    profile=_layout(first)
    if not 0<=profile['group_count']<=16:raise ValueError('bounded group count required')
    masks=[65535] if request_mask==65535 else [1<<i for i in range(profile['group_count']) if request_mask&(1<<i)]
    w=_f32(weight);visited=[];banks=dict(first=first,second=second)
    for mask in masks:
        if mask==65535:start=0;count=profile['channel_count']
        else:
            base=(mask.bit_length()-1)*7
            start=profile['group_words'][base];count=profile['group_words'][base+selector+1]
        descriptors=_layout(destination)['descriptors']
        if start<0 or count<0 or start+count>len(descriptors):raise ValueError('descriptor range outside profile')
        selected=descriptors[start:start+count]
        route=plan_arithmetic_channel_route(4,w,swap,[d['kind'] for d in selected],exclusion_mask)
        a,b=(banks[name]['data'] for name in route['sources'])
        scaled=_f32(w*255)
        if not math.isfinite(scaled) or not -(2**63)<=scaled<2**63:
            raise ValueError('integer-weight conversion outside supported range')
        integer=math.trunc(scaled)&0xffffffff
        if weight_mode==2:
            work=(dict(index=i,weight=w,integer_weight=integer,
                       unweighted=route['helper']=='unweighted_combine') for i in route['indices'])
        else:
            from reference.animation_mask_weights import iter_masked_channel_weights
            values=(first if weight_mode==0 else second)['data']
            work=(dict(row,unweighted=row['integer_weight']==255) for row in
                  iter_masked_channel_weights(selected,lambda o:values[o],w,weight_mode))
        for row in work:
            d=selected[row['index']]
            if exclusion_mask&(1<<(d['kind']&15)):continue
            descriptor=struct.pack('<IHH',0,d['offset'],d['kind'])
            if row['unweighted']:
                combine_unweighted_byte_channel(destination['data'],a,b,descriptor)
            else:
                effective=row['weight']
                blend_additive_channel(destination['data'],a,b,descriptor,effective,[effective]*4,row['integer_weight'],
                    reciprocal_sqrt=reciprocal_sqrt)
        visited.append(dict(mask=mask,start=start,count=count,helper=route['helper'] if weight_mode==2 else 'masked_combine'))
    return visited
