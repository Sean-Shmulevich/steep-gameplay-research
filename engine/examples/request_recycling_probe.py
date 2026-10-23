"""Show request reset and free-ring accounting using synthetic storage."""
import json
from engine.request_recycling import reset_request,recycle_request


def run_case(full):
    work=dict(payload='resource',resource_holder='r',descriptor_holder='d',callback='callback',alternate=None,context='context-token',associated=None,marked=False,reload=False,tracked=False,kind=0,mode=1,seed=None)
    holders={'r':dict(status=2),'d':dict(status=2),'default':dict(status=100)}
    pool=dict(slots=['occupied' if full else None],count=int(full),capacity=1,write_index=0,available_total=int(full),normal_outstanding=1)
    events=[]
    services={name:(lambda *args,name=name:events.append(name)) for name in
              ('release_holder','unlink_tracking','lock','unlock','allocation_token','destroy_seed','free_seed')}
    services['clear_associated']=lambda w:w.update(associated=None)
    receipt=recycle_request(pool,work,reset=lambda w:reset_request(w,holders,default_holder='default',services=services),services=services)
    return dict(initially_full=full,inserted=receipt['inserted'],ring_count=pool['count'],
                available_total=pool['available_total'],context_after_reset=work['context'],
                callback_after_reset=work['callback'],normal_outstanding=pool['normal_outstanding'],
                events=events,context_free_proved=False)


if __name__ == '__main__':
    print(json.dumps(dict(evidence='synthetic objects using recovered reset/pool rules',
                         cases=[run_case(False),run_case(True)]),indent=2))
