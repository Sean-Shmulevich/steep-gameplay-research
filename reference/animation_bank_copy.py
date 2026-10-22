"""Recovered masked and full-mask bank copy.

Evidence: CENTRAL_IMPULSE.md, Masked pose-bank record copy.
Byte storage is supplied, not extracted game data. Bounds checks are authored.
"""

def _layout(bank):
    # Native metadata comes through the bank profile. Flat inputs remain supported
    # for earlier isolated receipts; never prefer stale flat fields over a profile.
    profile=bank.get('profile')
    return bank if profile is None else profile


def copy_masked_pose_bank(destination, source, mode, request_mask):
    if type(request_mask) is not int or not 0<=request_mask<65535:
        raise ValueError('partial uint16 mask required; use copy_pose_bank for full-mask bulk copy')
    if type(mode) is not int or not 0<=mode<=7:
        raise ValueError('three-bit mode required')
    count=_layout(source)['group_count']
    if type(count) is not int or not 0<=count<=16:
        raise ValueError('at most 16 groups in this adapter')
    if len(source['parent_header'])!=32:raise ValueError('32-byte source header required')
    if not destination['flags'] & (1<<26):
        destination['parent_header']=bytes(source['parent_header'])
    data=destination['data'];src=source['data'];visited=[]
    for group in range(count):
        if not request_mask & (1<<group):continue
        # Seven uint16s per native group. Mode accesses can cross row boundaries.
        layout=_layout(destination);table=layout['group_words'];base=group*7
        start=table[base];length=table[base+mode+1]
        if start<0 or length<0 or start+length>len(layout['descriptors']):
            raise ValueError('descriptor range outside supplied table')
        for descriptor in layout['descriptors'][start:start+length]:
            offset=descriptor['offset'];kind=descriptor['kind'] & 15
            size=16 if kind>=5 else 1 if kind==0 else 12 if kind==4 else 4
            if type(offset) is not int or offset<0 or offset+size>min(len(src),len(data)):
                raise ValueError('descriptor outside supplied storage')
            data[offset:offset+size]=src[offset:offset+size]
        visited.append(dict(group=group,start=start,count=length))
    destination['flags'] |= 1<<27
    return visited


def copy_pose_bank(destination, source, mode, request_mask):
    """Dispatch masked copy or full storage copy with validated layout boundaries.

    Evidence: CENTRAL_IMPULSE.md, Full-mask pose-bank copy.
    Full-path buffers must be separate or exactly identical, not partly overlapping.
    """
    if request_mask!=65535:
        return dict(path='masked',groups=copy_masked_pose_bank(destination,source,mode,request_mask))
    first,second,total=_layout(source)['bulk_boundaries']
    if any(type(x) is not int for x in (first,second,total)) or not 0<=first<=second<=total<=65535:
        raise ValueError('ordered uint16 bulk boundaries required')
    if first%32 or (second-first)%4:
        raise ValueError('32-byte first region and four-byte middle region required')
    if total>min(len(source['data']),len(destination['data'])) or len(source['parent_header'])!=32:
        raise ValueError('supplied bank storage/header too short')
    if not destination['flags'] & (1<<26):destination['parent_header']=bytes(source['parent_header'])
    # Under the stated alignment/disjointness constraints the three native loops
    # copy one contiguous prefix, leaving trailing storage untouched.
    destination['data'][:total]=source['data'][:total]
    destination['flags'] |= 1<<27
    return dict(path='full',regions=[[0,first],[first,second],[second,total]])
