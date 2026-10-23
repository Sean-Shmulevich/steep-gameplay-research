"""Joined retirement-to-loading path with synthetic resources and leaf services.

The authored driver invokes loading after retirement returns. This is one serial
schedule, not a recovered global scheduler order or an unload barrier."""
import json
from engine.holder_retirement_service import run_retirement_service
from engine.resource_preparation_queue import prepare_resource_queue
from engine.holder_consumer_scope import run_holder_consumer
from engine.holder_consumer_step import consume_holder_step
from engine.holder_cleanup import cleanup_holder
from engine.holder_pool_lookup import locate_holder_pool
from engine.loading_destruction_enqueue import enqueue_loading_destruction
from engine.loading_destruction_batch import process_loading_destructions
from engine.allocation_metadata_lookup import lookup_allocation_metadata


class WorkerView:
    """Alias older consumer field names to the loading owner's actual words."""
    keys = dict(pending='staged', published='pending', semaphore='semaphore')

    def __init__(self, owner):
        self.owner = owner

    def __getitem__(self, key):
        return self.owner[self.keys[key]]

    def __setitem__(self, key, value):
        self.owner[self.keys[key]] = value


def run_probe(*, mode=0, references=0, processing=0, capacity=4):
    events=[];depths={};max_depths={}
    payload=dict(name='payload',flags=0x7ffff)
    holder=dict(address=0x300200,status=(1<<24)|references,count=0,payload=payload,token=0xf0000000)
    pool=dict(base=holder['address'],capacity=1,head=19)
    registry=dict(mode=mode,processing=processing,ring=dict(slots=[None,None,None,holder],count=1,capacity=4,head=3))
    preparation=dict(published=0,ring=dict(slots=[],count=0,head=0,capacity=0))
    coordination=dict(active=0,word=0,limit=0)
    loading=dict(staged=0,pending=0,busy=0,semaphore=0xffffffff,
                 ring=dict(slots=[None]*capacity,count=0,head=0,tail=0,capacity=capacity))
    worker=WorkerView(loading)
    insertions=[]
    cleanup_receipts=[];steps=[]
    def lock(name):
        depths[name]=depths.get(name,0)+1;max_depths[name]=max(max_depths.get(name,0),depths[name]);events.append(['lock',name])
    def unlock(name):
        depths[name]-=1;events.append(['unlock',name])
    def dispatch(p):
        events.append(['dispatch'])
        insertions.append(enqueue_loading_destruction(loading,p,
            lock=lambda _:lock('global_1d8'),unlock=lambda _:unlock('global_1d8'),
            grow=lambda *_:events.append(['growth_refused'])))
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
                dispatch_payload=dispatch,append_output=append,cleanup_holder=cleanup))
        run_holder_consumer(reg,coordination,worker,lock=lock,unlock=unlock,process_one=step,signal=lambda:events.append(['signal']))
    def lookup(p):
        events.append(['lookup',p['name']])
        # Synthetic address and populated region, independent of Python identity.
        return lookup_allocation_metadata(0x300300,
            read_region=lambda _:bytes(65536),read_entry=lambda _:'allocation-info',
            default_index=lambda:0)
    result=run_retirement_service(registry,lock=lock,unlock=unlock,prepare=prepare,consume=consume,
        allocation_lookup=lookup,destroy_payload=lambda p,arg:events.append(['destroy',p['name'],arg]),
        free_storage=lambda p,info:events.append(['free',p['name'],info]))
    before_batch=dict(staged=loading['staged'],pending=loading['pending'],
                      count=loading['ring']['count'],detached=holder['payload'] is None,
                      destruction_calls=sum(e[0]=='destroy' for e in events))
    events.append(['batch_start'])
    batch=process_loading_destructions(loading,
        lock=lambda _:lock('global_1d8'),unlock=lambda _:unlock('global_1d8'),
        allocation_lookup=lookup,destroy_payload=lambda p,arg:events.append(['destroy',p['name'],arg]),
        free_storage=lambda p,info:events.append(['free',p['name'],info]))
    return dict(before_batch=before_batch,batch=batch,insertions=insertions,
        loading=dict(staged=loading['staged'],pending=loading['pending'],busy=loading['busy'],
                     count=loading['ring']['count'],head=loading['ring']['head']),
        evidence='Joined serial models with synthetic objects, locks and leaf services',events=events,
        service=result,steps=steps,cleanup=cleanup_receipts,worker={k:worker[k] for k in WorkerView.keys},coordination=coordination,
        processing=registry['processing'],remaining_queue_count=registry['ring']['count'],
        holder_status=holder['status'],holder_count_or_link=holder['count'],pool_head=pool['head'],
        payload_detached=holder['payload'] is None,payload_flags=payload['flags'],
        lock_depths=depths,max_lock_depths=max_depths,native_completion_proved=False)


if __name__=='__main__':
    print(json.dumps({name:run_probe(**args) for name,args in
        [('mode_zero',{}),('mode_one',{'mode':1}),('refused_growth',{'capacity':0}),('retained',{'references':1}),('reentrant',{'processing':1})]},indent=2))
