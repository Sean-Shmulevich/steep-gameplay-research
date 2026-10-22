import unittest
from reference.animation_temporary import prepare_temporary_bank, cleanup_temporary_bank


class TemporaryCleanupTests(unittest.TestCase):
    def test_prepare_release_and_second_cleanup(self):
        pending=dict(references=1,owner='pool')
        temporary=dict(bank=None,bank_owner=None,owned=False,
                       binding=dict(value=None,owner=None),pending=pending)
        context=dict(bank_owner='bankpool',auxiliary_owner='aux',mode=2,
                     binding=dict(value='source',owner='bindingpool'),metadata_base='base')
        events=[]
        prepare_temporary_bank(temporary,context,release_binding=lambda *a:self.fail(),
            copy_selection_mask=lambda *a:'binding',release_bank=lambda *a:self.fail(),
            acquire_bank=lambda *a:'bank')
        def recycle(owner,obj):
            self.assertIs(obj,pending);self.assertEqual(obj['references'],0)
            self.assertIs(temporary['pending'],pending)
            events.append(('recycle',owner))
        for _ in range(2):
            cleanup_temporary_bank(temporary,recycle_pending=recycle,
                release_binding=lambda *a:events.append(('binding',*a)),
                release_bank=lambda *a:events.append(('bank',*a)))
        self.assertEqual(events,[('recycle','pool'),('binding','bindingpool','binding'),
                                 ('bank','bankpool','bank')])
        self.assertIsNone(temporary['pending']);self.assertIsNone(temporary['bank'])
        self.assertFalse(temporary['owned']);self.assertEqual(temporary['metadata'],('base',160))

    def test_shared_pending_and_unowned_bank(self):
        for references,expected in ((2,1),(0,0xffffffff)):
            pending=dict(references=references,owner='pool')
            state=dict(pending=pending,binding=dict(value=None,owner='owner'),
                       bank='borrowed',owned=False,bank_owner='bankowner')
            def forbidden(*a):self.fail('no releases expected')
            cleanup_temporary_bank(state,recycle_pending=forbidden,
                release_binding=forbidden,release_bank=forbidden)
            self.assertEqual(pending['references'],expected)
            self.assertIsNone(state['bank']);self.assertIsNone(state['binding']['owner'])

    def test_instruction_receipt(self):
        import json
        from pathlib import Path
        data=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/temporary_cleanup_validation.json').read_text())
        self.assertEqual(data['cases'],48)
        for row in data['rows']:
            pending=dict(owner='pool',references=row['references'])
            state=dict(pending=pending if row['pending'] else None,
                       binding=dict(value='binding' if row['binding'] else None,owner='pool'),
                       bank='bank' if row['bank'] else None,owned=row['owned'],bank_owner='pool')
            events=[]
            cleanup_temporary_bank(state,recycle_pending=lambda *a:events.append('recycle'),
                release_binding=lambda *a:events.append('binding'),
                release_bank=lambda *a:events.append('bank'))
            self.assertEqual(events,row['services'])
            self.assertEqual(pending['references'],row['final_references'])

    def test_flat_conversion_uses_one_temporary_bank(self):
        import struct
        from reference.animation_flat_conversion import convert_flat_results
        context=dict(bank_owner='pool',auxiliary_owner='aux',mode=0,
                     binding=dict(value='source',owner='pool'),metadata_base='base')
        events=[]
        def prepare(temporary,ctx):
            if temporary is None:
                temporary=dict(bank=None,owned=False,bank_owner=None,pending=None,
                               binding=dict(value=None,owner=None))
            return prepare_temporary_bank(temporary,ctx,
                release_binding=lambda *a:events.append('release binding'),
                copy_selection_mask=lambda *a:(events.append('retain') or 'binding'),
                release_bank=lambda *a:events.append('release bank'),
                acquire_bank=lambda *a:(events.append('acquire') or 'temporary bank'))
        def cleanup(temporary):
            if temporary is not None:
                cleanup_temporary_bank(temporary,recycle_pending=lambda *a:self.fail(),
                    release_binding=lambda *a:events.append('release binding'),
                    release_bank=lambda *a:events.append('release bank'))
        records=[struct.pack('<QQfHBB',i,99,w,1,0,0) for i,w in enumerate((.25,.25,.5))]
        result=convert_flat_results(records,1,context,{},publish_token=lambda *a:None,
            evaluate=lambda *a:events.append('evaluate'),prepare_temporary=prepare,
            blend=lambda o,t,w:events.append(('blend',w)),cleanup=cleanup)
        self.assertTrue(result['success'])
        self.assertEqual(events,['evaluate','retain','acquire','evaluate',('blend',.5),
                                 'evaluate',('blend',.5),'release binding','release bank'])
