"""Synthetic serial consumption -> cleanup -> pool lookup demonstration."""
import json
from engine.holder_consumer_step import consume_holder_step
from engine.holder_cleanup import cleanup_holder
from engine.holder_pool_lookup import locate_holder_pool


def run_probe(*, initial_status=1<<24, holder_count=0, payload_present=True,
              initial_mode=0, callback_mode=1, callback_references=0):
    payload=dict(flags=0x7ffff,name='payload')
    holder=dict(status=initial_status,count=holder_count,payload=payload if payload_present else None,
                address=0x300200,token=0xf0000000)
    pool=dict(base=0x300200,capacity=1,head=19)
    registry=dict(mode=initial_mode,ring=dict(slots=[None,None,None,holder],capacity=4,count=1,head=3))
    events=[];cleanup_result=None
    def virtual(p):
        events.append('payload_virtual48');registry['mode']=callback_mode
        holder['status']=(holder['status']&~0xffffff)|callback_references
    def cleanup(_,h):
        nonlocal cleanup_result
        events.append('cleanup_requested')
        cleanup_result=cleanup_holder(h,
            release_payload_token=lambda _:events.append('release_payload_token'),
            remove_token=lambda _:events.append('remove_token'),
            locate_pool=lambda x:locate_holder_pool(x['address'],[pool]))
    step=consume_holder_step(registry,payload_virtual48=virtual,
        dispatch_payload=lambda _:events.append('dispatch_payload'),
        append_output=lambda _:events.append('append_output'),cleanup_holder=cleanup)
    return dict(evidence='Serial recovered composition with synthetic objects and supplied payload services',
        step=step,cleanup=cleanup_result,events=events,remaining_queue_count=registry['ring']['count'],
        holder_status=holder['status'],holder_count_or_link=holder['count'],
        payload_detached=holder['payload'] is None,payload_flags=payload['flags'],pool_head=pool['head'],
        disposal_completion_proved=False)


if __name__=='__main__':
    print(json.dumps({'recycled':run_probe(),'reacquired':run_probe(callback_references=1),
                      'separate_count_retained':run_probe(holder_count=1)},indent=2))
