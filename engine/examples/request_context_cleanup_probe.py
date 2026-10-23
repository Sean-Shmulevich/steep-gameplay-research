"""Synthetic invocation of decoded request callback cleanup, not native delivery."""
import json
from engine.request_context_cleanup import complete_request_context


def run():
    context=dict(value=7,weak_holder='weak',strong_holder='strong',parameter=None,flags=[0,0,0])
    target={};holders={'weak':dict(status=0,weak=1),'strong':dict(status=1,weak=0)}
    events=[]
    services={name:(lambda *args,name=name:events.append(name)) for name in
              ('activate','refresh','apply_holder','optional0','optional1','optional2',
               'release_strong','release_weak','free_context')}
    services['allocation_token']=lambda c:events.append('allocation_token') or 'synthetic allocation'
    complete_request_context(context,target,holders,services=services)
    return dict(evidence='explicit synthetic invocation of recovered local callback order',
                events=events,target=target,holders=holders,actual_consumer_join_proved=False)


if __name__ == '__main__':print(json.dumps(run(),indent=2))
