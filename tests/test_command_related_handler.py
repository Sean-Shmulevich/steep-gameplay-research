import unittest
from engine.command_related_handler import replace_related_reference, admit_pooled_request


class RelatedHandlerTests(unittest.TestCase):
    def test_exchange_visible_to_old_release_and_failed_submit_keeps_reference(self):
        entry=dict(source='new',retained='old')
        holders={'new':dict(status=5,payload=12),'old':dict(status=0x80000001,payload=13)}
        seen=[]
        result=replace_related_reference(entry,holders,release=lambda key:seen.append((key,entry['retained'],holders['new']['status'])),submit=lambda value:False)
        self.assertEqual(seen,[('old','new',7)])
        self.assertEqual((holders['new']['status'],holders['old']['status']),(6,0x80000000))
        self.assertFalse(result['submission_result'])
        self.assertEqual(entry['retained'],'new')

    def test_alias_is_balanced(self):
        entry=dict(source='same',retained='same');holders={'same':dict(status=8,payload=None)}
        replace_related_reference(entry,holders,release=lambda x:self.fail(),submit=lambda x:True)
        self.assertEqual(holders['same']['status'],8)

    def test_source_is_reloaded_after_release_callback(self):
        entry=dict(source='new',retained='old')
        holders={key:dict(status=value,payload=key) for key,value in [('new',5),('old',1),('other',9)]}
        seen=[]
        replace_related_reference(entry,holders,release=lambda key:entry.update(source='other'),submit=seen.append)
        self.assertEqual(seen,['other'])
        self.assertEqual(entry['retained'],'new')

    def test_pool_empty_null_and_success(self):
        for count,record,expected in [(0,'x',False),(1,None,False),(1,'x',True)]:
            pool=dict(count=count,slots=['unused',record],read_index=1,capacity=2,available_total=3)
            calls=[]
            result=admit_pooled_request(pool,initialize=lambda r:calls.append(('init',r)),publish=lambda r:calls.append(('publish',r)))
            self.assertEqual(result,expected)
            self.assertEqual(calls,[('init','x'),('publish','x')] if expected else [])
            self.assertEqual((pool['count'],pool['read_index'],pool['available_total']),(0,0,2) if count else (0,1,3))

    def test_publication_failure_does_not_restore_consumed_slot(self):
        pool=dict(count=1,slots=['x'],read_index=0,capacity=1,available_total=1)
        def fail(record):raise RuntimeError('supplied publisher failed')
        with self.assertRaises(RuntimeError):admit_pooled_request(pool,initialize=lambda r:None,publish=fail)
        self.assertEqual((pool['count'],pool['available_total']),(0,0))


if __name__ == '__main__':unittest.main()
