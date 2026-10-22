import unittest
from engine.action_axis_ramp import AxisRampState
from engine.action_response import directional_response

class DirectionalResponseTests(unittest.TestCase):
    def test_press_release_reverse_and_gates(self):
        state=(AxisRampState(1,1,0),)*2;clock=0
        outputs=[]
        for ticks,values in ((50,(1,1,0,0)),(100,(0,0,0,0)),(150,(-1,0,0,0))):
            r=directional_response(values,state,previous_clock=clock,duration=.2,
                                   axis_mode=0,start_ticks=ticks,end_ticks=ticks,curve=lambda x:x)
            state,clock=r['states'],r['clock'];outputs.append(r['output'])
        self.assertGreater(outputs[0][0],0)
        self.assertEqual(outputs[1][0],0)
        self.assertLess(outputs[2][0],0)
        r=directional_response((1,1,2,3),state,previous_clock=clock,duration=.2,
                               axis_mode=0,start_ticks=200,end_ticks=200,curve=lambda x:x,
                               ramp_enabled=False,diagonal_enabled=True)
        self.assertEqual(r['states'],state);self.assertEqual(r['clock'],clock)
        self.assertFalse(r['stages'][0].invoked)
        self.assertLess(r['output'][0],1);self.assertEqual(r['output'][2:],(2,3))

    def test_source_publication_uses_processed_sample(self):
        from engine.action_response import directional_action_response
        queries=dict(negative_x=(False,False),positive_x=(True,False),
                     positive_y=(False,True),negative_y=(False,False))
        r=directional_action_response(queries,states=(AxisRampState(1,1,0),)*2,
             previous_clock=0,duration=.2,axis_mode=0,start_ticks=50,end_ticks=50,
             curve=lambda x:x)
        self.assertEqual(r['raw_vector'],[1,1,0,0])
        self.assertEqual(r['publication']['sampled_vector'],list(r['response']['output']))
        self.assertTrue(r['publication']['status'])
        self.assertAlmostEqual(r['publication']['magnitude'],.25,places=6)
        self.assertIn('derived',r['publication']['normalization_policy'])
