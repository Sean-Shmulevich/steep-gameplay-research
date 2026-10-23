"""Synthetic command-copy ownership experiment, not native command admission."""
import json
from engine.command_record_copy import copy_record
from engine.command_record_cleanup import cleanup_record


def run_probe(*, copies=2):
    holder=dict(status=100)
    associated=dict(count=1)
    source=dict(kind=3,holder_08=holder,holder_10=holder,
        payload_18_30=bytes(24),invoker='not-executed',payload_38_60=bytes(40),
        associated=associated)
    queued=[];events=[];samples=[]
    def sample(stage):samples.append(dict(stage=stage,references=associated['count']))
    def cleanup(record):
        cleanup_record(record,destroy_associated=lambda _:events.append('associated_destroy'),
                       release_holder=lambda _:events.append('holder_release'))
    sample('source_owned')
    for _ in range(copies):queued.append(copy_record({},source))
    sample('copies_owned')
    cleanup(source);sample('source_cleaned')
    for i,record in enumerate(queued):
        cleanup(record);sample('copy_'+str(i)+'_discarded')
    return dict(evidence='Synthetic serial composition, retained objects and supplied destruction',
        samples=samples,events=events,callback_invocations=0,native_admission_proved=False,
        manager_lifetime_proved=False,module_lifetime_proved=False)


if __name__=='__main__':
    print(json.dumps(run_probe(),indent=2))
