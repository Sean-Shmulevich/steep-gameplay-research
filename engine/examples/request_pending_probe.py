"""Show category ordering and the resource-preparation stop with synthetic work."""
import json
from engine.request_pending import publish_request,transfer_pending


def ring(capacity=4):
    return dict(slots=[None]*capacity,count=0,capacity=capacity,read_index=0,write_index=0)


def run():
    manager=dict(pending=[ring() for _ in range(4)],ready=ring(),pending_total=0,normal_outstanding=0,wake_counter=-1)
    events=[]
    services={name:(lambda *args,name=name:events.append(name)) for name in ('lock','unlock','notify','before_transfer')}
    services['refill']=lambda m:False
    services['prepare_seed']=lambda w:events.append(['prepare_seed',w['identity']])
    for mode in (3,1,0,2):
        work=dict(identity=f'category-{mode}',mode=mode,kind=0,reload=False,resource=None if mode==1 else 'resource')
        publish_request(manager,work,services=services)
    result=transfer_pending(manager,services=services)
    return dict(evidence='synthetic request objects and lock/seed adapters',result=result,
                ready=[w['identity'] for w in manager['ready']['slots'] if w is not None],
                pending_counts=[r['count'] for r in manager['pending']],
                pending_total=manager['pending_total'],events=events,native_admission_proved=False)


if __name__ == '__main__':print(json.dumps(run(),indent=2))
