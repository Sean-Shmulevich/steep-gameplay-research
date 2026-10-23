import unittest
from engine.holder_retirement_service import run_retirement_service


class RetirementServiceTests(unittest.TestCase):
    def run_case(self,mode=1):
        r={'mode':mode};events=[]
        def consume(_,out):out.update(slots=['a',None,'b'],storage='array',count=3,flags=1<<30)
        def destroy(p,arg):
            self.assertEqual(arg,0);events.append(('destroy',p));r['mode']=2
        result=run_retirement_service(r,lock=lambda x:events.append(('lock',x)),
            unlock=lambda x:events.append(('unlock',x)),prepare=lambda _:events.append(('prepare',)),
            consume=consume,allocation_lookup=lambda p:events.append(('lookup',p)) or ('info',p),
            destroy_payload=destroy,free_storage=lambda p,info:events.append(('free',p,info)))
        return result,events

    def test_mode_is_checked_once_and_all_unlocks_precede_destructors(self):
        r,e=self.run_case()
        self.assertEqual(r,dict(payloads_destroyed=2,output_storage_freed=True))
        self.assertEqual([x for x in e if x[0]=='destroy'],[('destroy','a'),('destroy','b')])
        self.assertLess(max(i for i,x in enumerate(e) if x[0]=='unlock'),next(i for i,x in enumerate(e) if x[0]=='destroy'))
        self.assertEqual(e[-2:],[('lookup','array'),('free','array',('info','array'))])

    def test_other_modes_still_release_owned_output_storage(self):
        for mode in (0,2):
            r,e=self.run_case(mode)
            self.assertEqual(r,dict(payloads_destroyed=0,output_storage_freed=True))
            self.assertFalse(any(x[0]=='destroy' for x in e))
