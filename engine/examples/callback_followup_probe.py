"""Synthetic queue and related-record follow-up, keeping completion separate."""
import json
import struct
from engine.callback_commands import submit_callback, drain_counted_callbacks
from engine.command_related_selection import select_related
from engine.command_counter_transfer import replay_counter_transfers


def run():
    queue=[];invoked=[]
    receipt=submit_callback(queue,struct.pack('<4Q',1,0,0x1000,0x2000),capacity=1,deferred=0)
    entries=[dict(identity='low',owner_key='owner',priority=5,flagged=1,level=4),
             dict(identity='equal',owner_key='owner',priority=2,flagged=1,level=5)]
    handled=[]
    selection=select_related(entries,'owner',resolve=lambda e:e,handle=lambda e:handled.append(e['identity']))
    after_followup=dict(queued=len(queue),callback_invocations=len(invoked),related_handlers=handled)
    transfer=replay_counter_transfers({'A':[0,receipt['deferred']],'B':[0,0]},
                                     [('exchange','A',None),('add','A',None)])
    drain_counted_callbacks(queue,active=transfer['counters']['A'][0],
                            dispatch=lambda descriptor:invoked.append(struct.unpack_from('<Q',descriptor)[0]))
    return dict(evidence='authored composition of recovered local policies with synthetic objects',
                threshold=selection['threshold'],after_followup=after_followup,
                invocations_after_later_drain=invoked,native_lifetime_proved=False)


if __name__ == '__main__':print(json.dumps(run(),indent=2))
