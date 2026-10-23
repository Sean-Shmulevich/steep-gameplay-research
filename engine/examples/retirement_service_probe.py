"""Joined serial retirement service; synthetic resources and leaf services only."""
import json
from engine.holder_retirement_service import run_retirement_service
from engine.resource_preparation_queue import prepare_resource_queue
from engine.holder_consumer_scope import run_holder_consumer
from engine.holder_consumer_step import consume_holder_step
from engine.holder_cleanup import cleanup_holder
from engine.holder_pool_lookup import locate_holder_pool


def run_probe(*, mode=1, references=0, processing=0, pending=2):
    events=[];depths={};max_depths={}
    payload=dict(name='payload',flags=0x7ffff)
    holder=dict(address=0x300200,status=(1<<24)|references,count=0,payload=payload,token=0xf0000000)
    pool=dict(base=holder['address'],capacity=1,head=19)
    registry=dict(mode=mode,processing=processing,ring=dict(slots=[None,None,None,holder],count=1,capacity=4,head=3))
    preparation=dict(published=0,ring=dict(slots=[],count=0,head=0,capacity=0))
    coordination=dict(active=0,word=0,limit=0)
    worker=dict(pending=pending,published=4,semaphore=0xffffffff)
    cleanup_receipts=[];steps=[]
    def lock(name):
        depths[name]=depths.get(name,0)+1;max_depths[name]=max(max_depths.get(name,0),depths[name]);events.append(['lock',name])
    def unlock(name):
        depths[name]-=1;events.append(['unlock',name])
    def prepare(_):
        prepare_resource_queue(preparation,lock=lambda _:lock('registry_b8'),unlock=lambda _:unlock('registry_b8'),
            dispatch_current=lambda _:events.append(['prepare_dispatch']))
    def consume(reg,out):
        def append(p):out['slots'][out['count']]=p;out['count']+=1
        def cleanup(_,h):
            cleanup_receipts.append(cleanup_holder(h,release_payload_token=lambda _:events.append(['release_token']),
                remove_token=lambda _:events.append(['remove_token']),locate_pool=lambda x:locate_holder_pool(x['address'],[pool])))
        def step(r):
            steps.append(consume_holder_step(r,payload_virtual48=lambda _:events.append(['virtual48']),
                dispatch_payload=lambda _:events.append(['dispatch']),append_output=append,cleanup_holder=cleanup))
        run_holder_consumer(reg,coordination,worker,lock=lock,unlock=unlock,process_one=step,signal=lambda:events.append(['signal']))
    def lookup(p):events.append(['lookup',p['name']]);return 'allocation-info'
    result=run_retirement_service(registry,lock=lock,unlock=unlock,prepare=prepare,consume=consume,
        allocation_lookup=lookup,destroy_payload=lambda p,arg:events.append(['destroy',p['name'],arg]),
        free_storage=lambda p,info:events.append(['free',p['name'],info]))
    return dict(evidence='Joined serial models with synthetic objects, locks and leaf services',events=events,
        service=result,steps=steps,cleanup=cleanup_receipts,worker=worker,coordination=coordination,
        processing=registry['processing'],remaining_queue_count=registry['ring']['count'],
        holder_status=holder['status'],holder_count_or_link=holder['count'],pool_head=pool['head'],
        payload_detached=holder['payload'] is None,payload_flags=payload['flags'],
        lock_depths=depths,max_lock_depths=max_depths,native_completion_proved=False)


if __name__=='__main__':
    print(json.dumps({name:run_probe(**args) for name,args in
        [('mode_one',{}),('mode_zero',{'mode':0}),('retained',{'references':1}),('reentrant',{'processing':1})]},indent=2))
