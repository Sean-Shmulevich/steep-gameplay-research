import unittest
from engine.command_related_selection import select_related


class RelatedSelectionTests(unittest.TestCase):
    def test_owner_filter_unsigned_max_and_inclusive_level(self):
        entries=[dict(owner='a',priority=0x80000000,flagged=1,level=0x80000000),
                 dict(owner='a',priority=0xffffffff,flagged=0,level=0x7fffffff),
                 dict(owner='b',priority=0xffffffff,flagged=1,level=0xffffffff)]
        seen=[]
        result=select_related(entries,'a',resolve=lambda e:dict(owner_key=e['owner'],level=e['level']),handle=seen.append)
        self.assertEqual((result['threshold'],seen),(0x80000000,[entries[0]]))

    def test_duplicate_entries_remain_and_zero_default(self):
        entry=dict(priority=9,flagged=0)
        seen=[]
        result=select_related([entry,entry],1,resolve=lambda e:dict(owner_key=1,level=0),handle=seen.append)
        self.assertEqual((result['threshold'],len(seen)),(0,2))

    def test_second_pass_resolves_again_without_owner_recheck(self):
        entry=dict(priority=5,flagged=255)
        resolutions=iter([dict(owner_key=1,level=0),dict(owner_key=2,level=5)])
        seen=[]
        select_related([entry],1,resolve=lambda e:next(resolutions),handle=seen.append)
        self.assertEqual(seen,[entry])

    def test_empty_collection_invokes_nothing(self):
        result=select_related([],1,resolve=lambda e:self.fail(),handle=lambda e:self.fail())
        self.assertEqual((result['selected'],result['handled'],result['threshold']),([],[],0))


if __name__ == '__main__':unittest.main()
