import unittest
from engine.action_clock_selection import select_ramp_clock

class ClockSelectionTests(unittest.TestCase):
    def run_selection(self, **kw):
        values=dict(manager_present=True,context_present=False,context_index=-1,
                    override=(90,True),candidates=((10,False),(20,True),(30,True)),
                    fallback=40,excluded=(120,),identity=lambda obj:obj+100)
        values.update(kw)
        return select_ramp_clock(**values)
    def test_override_and_manager_gate(self):
        self.assertEqual(self.run_selection(context_present=True,context_index=0),90)
        self.assertEqual(self.run_selection(context_present=True,context_index=0,manager_present=False),0)
        self.assertEqual(self.run_selection(context_present=True,context_index=-1),30)
        self.assertEqual(self.run_selection(context_present=True,context_index=0,override=(90,False)),30)
    def test_exclusion_uses_registry_identity(self):
        self.assertEqual(self.run_selection(excluded=(20,)),20)
        self.assertEqual(self.run_selection(excluded=(120,130)),40)
        self.assertEqual(self.run_selection(excluded=(120,130,140)),0)
    def test_query_order_and_early_exit(self):
        calls=[]
        def identity(obj):calls.append(obj);return obj+100
        self.assertEqual(self.run_selection(identity=identity),30)
        self.assertEqual(calls,[20,30])
        calls.clear()
        self.assertEqual(self.run_selection(identity=identity,candidates=()),40)
        self.assertEqual(calls,[40])
