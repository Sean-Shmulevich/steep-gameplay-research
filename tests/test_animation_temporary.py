import unittest
from reference.animation_temporary import assign_binding, prepare_temporary_bank


class TemporaryTests(unittest.TestCase):
    def fixture(self):
        return (dict(bank=None, bank_owner='oldbankowner', owned=False,
                     binding=dict(value='old',owner='oldowner'), pending='preserve'),
                dict(bank_owner='newbankowner',auxiliary_owner='aux',mode=257,
                     binding=dict(value='source',owner='sourceowner'),metadata_base='base'))

    def test_prepare_once_preserves_pending_and_reuses_bank(self):
        temp,ctx=self.fixture();events=[]
        def release(*args):events.append(('release',args))
        def retain(*args):events.append(('retain',args));return 'retained'
        def acquire(*args):events.append(('acquire',args));return 'bank'
        def release_bank(*args):self.fail('no prior bank')
        for _ in range(2):
            self.assertIs(prepare_temporary_bank(temp,ctx,release_binding=release,
                copy_selection_mask=retain,release_bank=release_bank,acquire_bank=acquire),temp)
        self.assertEqual(events,[('release',('oldowner','old')),
            ('retain',('sourceowner','source')),('acquire',('newbankowner','retained',1,0))])
        self.assertEqual(temp['pending'],'preserve');self.assertEqual(temp['metadata'],('base',160))
        self.assertTrue(temp['owned'])

    def test_null_bank_retries_and_releases_previous_binding(self):
        temp,ctx=self.fixture();events=[]
        for _ in range(2):
            prepare_temporary_bank(temp,ctx,release_binding=lambda o,v:events.append(v),
                copy_selection_mask=lambda o,v:'retained',release_bank=lambda *a:None,
                acquire_bank=lambda *a:None)
        self.assertEqual(events,['old','retained']);self.assertIsNone(temp['bank'])
        self.assertEqual(temp['metadata'],('base',160))

    def test_binding_alias_is_not_retain(self):
        binding=dict(value='old',owner='owner');events=[]
        assign_binding(binding,binding,release=lambda *a:events.append(a),
                       copy_selection_mask=lambda *a:self.fail('self assignment clears source'))
        self.assertEqual(events,[('owner','old')])
        self.assertEqual(binding,dict(value=None,owner=None))

    def test_instruction_receipt(self):
        import json
        from pathlib import Path
        data=json.loads((Path(__file__).resolve().parents[1]/
            'native/snow_host/animation_temporary_validation.json').read_text())
        self.assertEqual(data['cases'],64)
        for row in data['rows']:
            temp,ctx=self.fixture();events=[]
            temp['bank']='existing' if row['existing_bank'] else None
            temp['binding']['value']='old' if row['old_binding'] else None
            ctx['binding']['value']='source' if row['source_binding'] else None
            ctx['mode']=row['mode']
            def release(*a):events.append('release')
            def retain(*a):events.append('retain');return 'retained'
            def acquire(owner,binding,mode,option):
                self.assertEqual((mode,option),(row['mode'],0))
                self.assertEqual(binding,'retained' if row['source_binding'] else None)
                events.append('acquire');return 'new' if row['allocation_succeeds'] else None
            prepare_temporary_bank(temp,ctx,release_binding=release,copy_selection_mask=retain,
                                   release_bank=lambda *a:self.fail('unexpected bank release'),
                                   acquire_bank=acquire)
            self.assertEqual(events,row['services'])
            self.assertEqual(temp['pending'],'preserve')
            self.assertEqual(temp['bank'],'existing' if row['existing_bank'] else
                             'new' if row['allocation_succeeds'] else None)
