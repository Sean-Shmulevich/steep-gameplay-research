"""Import caller-supplied decoded rig/clip records, without shipping payloads.

Supported source schema is the documented pose-assembly research export.
unit_scale and per-clip looping are mandatory caller policies. This adapter
never infers meters, sport selection, root motion or addon merge from names.
"""
import copy
import math
from .animation import validate_resources
from .assets import digest,CATEGORIES

def from_decoded(rig,clips,*,unit_scale,looping,category='asset-decoded'):
    if category not in CATEGORIES:raise ValueError('Unknown evidence category')
    if not isinstance(unit_scale,(int,float)) or isinstance(unit_scale,bool) or not math.isfinite(unit_scale) or unit_scale<=0:raise ValueError('Explicit positive unit scale required')
    bones=[];mapping={}
    for bone in rig['bones']:
        key=bone['binding_hash']
        if type(key) is not int or not 0<=key<=0xffffffff:raise ValueError('Expected unsigned 32-bit binding hash')
        if key in mapping:raise ValueError('Duplicate rig binding hash; active addon merge policy required')
        mapping[key]=bone['name']
        local=copy.deepcopy(bone['local_bind']);local['translation']=[x*unit_scale for x in local['translation']]
        bones.append(dict(name=bone['name'],parent_index=-1 if bone['parent_index'] is None else bone['parent_index'],binding_id=key,local_bind=local))
    converted={};unbound=[];auxiliary=[]
    for clip in clips:
        name=clip['name']
        if name in converted:raise ValueError('Duplicate clip name requires explicit resource alias')
        if name not in looping or type(looping[name]) is not bool:raise ValueError('Explicit looping policy required for every clip')
        channels={}
        for track in clip['tracks']:
            key=track['binding_hash'];kind=track['value_type']
            if kind not in ('vector3','quaternion'):
                auxiliary.append(dict(clip=name,track=track.get('track_number'),kind=kind));continue
            if key not in mapping:
                unbound.append(dict(clip=name,binding_hash=key,kind=kind));continue
            target=mapping[key];channel=channels.setdefault(target,{})
            field='translation' if kind=='vector3' else 'rotation'
            if field in channel:raise ValueError('Multiple tracks for the same bound component')
            values=track['values'];ticks=track.get('keyframes',[0] if len(values)==1 else None)
            if ticks is None or len(ticks)!=len(values) or any(type(t) is not int or t<0 for t in ticks):raise ValueError('Decoded key times required')
            channel[field]=[dict(time=t/60.,value=[x*unit_scale for x in value] if field=='translation' else list(value)) for t,value in zip(ticks,values)]
        converted[name]=dict(duration=clip['duration'],loop=looping[name],sampling_policy='recovered_60hz',wrap_policy='inclusive',channels=channels)
    output_rig=dict(bones=bones,provenance=dict(category=category,source_digest=digest(rig),unit_scale=unit_scale,source_units='caller-supplied authored units; scale is explicit'))
    validate_resources(output_rig,converted)
    return dict(bundle=dict(category=category,rig=output_rig,clips=converted),diagnostics=dict(unbound_transform_tracks=unbound,auxiliary_tracks=auxiliary,loop_policy='explicit caller mapping',root_motion='not automatically applied',addon_merge='not inferred'))
