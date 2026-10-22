import unittest
from reference.animation_pending_copy import copy_pending_state
from reference.animation_completion import complete_pending_groups


class PendingCopyTests(unittest.TestCase):
    def test_copy_rearms_destination_then_completion_consumes(self):
        descriptors=[dict(kind=8,marker=0,provider_offset=0)]
        source=dict(flags=3,providers={0:'provider'},auxiliary=[7],word=12)
        destination=dict(flags=0xa4,providers={},auxiliary=[],word=0,
                         descriptors=descriptors,owner='owner',references=5)
        events=[]
        def copy_vector(dst,src,field):
            events.append(field);dst[field]=src[field].copy()
        copy_pending_state(destination,source,copy_vector=copy_vector)
        self.assertEqual(events,['providers','auxiliary'])
        self.assertEqual(destination['flags'],0xa5)
        self.assertEqual((destination['owner'],destination['references']),('owner',5))
        self.assertEqual(destination['word'],12)
        self.assertEqual(complete_pending_groups({'pending':destination},
            ready=lambda *args:1,complete=lambda *args:events.append('complete')),1)
        self.assertEqual(destination['flags'],0xa4)
        self.assertEqual(source['flags'],3)
        self.assertEqual(events,['providers','auxiliary','complete'])

    def test_alias_skips_vector_services(self):
        state=dict(flags=255,word=9)
        copy_pending_state(state,state,copy_vector=lambda *args:self.fail('alias copy'))
        self.assertEqual(state,dict(flags=255,word=9))

    def test_scalar_read_order(self):
        source=dict(flags=0,word=1);destination=dict(flags=0xaa,word=0)
        def copy_vector(dst,src,field):
            if field=='providers':src['flags']=1
            else:src['flags']=0;src['word']=42
        copy_pending_state(destination,source,copy_vector=copy_vector)
        self.assertEqual(destination,dict(flags=0xab,word=42))

    def test_instruction_receipt(self):
        import json
        from pathlib import Path
        data=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/pending_copy_validation.json').read_text())
        self.assertEqual(data['cases'],32)
        for row in data['rows']:
            source=dict(flags=row['source_flags'],word=row['word'])
            destination=source if row['alias'] else dict(flags=row['destination_flags'],word=0)
            events=[]
            copy_pending_state(destination,source,copy_vector=lambda d,s,f:events.append(f))
            self.assertEqual(events,row['events'])
            self.assertEqual(destination['flags'],row['final_flags'])
            self.assertEqual(destination['word'],row['word'])
