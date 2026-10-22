"""Recovered primary-to-current hierarchy conversion after work application.

Evidence: CENTRAL_IMPULSE.md, Preparation hierarchy conversion.
Ranks and skip spans are supplied metadata, not inferred animation LOD policy.
"""
from reference.ground_response_pose import provider_pose_transform
from reference.snow import f32


def decompose_bank_hierarchy(source, destination, metadata, mask, reciprocal_sqrt):
    """Derive parent-relative records in native forward traversal order.

    Evidence: CENTRAL_IMPULSE.md, Parent-relative bank conversion.
    None or source itself means in-place conversion. Parent reads then see any
    earlier writes, deliberately preserving native aliasing rather than silently
    snapshotting the original hierarchy. Bounds checks are authored safeguards.
    """
    alias=destination is None or destination is source
    src=[(tuple(p),tuple(q)) for p,q in source]
    dst=src if alias else [(tuple(p),tuple(q)) for p,q in destination]
    if len(src)!=len(dst) or len(metadata)!=len(src) or type(mask) is not int or not 0<=mask<=7:
        raise ValueError('matching banks/metadata and three-bit mask required')
    visited=[];skipped=[];i=0
    while i<len(src):
        row=metadata[i]
        if i and row['rank']>mask:
            step=row['skip_span']+1
            if type(step) is not int or not 1<=step<=65535:
                raise ValueError('nonwrapping positive skip required')
            skipped.append([i,min(i+step,len(src))]);i+=step;continue
        p,q=src[i]
        if i:
            parent=row['parent']
            if type(parent) is not int or not 0<=parent<i:
                raise ValueError('preceding parent required')
            pp,pq=src[parent]
            p=tuple(f32(f32(a)-f32(b)) for a,b in zip(p,pp))
            pq=tuple(-f32(x) for x in pq[:3])+(f32(pq[3]),)
        else:pq=(0.,0.,0.,1.)
        pose=provider_pose_transform(p,q,(-0.,)*4,pq,False)
        rotation=pose['rotation'];sq=[f32(x*x) for x in rotation]
        norm=f32(f32(sq[0]+sq[2])+f32(sq[1]+sq[3]))
        if norm<=0:raise ValueError('positive rotation norm required')
        seed=f32(reciprocal_sqrt(norm))
        factor=f32(f32(3.-f32(f32(seed*norm)*seed))*f32(.5*seed))
        dst[i]=(pose['position'],tuple(f32(x*factor) for x in rotation))
        visited.append(i);i+=1
    return dict(records=dst,visited=visited,skipped=skipped,in_place=alias)


def compose_primary_hierarchy(current, primary, metadata, mask, reciprocal_sqrt):
    current=[(tuple(p),tuple(q)) for p,q in current]
    primary=list(primary);metadata=list(metadata)
    if len(current)!=len(primary) or len(metadata)!=len(primary) or type(mask) is not int or not 0<=mask<=7:
        raise ValueError('matching banks/metadata and three-bit mask required')
    visited=[];skipped=[];i=0
    while i<len(primary):
        row=metadata[i]
        if i and row['rank']>mask:
            step=row['skip_span']+1
            if type(step) is not int or not 1<=step<=65535:
                raise ValueError('nonwrapping positive skip required by adapter')
            skipped.append([i,min(i+step,len(primary))]);i+=step;continue
        if i==0:
            parent_position=(0.,0.,0.,0.);parent_rotation=(0.,0.,0.,1.)
        else:
            parent=row['parent']
            if type(parent) is not int or not 0<=parent<i:
                raise ValueError('preceding parent required by inspection adapter')
            parent_position,parent_rotation=current[parent]
        p,q=primary[i]
        pose=provider_pose_transform(p,q,parent_position,parent_rotation,False)
        if i==0:
            # Root omits the final parent-position add, preserving signed zero W.
            pose['position']=pose['position'][:3]+(f32(f32(.5*f32(p[3]))*0.),)
        rotation=pose['rotation'];squares=[f32(x*x) for x in rotation]
        n=f32(f32(squares[0]+squares[2])+f32(squares[1]+squares[3]))
        if n<=0:raise ValueError('positive rotation norm required')
        seed=f32(reciprocal_sqrt(n));factor=f32(f32(.5*seed)*f32(3.-f32(f32(seed*n)*seed)))
        current[i]=(pose['position'],tuple(f32(x*factor) for x in rotation))
        visited.append(i);i+=1
    return dict(records=current,visited=visited,skipped=skipped)


def reconcile_current_hierarchy(current, primary, metadata, mask, reciprocal_sqrt, processed_count=None):
    """Mode-one alternate processing, selected per metadata bit 3.

    Marked nodes derive primary/local pose from current and its current parent.
    Unmarked nodes rebuild current from primary. Threshold skips preserve both.
    Caller supplies the processed prefix, whose count is distinct in native data.
    """
    current=[(tuple(p),tuple(q)) for p,q in current]
    primary=[(tuple(p),tuple(q)) for p,q in primary]
    metadata=list(metadata)
    if len(current)!=len(primary) or len(metadata)!=len(primary) or type(mask) is not int or not 0<=mask<=7:
        raise ValueError('matching banks/metadata and three-bit mask required')
    if processed_count is None:processed_count=len(primary)
    if type(processed_count) is not int or not 0<=processed_count<=len(primary):
        raise ValueError('processed prefix outside supplied banks')
    # Wrapper tests total count, while helper handles root before prefix comparison.
    limit=max(1,processed_count) if primary else 0
    visited=[];skipped=[];i=0
    while i<limit:
        row=metadata[i]
        if i and row['rank']>mask:
            step=row['skip_span']+1
            if type(step) is not int or not 1<=step<=65535:
                raise ValueError('nonwrapping positive skip required')
            skipped.append([i,min(i+step,limit)]);i+=step;continue
        inverse=row['current_authoritative']
        if type(inverse) is not bool:raise ValueError('boolean authority flag required')
        if i==0:
            p,q=(current if inverse else primary)[i]
            pose=provider_pose_transform(p,q,(-0.,)*4,(0.,0.,0.,1.),False)
        else:
            parent=row['parent']
            if type(parent) is not int or not 0<=parent<i:raise ValueError('preceding parent required')
            pp,pq=current[parent]
            if inverse:
                p,q=current[i]
                delta=tuple(f32(f32(a)-f32(b)) for a,b in zip(p,pp))
                conjugate=tuple(-f32(x) for x in pq[:3])+(f32(pq[3]),)
                pose=provider_pose_transform(delta,q,(-0.,)*4,conjugate,False)
            else:
                p,q=primary[i];pose=provider_pose_transform(p,q,pp,pq,False)
        q=pose['rotation'];sq=[f32(x*x) for x in q]
        n=f32(f32(sq[0]+sq[2])+f32(sq[1]+sq[3]))
        if n<=0:raise ValueError('positive rotation norm required')
        seed=f32(reciprocal_sqrt(n));factor=f32(f32(.5*seed)*f32(3.-f32(f32(seed*n)*seed)))
        record=(pose['position'],tuple(f32(x*factor) for x in q))
        (primary if inverse else current)[i]=record
        visited.append(dict(index=i,destination='primary' if inverse else 'current'));i+=1
    return dict(current=current,primary=primary,visited=visited,skipped=skipped)


def convert_relative_pose_bank(source, destination, mask, reciprocal_sqrt):
    """Whole-bank adapter; see CENTRAL_IMPULSE.md, Joined relative bank selection.

    Bank dictionaries carry records, metadata, parent_header and flags. Header
    is an opaque immutable 32-byte value. Record bounds checks are authored.
    """
    if destination is None:
        destination=source
    result=decompose_bank_hierarchy(source['records'],
        None if destination is source else destination['records'],
        source['metadata'],mask,reciprocal_sqrt)
    if source['records']:
        if len(source['parent_header'])!=32:
            raise ValueError('32-byte parent header required')
        destination['records']=result['records']
        destination['parent_header']=source['parent_header']
        destination['flags']=(destination['flags'] & ~(1<<27)) | (1<<26)
    return result
