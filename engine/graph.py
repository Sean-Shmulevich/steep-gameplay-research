"""Recovered lazy-producer readiness and deferred-evaluation contract.

Callback identity and graph selection are supplied by the caller. This kernel
is independently testable; the default clip runtime does not assume its gate
configuration describes the active original rider graph.
"""
import copy
import math
from .assets import canonical

def read_producer(state,group,field,produce):
    groups=state.setdefault('groups',{})
    cached=groups.setdefault(group,{'ready':False,'values':{}})
    if not cached['ready']:
        values=produce();canonical(values)
        if not isinstance(values,dict):raise ValueError('Producer must return named scalar values')
        cached['values']=copy.deepcopy(values);cached['ready']=True
    if field not in cached['values']:raise KeyError('Missing producer output')
    return copy.deepcopy(cached['values'][field])

def update(state,dt,config,evaluate,cached_callbacks=()):
    if not math.isfinite(dt) or dt<0:raise ValueError('Invalid graph dt')
    threshold=config.get('byte_threshold',1)
    if type(threshold) is not int or not 0<=threshold<=255:raise ValueError('Threshold must be a byte')
    pending=config.get('pending_count',0);flags=config.get('flags',1)
    if not config.get('graph_present',True):return {'path':'no_graph'}
    eligible=bool(cached_callbacks) and pending==0 and flags&5==1
    counter=state.get('byte_counter',0)
    if eligible:
        counter=(counter+1)&255;state['byte_counter']=counter
    if eligible and counter<threshold:
        for callback in cached_callbacks:callback(dt)
        state['accumulated_dt']=state.get('accumulated_dt',0.)+dt
        return {'path':'cached_callbacks','dt':dt}
    effective=state.get('accumulated_dt',0.)+dt
    state['accumulated_dt']=0.;state['byte_counter']=0
    result=evaluate(effective)
    # Readiness reset AFTER full evaluation is a recovered ordering constraint.
    for group in state.get('groups',{}).values():group['ready']=False
    return {'path':'full_evaluation','dt':effective,'result':result}


def evaluate_pose(rig,clips,state,dt,definition,inputs):
    """Evaluate a serializable clip/blend/axial/additive/mask/selector graph.

    Schema and active-child clock ownership are our design. Weight normalization,
    stored-order blending, quaternion branches and byte masks use recovered math.
    State is copied and contains every clip clock. Nodes evaluate at most once
    per invocation. Inactive clips retain their clocks. Cycles are rejected.
    Scalar input references are {'input':'name'}; numeric constants also work.
    """
    from . import animation
    from reference import animation_blending as blend
    animation.validate_resources(rig,clips)
    validate_definition(definition,clips)
    canonical([state,dt,definition,inputs])
    if not isinstance(dt,(int,float)) or isinstance(dt,bool) or dt<0:raise ValueError('Invalid pose graph dt')
    if definition.get('schema_version')!=1:raise ValueError('Unsupported pose graph version')
    nodes=definition['nodes'];root=definition['root']
    if not isinstance(nodes,dict) or root not in nodes:raise ValueError('Missing graph root')
    s=copy.deepcopy(state);s.setdefault('nodes',{})
    memo={};active=set();visits=[];contexts={};missing_masks=[]
    bind=[animation._pose(b['local_bind']) for b in rig['bones']]
    def scalar(value):
        from .animation_decisions import evaluate_expression
        return evaluate_expression(value,inputs)
    def pose_blend(a,b,weight,mask=None,excluded=()):
        out=[]
        if mask is not None:
            unknown=set(mask)-{bone['name'] for bone in rig['bones']};missing_masks.extend(sorted(unknown))
            if any(type(v) is not int or not 0<=v<=255 for v in mask.values()):raise ValueError('Mask weights must be bytes')
        for bone,x,y in zip(rig['bones'],a,b):
            w=blend.masked_channel_weight(mask.get(bone['name'],0),weight) if mask is not None else weight
            out.append({'translation':copy.deepcopy(x['translation']) if 'translation' in excluded else blend.linear_blend(x['translation'],y['translation'],w),
                        'quaternion_xyzw':copy.deepcopy(x['quaternion_xyzw']) if 'rotation' in excluded else blend.bone_rotation_blend(x['quaternion_xyzw'],y['quaternion_xyzw'],w)})
        return out
    def visit(key):
        if key in active:raise ValueError('Cyclic pose graph')
        if key in memo:return memo[key]
        if key not in nodes:raise ValueError('Missing pose graph node')
        active.add(key);node=nodes[key];kind=node['type'];space='local'
        if kind=='clip':
            name=node['clip']
            if name not in clips:raise ValueError('Missing graph clip')
            clip=clips[name];clock=s['nodes'].setdefault(key,{'time':0.})
            rate=scalar(node.get('rate',1.))
            if rate<0:raise ValueError('Reverse clip playback is not implemented')
            clock['time']=animation._time(clip,clock['time']+dt*rate)
            space=node.get('space','local')
            if space not in ('local','delta'):raise ValueError('Invalid pose space')
            fallback=bind if space=='local' else [animation._identity() for _ in bind]
            pose=[animation._sample(clip,clock['time'],b['name'],seed) for b,seed in zip(rig['bones'],fallback)]
        elif kind=='blend':
            children=node['children'];weights=node['weights']
            if len(children)!=len(weights):raise ValueError('Child weight count mismatch')
            weights,dominant=blend.normalize_weights([scalar(w) for w in weights]);schedule=blend.incremental_blend_schedule(weights)
            pose=None;space=None
            for item in schedule:
                child_pose,child_space=visit(children[item['child']])
                if pose is None:pose=copy.deepcopy(child_pose);space=child_space
                else:
                    if space!=child_space:raise ValueError('Cannot mix delta and local poses')
                    pose=pose_blend(pose,child_pose,item['alpha'])
            if pose is None:pose=copy.deepcopy(bind);space='local'
            contexts[key]={'weights':weights,'dominant_child':children[dominant] if children else None,'order':[children[x['child']] for x in schedule],'empty_policy':'bind fallback'}
        elif kind=='axial':
            knots=[scalar(x) for x in node['knots']];children=node['children']
            if len(children)!=len(knots) or not knots or any(a>=b for a,b in zip(knots,knots[1:])):raise ValueError('Axial knots must be strictly ordered')
            left,right,weight=blend.axial_blend(scalar(node['coordinate']),knots)
            pose,space=visit(children[left]);pose=copy.deepcopy(pose)
            if right!=left:
                other,other_space=visit(children[right])
                if space!=other_space:raise ValueError('Pose space mismatch')
                pose=pose_blend(pose,other,weight)
            contexts[key]={'left':left,'right':right,'weight':weight}
        elif kind=='additive':
            base,space=visit(node['base']);delta,delta_space=visit(node['delta']);weight=scalar(node.get('weight',1.))
            if space!='local' or delta_space!='delta':raise ValueError('Additive expects local base and delta layer')
            pose=[{'translation':blend.additive_translation(a['translation'],b['translation'],weight),'quaternion_xyzw':blend.additive_rotation(a['quaternion_xyzw'],b['quaternion_xyzw'],weight)} for a,b in zip(base,delta)]
        elif kind=='mask':
            pose,space=visit(node['base']);other,other_space=visit(node['overlay'])
            if space!=other_space:raise ValueError('Pose space mismatch')
            excluded=node.get('exclude',[])
            if set(excluded)-{'translation','rotation'}:raise ValueError('Unknown channel exclusion')
            pose=pose_blend(pose,other,scalar(node.get('weight',1.)),node['bytes'],excluded)
        elif kind=='select':
            # Choice mapping and retained clocks are explicit independent policies.
            branch=node['if_true'] if scalar(node['condition'])!=0 else node['if_false']
            pose,space=visit(branch);pose=copy.deepcopy(pose);contexts[key]={'selected':branch}
        else:raise ValueError('Unsupported pose graph node')
        active.remove(key);visits.append(key);memo[key]=(pose,space);return pose,space
    pose,space=visit(root)
    if space!='local':raise ValueError('Graph root must produce a local pose')
    canonical(pose)
    return {'state':s,'local_pose':pose,'model_pose':animation._models(rig['bones'],pose),
            'diagnostics':{'visited':visits,'contexts':contexts,'unmatched_mask_bones':sorted(set(missing_masks)),
                           'evidence':'recovered ordered blending/masks; designed graph schema, selection and active-child clocks'}}


def validate_definition(definition,clips):
    """Structural validation includes inactive branches before runtime evaluation."""
    canonical(definition)
    if not isinstance(definition,dict) or definition.get('schema_version')!=1:raise ValueError('Unsupported pose graph version')
    nodes=definition.get('nodes')
    if not isinstance(nodes,dict) or definition.get('root') not in nodes:raise ValueError('Missing graph root')
    edges={}
    for name,node in nodes.items():
        if not isinstance(name,str) or not isinstance(node,dict):raise ValueError('Invalid node record')
        kind=node.get('type')
        from .animation_decisions import validate_expression
        for field in ('condition','rate','coordinate','weight'):
            if field in node:validate_expression(node[field])
        for field in ('weights','knots'):
            if field in node:
                if not isinstance(node[field],list):raise ValueError('scalar expression list required')
                for value in node[field]:validate_expression(value)

        if kind=='clip':
            if node.get('clip') not in clips:raise ValueError('Missing graph clip')
            edges[name]=[]
        elif kind in ('blend','axial'):
            children=node.get('children')
            if not isinstance(children,list):raise ValueError('Missing child list')
            edges[name]=children
            values=node.get('weights' if kind=='blend' else 'knots')
            if not isinstance(values,list) or len(values)!=len(children):raise ValueError('Child parameter count mismatch')
        elif kind=='additive':edges[name]=[node.get('base'),node.get('delta')]
        elif kind=='mask':edges[name]=[node.get('base'),node.get('overlay')]
        elif kind=='select':edges[name]=[node.get('if_true'),node.get('if_false')]
        else:raise ValueError('Unsupported pose graph node')
        if any(not isinstance(child,str) or child not in nodes for child in edges[name]):raise ValueError('Missing graph child')
    active=set();done=set()
    def walk(name):
        if name in active:raise ValueError('Cyclic pose graph')
        if name in done:return
        active.add(name)
        for child in edges[name]:walk(child)
        active.remove(name);done.add(name)
    for name in nodes:walk(name)
    return {'node_count':len(nodes)}
