"""Inspect completed lock events, not attempted/blocking calls.

Authored trace-consistency policy. This does not implement a native lock, prove
trace completeness, establish memory ordering or validate object lifetime.
"""


def inspect_completed_lock_events(events):
    owner=None;depth=0;maximum=0;observations=[]
    for index,event in enumerate(events):
        operation=event.get('operation');thread=event.get('thread')
        if not isinstance(thread,str) or not thread or operation not in ('enter','leave'):
            raise ValueError('completed enter/leave event with nonempty thread identity required')
        if operation=='enter':
            if depth and owner!=thread:
                raise ValueError('completed acquisition conflicts with recorded owner')
            owner=thread;depth+=1;maximum=max(maximum,depth)
        else:
            if depth==0 or owner!=thread:
                raise ValueError('release without matching recorded ownership')
            depth-=1
            if not depth:owner=None
        if 'depth_after' in event and event['depth_after']!=depth:
            raise ValueError('reported recursion depth disagrees with event history')
        observations.append(dict(index=index,owner=owner,depth=depth))
    return dict(owner=owner,depth=depth,max_depth=maximum,balanced=depth==0,
                observations=observations,trace_completeness_proven=False)
