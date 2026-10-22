import unittest
from engine.debugger_stop_state import ResumeTransition


class ResumeTransitionTests(unittest.TestCase):
    def test_stale_stop_never_authorizes_cleanup(self):
        state=ResumeTransition()
        self.assertTrue(state.confirmed_stopped(stopped=True,stop_id=1))
        state.attempted_resume(1)
        for stopped,stop_id in ((True,1),(False,1),(True,0),(False,2)):
            self.assertFalse(state.confirmed_stopped(stopped=stopped,stop_id=stop_id))
        self.assertTrue(state.confirmed_stopped(stopped=True,stop_id=2))

    def test_each_resume_invalidates_its_stop_even_without_running_report(self):
        state=ResumeTransition()
        for stop in range(1,5):
            self.assertTrue(state.confirmed_stopped(stopped=True,stop_id=stop))
            state.attempted_resume(stop)
            self.assertFalse(state.confirmed_stopped(stopped=True,stop_id=stop))

    def test_invalid_stop_id(self):
        for value in (-1,True,None):
            with self.assertRaises(ValueError):ResumeTransition().attempted_resume(value)
