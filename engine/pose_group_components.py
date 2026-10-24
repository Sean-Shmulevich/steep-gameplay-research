"""Recovered destination preparation by constraint connectivity propagation.

Evidence: CENTRAL_IMPULSE.md, Constraint-connected destination preparation.
"""


def prepare_pose_group_destinations(group, destinations, *, acquire_group):
    """Clear body destinations, then seed and propagate one component at a time.

    group: token, count, links, poses. Each endpoint is a retained dictionary
    with index and flags16. Pose second endpoints may be None; link endpoints may
    not. Lists are ordered synthetic representations of native pointer arrays.
    Stable topology and nonzero acquired group tokens are caller requirements.
    """
    count=group['count']
    if type(count) is not int or not 0<=count<=len(destinations):
        raise ValueError('Retained destination capacity required')
    destinations[:count]=[0]*count
    components=0;may_seed=True
    while True:
        changed=False
        for name in ('links','poses'):
            records=group[name];length=len(records)
            for index in range(length):
                first,second=records[index]
                if second is None:
                    if name=='poses':continue
                    raise ValueError('Link second endpoint must be retained')
                if not second['flags16']&0x8000:continue
                i,j=first['index'],second['index']
                if not 0<=i<count or not 0<=j<count:raise ValueError('Valid endpoint indices required')
                a,b=destinations[i],destinations[j]
                if not a and not b:
                    if not may_seed:continue
                    token=group['token'] if components==0 else acquire_group()
                    if not token:raise ValueError('Nonzero destination required for propagation')
                    components+=1;may_seed=False
                    destinations[i]=token;destinations[j]=token;changed=True
                elif not a:
                    destinations[i]=b;changed=True
                elif not b:
                    destinations[j]=a;changed=True
        if not changed:
            if may_seed:return components
            may_seed=True
