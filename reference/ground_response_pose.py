"""Recovered local bridge from published ground response to a pose scalar.

See CENTRAL_IMPULSE.md. Buffer swapping, actor lifetime and skeleton queries are
caller responsibilities. No complete landing, IK or animation graph is implied.
"""
from reference.central_impulse import f32


def consume_displacement(previous, published, decay_mode):
    """Actor-local response: copy readable displacement or decay prior by .9.

    The ignored input is not read, matching the branch-local native access.
    """
    if type(decay_mode) is not bool:
        raise ValueError('boolean decay mode required')
    return f32(f32(previous)*f32(.9)) if decay_mode else f32(published)


def pose_length_correction(length, displacement, factor, suppress, unclamped, lower, upper):
    """Recovered scalar block after the nonzero Reference-length gate.

    factor is the supplied scalar argument; its physical units are not assumed.
    Returned correction_scale feeds vector normalization/scaling outside this
    scalar model. Comparison order and float32 arithmetic are preserved.
    """
    if type(suppress) is not bool or type(unclamped) is not bool:
        raise ValueError('boolean mode flags required')
    length=f32(length)
    if abs(length) <= f32(.01):
        return {'active':False,'stored_length':None,'correction_scale':0.}
    adjustment=0. if suppress else f32(f32(f32(displacement)*.5)*f32(factor))
    target=f32(length-adjustment)
    if not unclamped:
        target=min(f32(upper),max(f32(lower),target))
    scale=f32(f32(target-length)*-2.)
    stored=f32(length-f32(scale*.5))
    return {'active':True,'stored_length':stored,'correction_scale':scale}


def reference_pose_correction(provider_vector, provider_rotation, displacement,
                              factor, suppress, unclamped, lower, upper,
                              reciprocal_sqrt):
    """Reference-provider transform through actor correction-vector storage.

    Inputs are four lanes, rotation ordered XYZW. The reciprocal_sqrt callback
    supplies the hardware estimate, not a refined reciprocal length. Finite,
    nondegenerate data are required by this authored inspection API. No provider
    lookup, actor scheduling or downstream skeleton application is performed.
    """
    import math
    v = tuple(f32(x) for x in provider_vector)
    q = tuple(f32(x) for x in provider_rotation)
    if len(v) != 4 or len(q) != 4 or not all(math.isfinite(x) for x in v+q):
        raise ValueError('finite four-lane provider vector and rotation required')

    def norm_squared(a):
        squares = tuple(f32(x*x) for x in a)
        return f32(f32(squares[0]+squares[2])+f32(squares[1]+squares[3]))

    length = f32(math.sqrt(norm_squared(v)))
    q2 = norm_squared(q)
    if not q2 > 0:
        raise ValueError('nonzero provider rotation required')
    inverse = tuple(f32((-q[i] if i < 3 else q[i])/q2) for i in range(4))
    products = tuple(f32(inverse[i]*v[i]) for i in range(4))
    dot = f32(products[0]+f32(products[1]+products[2]))
    cross = tuple(f32(f32(inverse[i]*v[j])-f32(v[i]*inverse[j]))
                  for i,j in ((1,2),(2,0),(0,1))) + (0.,)
    w_term = f32(f32(inverse[3]*inverse[3])-.5)
    transformed = tuple(f32(f32(f32(f32(cross[i]*inverse[3])+f32(dot*inverse[i]))
                                  +f32(w_term*v[i])) * (2. if i < 3 else 0.))
                        for i in range(4))
    scalar = pose_length_correction(length, displacement, factor, suppress, unclamped, lower, upper)
    if not scalar['active']:
        return dict(scalar, input_length=length, transformed=transformed, correction=(0.,)*4)
    n2 = norm_squared(transformed)
    if not n2 > 0 or not math.isfinite(n2):
        raise ValueError('nonzero finite transformed direction required')
    seed = f32(reciprocal_sqrt(n2))
    if not math.isfinite(seed) or seed <= 0:
        raise ValueError('positive finite reciprocal-square-root estimate required')
    refined = f32(f32(3.-f32(f32(seed*n2)*seed))*f32(.5*seed))
    correction = tuple(f32(f32(f32(refined*x)*-.5)*scalar['correction_scale'])
                       for x in transformed)
    return dict(scalar, input_length=length, transformed=transformed, correction=correction)


def _signed_reach(reference, endpoint, axis):
    import math
    def reduce4(a):
        return f32(f32(a[0]+a[2])+f32(a[1]+a[3]))
    delta = tuple(f32(f32(x)-f32(y)) for x,y in zip(reference,endpoint))
    dot = reduce4(tuple(f32(x*f32(y)) for x,y in zip(delta,axis)))
    length = f32(math.sqrt(reduce4(tuple(f32(x*x) for x in delta))))
    sign = 0. if dot == 0 else (1. if dot > 0 else -1.)
    return f32(sign*length)


def stored_length_filter(reference, endpoint_a, endpoint_b, axis, previous,
                         stored_length, blend):
    """Local signed-reach correction after provider queries and outer gates.

    Four-lane vectors and explicit blend are observations. Endpoints are not
    assigned anatomical names. This returns the new persistent correction and
    corrected reference point, not a complete skeleton or body update.
    """
    import math
    vectors = [tuple(f32(x) for x in a) for a in
               (reference, endpoint_a, endpoint_b, axis, previous)]
    if any(len(a) != 4 or not all(math.isfinite(x) for x in a) for a in vectors):
        raise ValueError('finite four-lane observations required')
    reference, endpoint_a, endpoint_b, axis, previous = vectors
    blend, stored_length = f32(blend), f32(stored_length)
    if not math.isfinite(blend) or not math.isfinite(stored_length):
        raise ValueError('finite blend and stored length required')
    a,b = (_signed_reach(reference, endpoint, axis) for endpoint in (endpoint_a,endpoint_b))
    error = -f32(f32(f32(a+b)*.5)-stored_length)
    retention = f32(1.-blend)
    correction = tuple(f32(f32(f32(error*x)*blend)+f32(retention*y))
                       for x,y in zip(axis,previous))
    corrected = tuple(f32(x+y) for x,y in zip(reference,correction))
    return {'signed_distances':(a,b),'error':error,'correction':correction,
            'corrected_reference':corrected}


def reach_limit_endpoints(endpoints, signed_distances, axis, above_directions,
                          below_directions, velocity, rest_lengths, lower, upper):
    """Recovered two-endpoint reach adjustment, before subsequent smoothing.

    Endpoint roles and direction frames are supplied explicitly. The speed test
    is squared four-lane magnitude > .5 in native units. No sport or body-write
    semantics are assigned to this local calculation.
    """
    import math
    def vector(a):
        a = tuple(f32(x) for x in a)
        if len(a) != 4 or not all(math.isfinite(x) for x in a):
            raise ValueError('finite four-lane vectors required')
        return a
    endpoints = tuple(vector(a) for a in endpoints)
    above_directions = tuple(vector(a) for a in above_directions)
    below_directions = tuple(vector(a) for a in below_directions)
    signed_distances = tuple(f32(x) for x in signed_distances)
    rest_lengths = tuple(f32(x) for x in rest_lengths)
    if any(len(a) != 2 for a in (endpoints, above_directions, below_directions,
                                 signed_distances, rest_lengths)):
        raise ValueError('two endpoint observations required')
    lower, upper = f32(lower), f32(upper)
    if not all(math.isfinite(x) for x in signed_distances+rest_lengths+(lower,upper)):
        raise ValueError('finite reach scalars required')
    axis, velocity = vector(axis), vector(velocity)
    squares = tuple(f32(x*x) for x in velocity)
    speed_squared = f32(f32(squares[0]+squares[2])+f32(squares[1]+squares[3]))
    moving = speed_squared > f32(.5)
    output, bounds, branches = [], [], []
    for point, distance, rest, above, below in zip(endpoints, signed_distances,
                                                 rest_lengths, above_directions, below_directions):
        lo, hi = (lower, upper) if moving else (min(lower,rest),max(upper,rest))
        p = point
        high_branch, low_branch = distance > hi, lo > distance
        if high_branch:
            excess = f32(distance-hi)
            lateral = min(f32(.15) if moving else 0., max(0., excess))
            p = tuple(f32(f32(f32(lateral*d)+x)+f32(excess*n))
                      for d,x,n in zip(above,p,axis))
        if low_branch:
            deficit = f32(lo-distance)
            amount = min(f32(.25),max(0.,deficit))
            axial = f32(f32(distance-lo)+f32(amount*f32(.3)))
            p = tuple(f32(f32(f32(amount*d)+x)+f32(axial*n))
                      for d,x,n in zip(below,p,axis))
        output.append(p);bounds.append((lo,hi));branches.append((high_branch,low_branch))
    return {'endpoints':tuple(output),'bounds':tuple(bounds),
            'branches':tuple(branches),'moving':moving,'speed_squared':speed_squared}


def endpoint_output_stage(origins, rotations, deltas, previous, blend,
                          offsets, contact_scalars, decay_mode, reference_z):
    """Recovered endpoint smoothing and output stores after reach adjustment.

    Rotation is XYZW and is not normalized here. Contact scalars retain their
    native zero/nonzero predicate; their producer semantics are unresolved.
    reference_z is a separately supplied output scalar, not a world/body write.
    """
    import math
    def vectors(values):
        values = tuple(tuple(f32(x) for x in a) for a in values)
        if len(values) != 2 or any(len(a) != 4 or not all(math.isfinite(x) for x in a) for a in values):
            raise ValueError('two finite four-lane vectors required')
        return values
    origins, rotations, deltas, previous = map(vectors, (origins, rotations, deltas, previous))
    offsets, contact_scalars = tuple(map(f32, offsets)), tuple(map(f32, contact_scalars))
    blend, reference_z = f32(blend), f32(reference_z)
    if (len(offsets) != 2 or len(contact_scalars) != 2 or type(decay_mode) is not bool
            or not all(math.isfinite(x) for x in offsets+contact_scalars+(blend,reference_z))):
        raise ValueError('finite endpoint scalars and boolean decay mode required')
    retention = f32(1.-blend)
    smoothed, positions, directions, amounts = [], [], [], []
    for origin,q,delta,old,offset,contact in zip(origins,rotations,deltas,previous,offsets,contact_scalars):
        x,y,z,w = q
        # Native lane unpacking yields the rotation's Y basis direction.
        x_component = f32(f32(x*y)-f32(w*z))
        z_component = f32(f32(x*w)+f32(y*z))
        squared = f32(f32(x*x)+f32(z*z))
        direction = (f32(x_component+x_component),f32(1.-f32(squared+squared)),
                     f32(z_component+z_component),0.)
        smooth = tuple(f32(f32(retention*a)+f32(blend*b)) for a,b in zip(old,delta))
        bump = f32(.02) if contact == 0 and not decay_mode else 0.
        amount = f32(f32(offset+f32(.13))+bump)
        base = tuple(f32(a+b) for a,b in zip(origin,smooth))
        position = tuple(f32(f32(amount*d)+p) for d,p in zip(direction,base))
        smoothed.append(smooth);positions.append(position);directions.append(direction);amounts.append(amount)
    # Native scales the summed offsets by 0.1, not by one half.
    reference_z = f32(f32(f32(offsets[1]+offsets[0])*f32(.1))+reference_z)
    return {'smoothed':tuple(smoothed),'positions':tuple(positions),
            'directions':tuple(directions),'offset_amounts':tuple(amounts),
            'reference_z':reference_z}


def reference_local_correction(rotation, correction):
    """Rotate correction by conjugated provider rotation, without normalization.

    The native caller uses only the inverse-transform helper's rotation, ignoring
    its translated/scaled origin. This is a vector transform, not a point transform.
    """
    import math
    q, v = tuple(map(f32, rotation)), tuple(map(f32, correction))
    if len(q) != 4 or len(v) != 4 or not all(math.isfinite(x) for x in q+v):
        raise ValueError('finite four-lane rotation and correction required')
    q = (-q[0],-q[1],-q[2],q[3])
    products = tuple(f32(a*b) for a,b in zip(q,v))
    dot = f32(products[0]+f32(products[1]+products[2]))
    cross = tuple(f32(f32(q[i]*v[j])-f32(v[i]*q[j]))
                  for i,j in ((1,2),(2,0),(0,1)))+(0.,)
    w_term = f32(f32(q[3]*q[3])-.5)
    return tuple(f32(f32(f32(f32(dot*q[i])+f32(cross[i]*q[3]))+
                         f32(w_term*v[i]))*(2. if i < 3 else 0.)) for i in range(4))


def resolved_pose_tail(*, reference, endpoints, axis, correction_previous,
                       stored_length, blend, above_directions, below_directions,
                       velocity, rest_lengths, lower, upper, origins, rotations,
                       endpoint_previous, offsets, contact_scalars, decay_mode,
                       provider_rotation):
    """Compose the resolved-input active tail through endpoint record outputs.

    Starts after native provider/contact queries. It does not select branches,
    decode clips, commit a skeleton palette, or mutate original-game objects.
    The initial Reference length/response producer remains a separate stage.
    """
    filtered = stored_length_filter(reference, endpoints[0], endpoints[1], axis,
                                    correction_previous, stored_length, blend)
    # Re-evaluate reach from the corrected reference, as the native tail does.
    distances = tuple(_signed_reach(filtered['corrected_reference'], p, axis) for p in endpoints)
    reached = reach_limit_endpoints(endpoints, distances, axis,
                                    above_directions, below_directions, velocity,
                                    rest_lengths, lower, upper)
    deltas = tuple(tuple(f32(a-f32(b)) for a,b in zip(point,origin))
                   for point,origin in zip(reached['endpoints'],origins))
    local = reference_local_correction(provider_rotation, filtered['correction'])
    output = endpoint_output_stage(origins, rotations, deltas, endpoint_previous,
                                    blend, offsets, contact_scalars, decay_mode, local[2])
    reference_output = (local[0],local[1],output['reference_z'],local[3])
    return {'filter':filtered,'reach':reached,'output':output,
            'reference_output':reference_output,
            'state':{'correction':filtered['correction'],'endpoints':output['smoothed']}}


def resolve_pose_contacts(axis, initial_point, initial_normal, initial_scalar, hits):
    """Local ordered hit response after a pose query has returned its records.

    Each hit supplies point, normal, hit_flags, body_flags, optional hit_scalar
    and override_allowed. Bit meanings remain unnamed. Skipped hits may change
    outputs even when no hit is ultimately accepted; normal changes on accept.
    No raycast, native handle validation or collision ordering is synthesized.
    """
    import math
    def vector(a):
        a = tuple(map(f32,a))
        if len(a) != 4 or not all(math.isfinite(x) for x in a):
            raise ValueError('finite four-lane observations required')
        return a
    axis, point, normal = map(vector,(axis,initial_point,initial_normal))
    scalar = f32(initial_scalar)
    if not math.isfinite(scalar):raise ValueError('finite initial scalar required')
    if not isinstance(hits,(tuple,list)) or len(hits) > 4096:
        raise ValueError('at most 4096 supplied ordered hits required')
    visited=[]
    for index,hit in enumerate(hits):
        position=vector(hit['point']); hit_normal=vector(hit['normal'])
        flags,body_flags=hit['hit_flags'],hit['body_flags']
        if (type(flags) is not int or not 0<=flags<2**64 or type(body_flags) is not int
                or not 0<=body_flags<2**32 or type(hit['override_allowed']) is not bool):
            raise ValueError('unsigned flags and boolean override required')
        value = hit.get('hit_scalar')
        if value is not None:
            value=f32(value)
            if not math.isfinite(value):raise ValueError('finite hit scalar required')
        if value is None or value < f32(.05):
            scalar=0.;effective=0.
        else:
            effective=value
            if hit['override_allowed']:scalar=value
        point=tuple(f32(x-f32(scalar*n)) for x,n in zip(position,axis))
        skipped=bool(flags & body_flags & (1<<15))
        visited.append({'index':index,'skipped':skipped,'scalar':scalar})
        if skipped:continue
        if not flags & (1<<24):
            point=tuple(f32(f32(effective*n)+x) for n,x in zip(axis,point))
        normal=hit_normal
        return {'accepted':True,'accepted_index':index,'point':point,
                'normal':normal,'scalar':scalar,'visited':visited}
    return {'accepted':False,'accepted_index':None,'point':point,
            'normal':normal,'scalar':scalar,'visited':visited}


def pose_contact_segment(endpoint, axis):
    """Recovered query geometry before collision dispatch; XYZ range, W cleared.

    Axis is not normalized. Finite four-lane inputs/results are required by this
    authored inspection interface. Caller gates and collision query are outside.
    """
    import math
    endpoint, axis = tuple(map(f32,endpoint)), tuple(map(f32,axis))
    if len(endpoint)!=4 or len(axis)!=4 or not all(math.isfinite(x) for x in endpoint+axis):
        raise ValueError('finite four-lane endpoint and axis required')
    extent=tuple(f32(f32(1.2)*a) for a in axis)
    start=tuple(f32(p+d) for p,d in zip(endpoint,extent))
    end=tuple(f32(p-d) for p,d in zip(endpoint,extent))
    delta=tuple(f32(b-a) for a,b in zip(start,end))
    squares=tuple(f32(x*x) for x in delta[:3])
    length=f32(math.sqrt(f32(squares[0]+f32(squares[1]+squares[2]))))
    direction=tuple(f32(x/length) if length>0 else x for x in delta[:3])+(0.,)
    if not all(math.isfinite(x) for x in start+end+direction+(length,)):
        raise ValueError('finite query geometry required')
    return {'start':start,'end':end,'direction':direction,'range':length}


def orient_pose_contact_direction(direction, normal, accepted):
    """Flip the above-limit direction only for an accepted positive dot4.

    The below-limit direction has already been computed and is not flipped.
    A rejected query does not read the normal. See CENTRAL_IMPULSE.md.
    """
    import math
    direction=tuple(map(f32,direction))
    if len(direction)!=4 or not all(math.isfinite(x) for x in direction):
        raise ValueError('finite four-lane direction required')
    if type(accepted) is not bool:raise ValueError('boolean accepted flag required')
    if not accepted:return direction
    normal=tuple(map(f32,normal))
    if len(normal)!=4 or not all(math.isfinite(x) for x in normal):
        raise ValueError('finite four-lane normal required')
    products=tuple(f32(a*b) for a,b in zip(direction,normal))
    dot=f32(f32(products[1]+products[3])+f32(products[0]+products[2]))
    return tuple(-x for x in direction) if dot>0 else direction


def resolved_pose_contact(*, endpoint, axis, initial_point, initial_normal,
                          initial_scalar, above_direction, hits):
    """Compose query geometry and supplied-hit response for one endpoint.

    This inspection API takes ordered hits from its caller. It does not run a
    collision backend or infer the provider transform or adjustment directions.
    """
    segment=pose_contact_segment(endpoint,axis)
    contact=resolve_pose_contacts(axis,initial_point,initial_normal,initial_scalar,hits)
    direction=orient_pose_contact_direction(above_direction,contact['normal'],contact['accepted'])
    return {'segment':segment,'contact':contact,'above_direction':direction}


def contacted_pose_tail(contact_inputs, **tail_inputs):
    """Feed two supplied-hit contact results into the recovered active tail.

    Provider selection, raycast execution and direction generation remain caller
    responsibilities. Rejected contacts retain their local output mutations.
    """
    if not isinstance(contact_inputs,(list,tuple)) or len(contact_inputs)!=2:
        raise ValueError('two endpoint contact observations required')
    reserved={'endpoints','above_directions','contact_scalars'}
    if reserved.intersection(tail_inputs):
        raise ValueError('contact-owned tail inputs must not be supplied twice')
    contacts=tuple(resolved_pose_contact(axis=tail_inputs['axis'],**c) for c in contact_inputs)
    tail=resolved_pose_tail(**tail_inputs,
        endpoints=tuple(c['contact']['point'] for c in contacts),
        above_directions=tuple(c['above_direction'] for c in contacts),
        contact_scalars=tuple(c['contact']['scalar'] for c in contacts))
    return {'contacts':contacts,'tail':tail}


def pose_adjustment_directions(rotation, axis, reciprocal_sqrt):
    """Recovered endpoint basis and two cross-product normalizations.

    rotation is XYZW without implicit normalization. The callback supplies an
    RSQRT estimate for each non-tiny squared length, in evaluation order. Tiny
    vectors retain their original components. Caller/provider frames are inputs.
    """
    import math
    q,a=tuple(map(f32,rotation)),tuple(map(f32,axis))
    if len(q)!=4 or len(a)!=4 or not all(math.isfinite(x) for x in q+a):
        raise ValueError('finite four-lane rotation and axis required')
    x,y,z,w=q
    yz=f32(f32(y*y)+f32(z*z))
    xywz=f32(f32(w*z)+f32(y*x))
    xzwy=f32(f32(z*x)-f32(w*y))
    basis=(f32(1.-f32(yz+yz)),f32(xywz+xywz),f32(xzwy+xzwy),0.)
    def cross(p,q):
        return tuple(f32(f32(p[i]*q[j])-f32(p[j]*q[i]))
                     for i,j in ((1,2),(2,0),(0,1)))+(0.,)
    def normalize(v):
        sq=tuple(f32(x*x) for x in v)
        n=f32(f32(sq[1]+sq[3])+f32(sq[0]+sq[2]))
        if n<=f32(1e-10):return v
        s=f32(reciprocal_sqrt(n))
        if not math.isfinite(s):raise ValueError('finite reciprocal-square-root estimate required')
        k=f32(f32(3.-f32(f32(s*n)*s))*f32(s*.5))
        return tuple(f32(k*x) for x in v)
    above=normalize(cross(a,basis))
    below=normalize(cross(above,a))
    return {'basis':basis,'above_direction':above,'below_direction':below}


def pose_contact_axis(reference_position, origin, fallback_axis):
    """Recovered Reference-to-origin axis with inclusive .01 length fallback.

    Position W lanes are cleared before subtraction. The selected transform's
    fallback axis is copied unchanged, including W, and is not normalized here.
    Transform selection/lifetime are outside this resolved-input interface.
    """
    import math
    def vector(values):
        v=tuple(map(f32,values))
        if len(v)!=4 or not all(math.isfinite(x) for x in v):
            raise ValueError('finite four-lane observations required')
        return v
    p,o=vector(reference_position),vector(origin)
    delta=tuple(f32(a-b) for a,b in zip(p[:3],o[:3]))+(0.,)
    squares=tuple(f32(x*x) for x in delta)
    length=f32(math.sqrt(f32(f32(squares[1]+squares[3])+f32(squares[0]+squares[2]))))
    fallback=vector(fallback_axis)
    use_fallback=length<=f32(.01)
    axis=fallback if use_fallback else tuple(f32(x/length) for x in delta)
    return {'axis':axis,'length':length,'used_fallback':use_fallback,
            'reference_position':p[:3]+(0.,),'delta':delta}


def entity_pose_transform(basis_rows, position, stored_scalar):
    """Recovered entity-record conversion to position/scalar plus XYZW rotation.

    Three four-lane basis rows are supplied in storage order. Position XYZ is
    copied and W replaced by the entity's stored scalar. No orthonormalization,
    normalization or implicit indirect-transform refresh occurs in this helper.
    """
    import math
    rows=tuple(tuple(map(f32,row)) for row in basis_rows)
    p=tuple(map(f32,position));scalar=f32(stored_scalar)
    if (len(rows)!=3 or any(len(row)!=4 for row in rows) or len(p)!=4 or
            not all(math.isfinite(x) for row in rows for x in row) or
            not all(math.isfinite(x) for x in p+(scalar,))):
        raise ValueError('finite basis rows, position and stored scalar required')
    m=rows
    trace=f32(f32(f32(m[0][0]+m[1][1])+m[2][2])+1.)
    if trace>1.:
        numerators=(f32(m[1][2]-m[2][1]),f32(m[2][0]-m[0][2]),
                    f32(m[0][1]-m[1][0]),trace)
        branch='trace';radicand=trace
    else:
        i=1 if m[1][1]>m[0][0] else 0
        if m[2][2]>m[i][i]:i=2
        j=(i+1)%3;k=(j+1)%3
        radicand=f32(f32(f32(m[i][i]-m[j][j])-m[k][k])+1.)
        values=[0.]*4
        values[i]=radicand
        values[j]=f32(m[i][j]+m[j][i])
        values[k]=f32(m[k][i]+m[i][k])
        values[3]=f32(m[j][k]-m[k][j])
        numerators=tuple(values);branch=('x','y','z')[i]
    if not math.isfinite(radicand) or radicand<=0:
        raise ValueError('positive finite rotation conversion radicand required')
    root=f32(math.sqrt(radicand));denominator=f32(root+root)
    rotation=tuple(f32(x/denominator) for x in numerators)
    return {'position_scalar':p[:3]+(scalar,),'rotation':rotation,'branch':branch}


def provider_pose_transform(position, rotation, parent_position, parent_rotation, direct):
    """Recovered provider direct/composed branch, without implicit scaling.

    Inputs are four lanes, quaternions XYZW. Direct mode ignores parent records.
    Composition rotates XYZ, adds parent position and multiplies quaternions in
    native float32 order. No quaternion normalization is performed.
    """
    import math
    def vec(a):
        a=tuple(map(f32,a))
        if len(a)!=4 or not all(math.isfinite(x) for x in a):
            raise ValueError('finite four-lane provider data required')
        return a
    v,c=vec(position),vec(rotation)
    if type(direct) is not bool:raise ValueError('boolean direct mode required')
    if direct:return {'position':v,'rotation':c}
    p,q=vec(parent_position),vec(parent_rotation)
    dot=f32(f32(q[0]*v[0])+f32(f32(q[1]*v[1])+f32(q[2]*v[2])))
    cross=tuple(f32(f32(q[i]*v[j])-f32(v[i]*q[j]))
                for i,j in ((1,2),(2,0),(0,1)))+(0.,)
    wterm=f32(f32(q[3]*q[3])-.5)
    transformed=tuple(f32(f32(f32(f32(f32(cross[i]*q[3])+f32(dot*q[i]))+
                                      f32(wterm*v[i]))*(2. if i<3 else 0.))+p[i]) for i in range(4))
    x,y,z,w=q
    terms=((x,-x,x,-x),(y,y,-y,-y),(-z,z,z,-z))
    permutations=((c[3],c[2],c[1],c[0]),(c[2],c[3],c[0],c[1]),(c[1],c[0],c[3],c[2]))
    composed=tuple(f32(w*n) for n in c)
    for coefficients,values in zip(terms,permutations):
        composed=tuple(f32(f32(a*b)+old) for a,b,old in zip(coefficients,values,composed))
    return {'position':transformed,'rotation':composed}


def pose_endpoint_origin(position, rotation):
    """Recovered endpoint origin: xyz0(position) minus .13 times rotation Y.

    The quaternion is used as supplied. This origin seeds the contact query,
    initial endpoint and later output-stage base. It is not a provider position.
    """
    import math
    p,q=tuple(map(f32,position)),tuple(map(f32,rotation))
    if len(p)!=4 or len(q)!=4 or not all(math.isfinite(x) for x in p+q):
        raise ValueError('finite four-lane endpoint position and rotation required')
    x,y,z,w=q
    a=f32(f32(x*y)-f32(w*z));b=f32(f32(x*w)+f32(y*z))
    squared=f32(f32(x*x)+f32(z*z))
    direction=(f32(a+a),f32(1.-f32(squared+squared)),f32(b+b),0.)
    masked=p[:3]+(0.,)
    origin=tuple(f32(v-f32(f32(.13)*d)) for v,d in zip(masked,direction))
    return {'origin':origin,'rotation':q,'direction':direction}


def pose_channel_index(entries, key):
    """Unsigned lower-bound lookup; first equal key, low-16 index or 0xffff.

    Sorted entries are (uint32 key, uint32 encoded_index). Missing table is None.
    Sorting and shape checks are authored inspection policy, not native guards.
    """
    if type(key) is not int or not 0<=key<2**32:raise ValueError('uint32 channel key required')
    if entries is None:return 0xffff
    if not isinstance(entries,(list,tuple)) or len(entries)>65535:
        raise ValueError('at most 65535 sorted entries required')
    previous=-1
    for row in entries:
        if len(row)!=2 or any(type(x) is not int or not 0<=x<2**32 for x in row):
            raise ValueError('uint32 key/index pairs required')
        if row[0]<previous:raise ValueError('channel table must be sorted by unsigned key')
        previous=row[0]
    lo,hi=0,len(entries)
    while lo<hi:
        mid=(lo+hi)//2
        if entries[mid][0]<key:lo=mid+1
        else:hi=mid
    return entries[lo][1]&0xffff if lo<len(entries) and entries[lo][0]==key else 0xffff


def resolve_pose_channel(bank, key):
    """Resolve a supplied table and 32-byte-record bank, without native pointers.

    Bounds/missing failures are reported before any access. This is stricter than
    the native raw indexed accessor and is not a reconstruction of all callers'
    missing-channel behavior.
    """
    index=pose_channel_index(bank['entries'],key)
    if index==0xffff:raise ValueError('missing pose channel')
    records=bank['records']
    if not isinstance(records,(list,tuple)) or index>=len(records):
        raise ValueError('pose channel index outside supplied record bank')
    record=records[index]
    return {'position':record['position'],'rotation':record['rotation'],
            'parent_position':bank['parent_position'],'parent_rotation':bank['parent_rotation'],
            'direct':bank['direct']}


def acquire_pose_provider(cached_tag, cached_index, entity_tag, components, lookup):
    """Recovered entity component cache protocol for pose-provider acquisition.

    Tags are bytes; indices are uint16. 0xfffe forces lookup, 0xffff caches a
    missing component. lookup returns a supplied component index or None. This
    API models the protocol, not the original virtual type-search internals.
    """
    for value,limit in ((cached_tag,256),(entity_tag,256),(cached_index,65536)):
        if type(value) is not int or not 0<=value<limit:raise ValueError('byte tags and uint16 index required')
    if not isinstance(components,(list,tuple)) or len(components)>65535:
        raise ValueError('bounded supplied component array required')
    refreshed=cached_index==0xfffe or cached_tag!=entity_tag
    if refreshed:
        cached_tag=entity_tag
        found=lookup()
        if found is None:cached_index=0xffff
        elif type(found) is not int or not 0<=found<len(components):
            raise ValueError('lookup index outside supplied component array')
        else:cached_index=found
    if cached_index==0xffff:selected=None
    elif cached_index>=len(components):raise ValueError('cached index outside supplied component array')
    else:selected=components[cached_index]
    return {'cached_tag':cached_tag,'cached_index':cached_index,
            'refreshed':refreshed,'component':selected}


def component_type_slot(type_ranges, requested_range):
    """Recovered candidate virtual search: range containment plus lower bound.

    Each descriptor supplies two uint16 values. Receiver binding to the active
    player entity is not established. Input ordering is preserved, not repaired.
    Returns a logical slot or None; no component ownership/lifetime is implied.
    """
    def pair(v):
        if len(v)!=2 or any(type(x) is not int or not 0<=x<65536 for x in v):
            raise ValueError('two uint16 descriptor bounds required')
        return tuple(v)
    if not isinstance(type_ranges,(list,tuple)) or len(type_ranges)>65535:
        raise ValueError('bounded descriptor sequence required')
    ranges=tuple(pair(r) for r in type_ranges);low,high=pair(requested_range)
    def contained(r):return low<=r[0] and r[1]<=high
    start,count=0,len(ranges)
    while count:
        half=count//2;mid=start+half;r=ranges[mid]
        if not contained(r) and r[0]<low:
            start=mid+1;count-=half+1
        else:count=half
    return start if start<len(ranges) and contained(ranges[start]) else None


def acquire_pose_provider_by_ranges(cached_tag, cached_index, entity_tag,
                                    components, type_ranges, requested_range):
    """Compose the recovered cache and bound entity-family type search.

    Caller establishes receiver-family applicability and supplies descriptors.
    This does not acquire a live entity or establish component lifetime.
    """
    def lookup():
        if len(type_ranges)!=len(components):
            raise ValueError('one descriptor range per supplied component required')
        return component_type_slot(type_ranges,requested_range)
    return acquire_pose_provider(cached_tag,cached_index,entity_tag,components,lookup)


def number_type_subtree(children, root, counter):
    """Recovered entry/exit numbering for a supplied ordered type subtree.

    Counter increments wrap at uint16. Tree shape/order are supplied, not inferred
    from game metadata. Structural validation is authored inspection policy.
    """
    if not isinstance(children,(list,tuple)) or not 1<=len(children)<=4096:
        raise ValueError('bounded supplied child lists required')
    if type(root) is not int or not 0<=root<len(children) or type(counter) is not int or not 0<=counter<65536:
        raise ValueError('valid root and uint16 counter required')
    ranges=[None]*len(children);seen=set();stack=[(root,False)]
    while stack:
        node,leaving=stack.pop()
        if leaving:
            counter=(counter+1)&0xffff;ranges[node][1]=counter;continue
        if type(node) is not int or not 0<=node<len(children) or node in seen:
            raise ValueError('tree must contain valid unrepeated reachable nodes')
        if not isinstance(children[node],(list,tuple)):raise ValueError('child sequence required')
        seen.add(node);counter=(counter+1)&0xffff;ranges[node]=[counter,None]
        stack.append((node,True));stack.extend((child,False) for child in reversed(children[node]))
    return {'ranges':ranges,'counter':counter}


def assign_type_ranges(parents, order, root):
    """Recovered post-sort child-index, root traversal and unvisited fallback.

    Type IDs are logical array indices. Supplied order is not sorted here.
    Registry enumeration, callbacks and comparator behavior remain external.
    """
    if not isinstance(parents,(list,tuple)) or not 1<=len(parents)<=4096:
        raise ValueError('bounded parent table required')
    n=len(parents)
    if (not isinstance(order,(list,tuple)) or len(order)!=n or
            any(type(x) is not int for x in order) or sorted(order)!=list(range(n))):
        raise ValueError('descriptor order must be a permutation')
    if type(root) is not int or not 0<=root<n:raise ValueError('valid root required')
    if any(p is not None and (type(p) is not int or not 0<=p<n) for p in parents):
        raise ValueError('valid parent indices required')
    first=[None]*n;previous=None
    for i,node in enumerate(order):
        parent=parents[node]
        if parent is not None and parent!=previous:
            first[parent]=i;previous=parent
    children=[[] for _ in parents]
    for parent,start in enumerate(first):
        if start is None:continue
        for node in order[start:]:
            if parents[node]!=parent:break
            children[parent].append(node)
    result=number_type_subtree(children,root,1)
    ranges=result['ranges'];counter=result['counter'];fallback=[]
    for node in order:
        if ranges[node] is None:
            lower=counter;counter=(counter+1)&0xffff
            upper=counter;counter=(counter+1)&0xffff
            ranges[node]=[lower,upper];fallback.append(node)
    return {'ranges':ranges,'counter':counter,'first_child':first,'fallback_nodes':fallback}


def type_descriptor_order(keys, partition_budget=None):
    """Recovered lexicographic descriptor ordering with explicit tie boundary.

    Keys are uint32, uint16, uint32 in native comparison order. Median selection,
    equal-key partition swaps and smaller-side recursion preserve native order.
    Exhausting the partition budget uses the recovered heap fallback. The normal
    caller starts the budget at the record count; an override supports inspection.
    """
    if not isinstance(keys,(list,tuple)) or len(keys)>65535:
        raise ValueError('bounded descriptor-key sequence required')
    values=[]
    for key in keys:
        if len(key)!=3 or any(type(x) is not int or not 0<=x<limit
                             for x,limit in zip(key,(2**32,2**16,2**32))):
            raise ValueError('uint32/uint16/uint32 descriptor key required')
        values.append(tuple(key))
    order=list(range(len(values)))
    def sort(first,last,budget):
        while last-first>32:
            if budget<=0:
                _heap_type_keys(order,values,first,last)
                return
            left,right=_partition_type_keys(order,values,first,last)
            half=budget//2;budget=half+half//2
            if left-first<last-right:
                sort(first,left,budget);first=right
            else:
                sort(right,last,budget);last=left
        order[first:last]=sorted(order[first:last],key=values.__getitem__)
    budget=len(order) if partition_budget is None else partition_budget
    if type(budget) is not int or budget<0:raise ValueError('nonnegative partition budget required')
    sort(0,len(order),budget)
    return order



def _partition_type_keys(order, keys, first, last):
    """Recovered median selection and three-way equal-key partition."""
    def less(a,b):return keys[order[a]]<keys[order[b]]
    def equal(a,b):return keys[order[a]]==keys[order[b]]
    def swap(a,b):order[a],order[b]=order[b],order[a]
    def median(a,b,c):
        if less(b,a):swap(a,b)
        if less(c,b):
            swap(b,c)
            if less(b,a):swap(a,b)
    middle=first+(last-first)//2;end=last-1
    if end-first>40:
        step=(last-first)//8
        median(first,first+step,first+2*step)
        median(middle-step,middle,middle+step)
        median(end-2*step,end-step,end)
        median(first+step,middle,end-step)
    else:median(first,middle,end)
    pivot_first=middle;pivot_last=middle+1
    while first<pivot_first and equal(pivot_first-1,pivot_first):pivot_first-=1
    while pivot_last<last and equal(pivot_last,pivot_first):pivot_last+=1
    right=pivot_last;left=pivot_first
    while True:
        while right<last:
            if less(pivot_first,right):right+=1;continue
            if less(right,pivot_first):break
            swap(pivot_last,right);pivot_last+=1;right+=1
        while first<left:
            candidate=left-1
            if less(candidate,pivot_first):left-=1;continue
            if less(pivot_first,candidate):break
            pivot_first-=1;swap(pivot_first,candidate);left-=1
        if left==first:
            if right==last:return pivot_first,pivot_last
            if pivot_last!=right:swap(pivot_first,pivot_last)
            swap(pivot_first,right)
            pivot_first+=1;pivot_last+=1;right+=1
        else:
            left-=1
            if right==last:
                pivot_first-=1
                if left!=pivot_first:swap(left,pivot_first)
                pivot_last-=1;swap(pivot_first,pivot_last)
            else:
                swap(right,left);right+=1



def _heap_type_keys(order,keys,first,last):
    """Recovered bottom-up heap construction and pop order; right wins ties."""
    def adjust(top,size,value):
        hole=top
        while 2*hole+2<size:
            child=2*hole+2
            if keys[order[first+child]]<keys[order[first+child-1]]:child-=1
            order[first+hole]=order[first+child];hole=child
        if 2*hole+1<size:
            child=2*hole+1;order[first+hole]=order[first+child];hole=child
        while hole>top:
            parent=(hole-1)//2
            if not keys[order[first+parent]]<keys[value]:break
            order[first+hole]=order[first+parent];hole=parent
        order[first+hole]=value
    size=last-first
    for top in range(size//2-1,-1,-1):adjust(top,size,order[first+top])
    for end in range(size-1,0,-1):
        value=order[first+end];order[first+end]=order[first]
        adjust(0,end,value)


def prepare_type_ranges(parents, keys, root):
    """Compose native descriptor sorting and post-sort range assignment.

    Keys are observations after registration callbacks. Their lower-range field
    is sampled before assignment overwrites it. Registry population is external.
    """
    if len(parents)!=len(keys):raise ValueError('one sort key per descriptor required')
    order=type_descriptor_order(keys)
    return {'order':order,**assign_type_ranges(parents,order,root)}


def link_type_parents(parent_keys, previous_parents, lookup):
    """Recovered registry parent-link pass with supplied key lookup service.

    Successful lookup replaces a parent; a miss preserves the existing value.
    Logical descriptor indices stand in for native pointers. Lookup data and
    descriptor enumeration are caller-supplied, not decoded registry internals.
    """
    if (not isinstance(parent_keys,(list,tuple)) or len(parent_keys)>4096 or
            len(parent_keys)!=len(previous_parents)):
        raise ValueError('matching bounded parent-key and previous-parent arrays required')
    n=len(parent_keys);result=list(previous_parents)
    for p in result:
        if p is not None and (type(p) is not int or not 0<=p<n):raise ValueError('valid previous parent required')
    for i,key in enumerate(parent_keys):
        if type(key) is not int or not 0<=key<2**32:raise ValueError('uint32 parent key required')
        found=lookup(key)
        if found is not None:
            if type(found) is not int or not 0<=found<n:raise ValueError('lookup parent outside supplied descriptors')
            result[i]=found
    return result


def compact_type_registry_index(keys, key):
    """Recovered compact registry lookup, returning a logical value-slot index.

    See CENTRAL_IMPULSE.md, Compact registry lookup. Native root tag 1 stores
    1..31 sorted uint64 keys. None denotes the separate null-root case. Other
    root representations, allocation and live pointer ownership are external.
    Bounds and sortedness checks are authored inspection safeguards.
    """
    if type(key) is not int or not 0 <= key < 2**64:
        raise ValueError('uint64 lookup key required')
    if keys is None:
        return None
    if not isinstance(keys, (list, tuple)) or not 1 <= len(keys) <= 31:
        raise ValueError('compact registry requires 1..31 keys; use None for null root')
    if any(type(k) is not int or not 0 <= k < 2**64 for k in keys):
        raise ValueError('uint64 registry keys required')
    if any(a > b for a, b in zip(keys, keys[1:])):
        raise ValueError('sorted registry keys required')
    if key > keys[-1]:
        return None
    index = 0
    while key > keys[index]:
        index += 1
    return index if key == keys[index] else None


def compact_type_registry_cursor(keys, key, *, advance=False):
    """Recovered compact first-at-or-after / next cursor behavior.

    Returns key and logical slot index. Next increments the uint64 cursor before
    searching, even on exhaustion, except that a null root leaves it unchanged.
    At uint64 maximum it wraps the cursor to zero and returns no slot. Reusing
    that exhausted cursor can restart traversal; callers must stop on no slot.
    """
    exact = compact_type_registry_index(keys, key)  # Also validates inputs.
    if type(advance) is not bool:
        raise ValueError('boolean advance required')
    if not advance and exact is not None:
        return {'key': key, 'index': exact}
    if keys is None:
        return {'key': key, 'index': None}
    previous = key
    key = (key + 1) & (2**64 - 1)
    if previous == 2**64 - 1:
        return {'key': key, 'index': None}
    for index, candidate in enumerate(keys):
        if candidate >= key:
            return {'key': candidate, 'index': index}
    return {'key': key, 'index': None}


def link_compact_type_registry(registry_keys, descriptor_indices,
                               parent_keys, previous_parents):
    """Compose native compact iteration and parent linking with logical IDs.

    Descriptor arrays can include unregistered descriptors, which stay unchanged.
    Keys and value slots are supplied decoded data; allocation is not modeled.
    Duplicate registry keys are skipped after their first slot during traversal.
    See CENTRAL_IMPULSE.md, Compact registry iteration and complete parent linking.
    """
    cursor = compact_type_registry_cursor(registry_keys, 0)
    # Reuse authored parent-array validation without assigning any new links.
    result = link_type_parents(parent_keys, previous_parents, lambda key: None)
    expected = 0 if registry_keys is None else len(registry_keys)
    if not isinstance(descriptor_indices, (list, tuple)) or len(descriptor_indices) != expected:
        raise ValueError('one logical descriptor per registry slot required')
    if any(type(i) is not int or not 0 <= i < len(result) for i in descriptor_indices):
        raise ValueError('registry descriptor outside supplied descriptors')
    visited = []
    while cursor['index'] is not None:
        slot = cursor['index']
        visited.append(slot)
        descriptor = descriptor_indices[slot]
        parent_slot = compact_type_registry_index(registry_keys, parent_keys[descriptor])
        if parent_slot is not None:
            result[descriptor] = descriptor_indices[parent_slot]
        cursor = compact_type_registry_cursor(registry_keys, cursor['key'], advance=True)
    return {'parents': result, 'visited_slots': visited, 'cursor_key': cursor['key']}


def pose_bank_layout(flags, primary_bytes, alternate_bytes, transform_count):
    """Recovered metadata selection; capacity check is authored inspection policy.

    Bank metadata has uint16 byte sizes at +0x14/+0x16 and transform count at
    +0x5a. Flag bit 28 selects the alternate size. No allocation/lifetime proof.
    """
    if type(flags) is not int or not 0 <= flags < 2**32:
        raise ValueError('uint32 provider flags required')
    if any(type(v) is not int or not 0 <= v <= 65535
           for v in (primary_bytes, alternate_bytes, transform_count)):
        raise ValueError('uint16 bank metadata required')
    size = alternate_bytes if flags & (1 << 28) else primary_bytes
    return dict(allocation_bytes=size, transform_count=transform_count,
                transform_bytes=transform_count * 32,
                transforms_fit_allocation=transform_count * 32 <= size,
                alternate_allocation=bool(flags & (1 << 28)))
