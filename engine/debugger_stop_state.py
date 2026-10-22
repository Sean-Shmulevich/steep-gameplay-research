"""Authored observer policy for stale asynchronous debugger state reports.

This is tooling policy, not recovered engine behavior. A stopped report from
before an attempted resume cannot authorize further memory reads or cleanup.
"""


class ResumeTransition:
    def __init__(self):
        self.resume_stop_id = None

    def attempted_resume(self, stop_id):
        if type(stop_id) is not int or stop_id < 0:
            raise ValueError('nonnegative stop ID required')
        self.resume_stop_id = stop_id

    def confirmed_stopped(self, *, stopped, stop_id):
        if not stopped:
            return False
        return self.resume_stop_id is None or stop_id > self.resume_stop_id
