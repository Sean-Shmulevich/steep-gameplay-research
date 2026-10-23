"""Compose consumer routing and selected context cleanup on synthetic requests."""
import json
from engine.request_consumer import consume_requests
from engine.request_context_cleanup import complete_request_context


def run_case(materialization_succeeds):
    events=[];manager=dict(stop=False,active=None);target={}
    context=dict(value=7,weak_holder='weak',strong_holder='strong',parameter=None,flags=[0,0,0])
    holders={'weak':dict(status=0,weak=1),'strong':dict(status=1,weak=0)}
    cleanup={name:(lambda *args,name=name:events.append(name)) for name in
             ('activate','refresh','apply_holder','optional0','optional1','optional2',
              'release_strong','release_weak','free_context')}
    cleanup['allocation_token']=lambda c:'synthetic allocation'
    def callback(code,associated,work,c):
        events.append(['callback',code])
        complete_request_context(c,target,holders,services=cleanup)
    work=dict(kind=0,descriptor=None,resource=None,seed=None,payload=None,mode=1,
              associated=None,reload=False,callback=callback,context=context)
    services={name:(lambda *args,name=name:events.append(name)) for name in
              ('reset_event','prepare','defer','release_seed','alternate','lock','unlock')}
    def acquire(m):m['active']=work
    def materialize(w,flag):w['resource']='resource' if materialization_succeeds else None
    def recycle(m,w):events.append(['recycle',m['active'] is None])
    def signal():events.append('signal');manager['stop']=True
    services.update(acquire_active=acquire,descriptor_ready=lambda d:True,
                    materialize=materialize,recycle=recycle,signal=signal)
    result=consume_requests(manager,services=services)
    return dict(materialization_succeeds=materialization_succeeds,events=events,
                callback_count=result['callbacks'],context_free_observed='free_context' in events,
                native_lifecycle_proved=False)


def run():
    return dict(evidence='authored composition of recovered consumer and callback with synthetic services',
                cases=[run_case(True),run_case(False)])


if __name__ == '__main__':print(json.dumps(run(),indent=2))
