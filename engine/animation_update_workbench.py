"""Offline update inspection with explicit numerical policy and no live writes."""
import math
from reference.snow import f32
from reference.animation_work_application import update_context_free_work, update_context_work


def inspect_update(request):
    fields = {'schema','records','indices','saved','parent_position','parent_rotation',
              'direct','elapsed','duration','dt','bank_flags','saved_flag','bank_present',
              'context','numerics'}
    if not isinstance(request,dict) or request.get('schema') != 'animation-update-input-v1':
        raise ValueError('expected animation-update-input-v1')
    if set(request) != fields:
        raise ValueError('update requires exactly the documented fields')
    def vector(v, size):
        return isinstance(v,(list,tuple)) and len(v)==size and all(
            type(x) in (int,float) and math.isfinite(x) and math.isfinite(f32(x)) for x in v)
    for name in ('records','saved'):
        rows=request[name]
        if not isinstance(rows,list) or len(rows)>4096 or any(
            not isinstance(r,(list,tuple)) or len(r)!=2 or not all(vector(v,4) for v in r) for r in rows):
            raise ValueError('finite pose pairs required, maximum 4096')
    indices=request['indices']
    if not isinstance(indices,list) or len(indices)>4096 or any(
        type(i) is not int or not 0<=i<len(request['records']) for i in indices):
        raise ValueError('valid bounded record indices required')
    if type(request['direct']) is not bool or type(request['bank_present']) is not bool:
        raise ValueError('boolean mode and bank presence required')
    for name in ('bank_flags','saved_flag'):
        limit=0xffffffff if name=='bank_flags' else 255
        if type(request[name]) is not int or not 0<=request[name]<=limit:
            raise ValueError('invalid '+name)
    if bool(request['bank_flags'] & (1<<26)) != request['direct']:
        raise ValueError('direct mode must agree with bank flag bit 26')
    if not vector([request[x] for x in ('elapsed','duration','dt')],3):
        raise ValueError('finite timing required')
    if not request['direct'] and not all(vector(request[k],4) for k in ('parent_position','parent_rotation')):
        raise ValueError('composed bank requires finite parent transform')
    context=request['context']
    if context is not None:
        if not isinstance(context,dict) or set(context)!={'basis_rows','position'} or not vector(context['position'],4) or not isinstance(context['basis_rows'],list) or len(context['basis_rows'])!=3 or not all(vector(r,4) for r in context['basis_rows']):
            raise ValueError('context requires three basis rows and position')
    policy=request['numerics']
    if not isinstance(policy,dict) or policy.get('trig')!='host_math_substitute':
        raise ValueError('explicit host_math_substitute trig policy required')
    mode=policy.get('rsqrt');seeds=policy.get('seeds',[])
    if mode=='provided_seeds':
        if set(policy)!={'rsqrt','trig','seeds'} or not isinstance(seeds,list) or len(seeds)>8193 or any(not vector([x],1) or x<=0 for x in seeds):
            raise ValueError('bounded positive finite seed array required')
    elif mode!='exact_rsqrt_substitute' or set(policy)!={'rsqrt','trig'}:
        raise ValueError('explicit rsqrt policy required')
    normalizations=[];trig_calls=[]
    def rsqrt(n):
        if not math.isfinite(n) or n<=0:
            raise ValueError('positive finite norm required')
        if mode=='provided_seeds' and len(normalizations)>=len(seeds):
            raise ValueError('insufficient supplied seeds')
        seed=f32(seeds[len(normalizations)] if mode=='provided_seeds' else 1/math.sqrt(n))
        normalizations.append(dict(norm_squared=n,seed=seed))
        return seed
    def trig(name,x):
        y=f32(getattr(math,name)(x));trig_calls.append(dict(name=name,input=x,output=y));return y
    args={k:request[k] for k in fields-{'schema','context','numerics'}}
    args.update(reciprocal_sqrt=rsqrt,acos=lambda x:trig('acos',x),sin=lambda x:trig('sin',x))
    if context is None:
        result=update_context_free_work(**args)
    else:
        result=update_context_work(**args,basis_rows=context['basis_rows'],context_position=context['position'])
    if mode=='provided_seeds' and len(normalizations)!=len(seeds):
        raise ValueError('unused supplied seeds')
    if any(not math.isfinite(x) for record in result['records'] for v in record for x in v):
        raise ValueError('nonfinite output rejected')
    return dict(schema='animation-update-output-v1',result=result,
        numerics=dict(rsqrt=mode,trig='host_math_substitute',normalizations=normalizations,trig_calls=trig_calls),
        evidence=dict(this_input_game_verified=False,live_memory_access=False,
            original_engine_equivalence=False,pose_published=False,
            deferred_evaluator_executed=False,lifetime_established=False,
            supplied_seed_provenance_verified=False))
