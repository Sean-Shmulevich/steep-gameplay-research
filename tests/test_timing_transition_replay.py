import copy
import struct
import unittest
from engine.scheduler import schedule
from engine.timing_transition_replay import replay_timing_transition

def observation(state):
    h=state['history']
    return dict(owner=1,physics_manager=2,world=3,history_pointer=4,policy=0,
        smoothing_enabled=True,history_capacity=h['capacity'],history_count=h['count'],
        history_write=h['write'],history_oldest=h['oldest'],
        history_bits=[struct.unpack('<I',struct.pack('<f',x))[0] for x in h['values']],
        retained=state['retained'],consumed=state['last_consumed'],
        inverse_consumed=state['inverse_consumed_dt'],frequency=state['selected_frequency'],
        step_count=state['last_count'],elapsed=state['last_elapsed'])

class TimingReplayTests(unittest.TestCase):
    def pair(self):
        state={};config=dict(mode='subdivision',smoothing_enabled=True,policy=0,history_capacity=3)
        for dt in (.01,.02,.03):schedule(state,dt,config)
        before=observation(state);schedule(state,.12,config)
        return before,observation(state),state,config

    def test_single_append_reproduces_cap(self):
        b,a,_,_=self.pair();r=replay_timing_transition(b,a)
        self.assertTrue(r['matches']);self.assertFalse(r['producer_call_count_proved'])

    def test_multiple_appends_rejected_despite_equal_capped_outputs(self):
        b,a,state,config=self.pair();schedule(state,.13,config);after=observation(state)
        self.assertEqual(a['consumed'],after['consumed'])
        self.assertEqual(replay_timing_transition(b,after)['status'],'not_single_append')

    def test_unwritten_history_change_and_configuration_change(self):
        b,a,_,_=self.pair();bad=copy.deepcopy(a);bad['history_bits'][1]^=1
        self.assertEqual(replay_timing_transition(b,bad)['status'],'not_single_append')
        bad=copy.deepcopy(a);bad['policy']=1
        self.assertEqual(replay_timing_transition(b,bad)['status'],'configuration_changed')

    def test_output_mismatch_is_not_hidden_by_matching_ring(self):
        b,a,_,_=self.pair();a['frequency']+=1
        self.assertEqual(replay_timing_transition(b,a)['mismatched_fields'],['frequency'])
