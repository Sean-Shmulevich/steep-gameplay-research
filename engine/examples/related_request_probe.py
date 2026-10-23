"""Separate retained-reference changes from request admission and completion."""
import json
from engine.command_related_handler import replace_related_reference, admit_pooled_request


def run_case(available):
    entry=dict(source='new',retained='old')
    holders={'new':dict(status=3,payload='resource token'),'old':dict(status=2,payload=None)}
    pool=dict(slots=['work'],count=int(available),read_index=0,capacity=1,available_total=int(available))
    events=[]
    def submit(payload):
        return admit_pooled_request(pool,initialize=lambda work:events.append(['initialize',work,payload]),
                                   publish=lambda work:events.append(['publish',work]))
    result=replace_related_reference(entry,holders,release=lambda key:events.append(['release',key]),submit=submit)
    return dict(pool_initially_available=available,retained=entry['retained'],holders=holders,
                request_accepted=result['submission_result'],events=events,completion_proved=False)


if __name__ == '__main__':
    print(json.dumps(dict(evidence='synthetic state using recovered local ordering',
                         cases=[run_case(False),run_case(True)]),indent=2))
