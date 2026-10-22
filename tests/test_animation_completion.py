import unittest
from reference.animation_completion import complete_pending_groups


def descriptor(kind, marker=0, offset=0):
    return dict(kind=kind, marker=marker, provider_offset=offset)


class CompletionTests(unittest.TestCase):
    def test_flag_groups_and_reload_after_ready(self):
        records = [descriptor(0), descriptor(0x18), descriptor(7),
                   descriptor(8,65535,8), descriptor(0)]
        first = dict(flags=0xa5, descriptors=records, providers={0:'a',8:'b'})
        second = dict(flags=0, descriptors=[], providers={8:'c'})
        output = {'pending':first}; events=[]
        def ready(provider, pending):
            self.assertEqual(first['flags'],0xa4)
            events.append(('ready',provider))
            if provider=='a':output['pending']=second
            return 1
        def complete(provider,out,pending,descriptors,start,end):
            self.assertIs(out,output); self.assertIs(pending,second)
            self.assertIs(descriptors,records)
            events.append(('complete',provider,start,end))
        self.assertEqual(complete_pending_groups(output,ready=ready,complete=complete),2)
        self.assertEqual(events,[('ready','a'),('complete','a',1,3),
                                 ('ready','c'),('complete','c',3,5)])
        self.assertEqual(complete_pending_groups(output,ready=ready,complete=complete),0)

    def test_missing_and_declined_providers_skip_whole_group(self):
        for provider,status in ((None,1),('p',0),('p',256)):
            state=dict(flags=1,descriptors=[descriptor(8),descriptor(8,0,8)],
                       providers={0:provider})
            events=[]
            count=complete_pending_groups({'pending':state},
                ready=lambda *args:(events.append('ready') or status),
                complete=lambda *args:self.fail('must not complete'))
            self.assertEqual(count,0);self.assertEqual(state['flags'],0)
            self.assertEqual(events,[] if provider is None else ['ready'])

    def test_exception_does_not_rearm_flag(self):
        state=dict(flags=1,descriptors=[descriptor(8)],providers={0:'p'})
        def fail(*args):raise RuntimeError('service failure')
        with self.assertRaises(RuntimeError):
            complete_pending_groups({'pending':state},ready=fail,complete=fail)
        self.assertEqual(state['flags'],0)

    def test_instruction_receipt(self):
        import json
        from pathlib import Path
        receipt=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/animation_completion_validation.json').read_text())
        self.assertEqual(receipt['cases'],96)
        for row in receipt['rows']:
            events=[]
            provider='p' if row['provider_present'] else None
            pending=dict(flags=row['flags'],descriptors=row['descriptors'],
                         providers={0:provider,8:provider})
            count=complete_pending_groups({'pending':pending},
                ready=lambda *args:(events.append(['ready']) or row['status']),
                complete=lambda p,o,s,r,a,b:events.append(['complete',a,b]))
            self.assertEqual(count,row['dispatches'])
            self.assertEqual(events,row['events'])
            self.assertEqual(pending['flags'],row['final_flags'])
