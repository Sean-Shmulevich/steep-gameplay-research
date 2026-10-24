"""Recovered body and constraint redistribution between retained groups.

Evidence: CENTRAL_IMPULSE.md, Group migration and constraint ownership.
"""


def migrate_pose_group(source, destinations, *, groups, bodies, links, poses, grow):
    """Mutate active arrays and preserve inactive tails.

    destinations has slots and mutable count matching source body count on entry.
    grow(group, family, capacity) supplies writable storage for bodies/links/poses.
    Group/record tokens identify retained dictionaries, not native pointers.
    """
    def append(group,family,token,record):
        prefix='' if family=='bodies' else ('link_' if family=='links' else 'pose_')
        ck=prefix+'count';sk=prefix+'slots';cap=prefix+'capacity'
        n=group[ck]
        if family=='poses' and n>=65535:return False
        if family!='links':record['group']=group['token']
        record['index']=n
        if n==group[cap]:
            size=(group[cap]*2)&0xffffffff
            if family=='poses' and group[cap]==0:size=8
            grow(group,family,size)
        n=group[ck]
        if not 0<=n<len(group[sk]):raise ValueError('Writable destination storage required')
        group[sk][n]=token;group[ck]=(n+1)&0xffffffff
        return True
    if destinations['count']!=source['count']:
        raise ValueError('Destination count must match retained source bodies')
    index=0
    while index<destinations['count']:
        target=destinations['slots'][index]
        if target==source['token']:
            index+=1;continue
        destination=groups[target]
        token=source['slots'][index];body=bodies[token]
        source['count']-=1
        source['slots'][index]=source['slots'][source['count']]
        if index<destinations['count']-1:
            moved=bodies[source['slots'][index]]
            moved['group']=source['token'];moved['index']=index
            destinations['slots'][index]=destinations['slots'][destinations['count']-1]
        destinations['count']-=1
        append(destination,'bodies',token,body)
    index=0;remaining=source['link_count']
    while index<remaining:
        token=source['link_slots'][index];record=links[token]
        target=bodies[record['first']]['group']
        if target==source['token']:
            index+=1;continue
        old_index=record['index'];source['link_count']-=1
        count=source['link_count'];source['link_slots'][old_index]=source['link_slots'][count]
        record['index']=0xffffffff
        if old_index<count:links[source['link_slots'][old_index]]['index']=old_index
        remaining-=1
        append(groups[target],'links',token,record)
    index=0;remaining=source['pose_count']
    while index<remaining:
        token=source['pose_slots'][index];record=poses[token]
        target=bodies[record['first']]['group']
        if target==source['token']:
            index+=1;continue
        source['pose_count']-=1
        source['pose_slots'][index]=source['pose_slots'][source['pose_count']]
        if index<remaining-1:
            moved=poses[source['pose_slots'][index]]
            moved['group']=source['token'];moved['index']=index
        record['group']=0;record['index']=0xffffffff;remaining-=1
        append(groups[target],'poses',token,record)
