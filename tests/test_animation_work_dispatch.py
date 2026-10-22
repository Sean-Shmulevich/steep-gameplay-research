import json
from pathlib import Path
import unittest
from reference.animation_work_dispatch import dispatch_pose_work


class DispatchTests(unittest.TestCase):
    def test_instruction_receipt(self):
        receipt=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/pose_work_dispatch_validation.json').read_text())
        self.assertEqual(receipt['cases'],32)
        for row in receipt['rows']:
            state=dict(owner=dict(name='first',context='context') if row['owner_present'] else None)
            packet=dict(input=11,output=22,time_bits=row['time_bits']);events=[]
            def prepare(context,bits):
                self.assertEqual(context,'context');events.append(['prepare',bits])
                if row['replace_after_prepare']:
                    state['owner']=dict(name='second');packet.update(input=33,output=44,time_bits=row['replacement_time_bits'])
            def evaluate(owner,i,o,t,e):
                events.append(['evaluate',owner['name'],i,o,t,e]);return row['evaluator_result']
            result=dispatch_pose_work(state,packet,row['extra_work'],prepare=prepare,evaluate=evaluate)
            self.assertEqual(result,row['result']);self.assertEqual(events,row['events'])

    def test_absent_owner_does_not_read_packet(self):
        def unexpected(*args):self.fail('unexpected service')
        self.assertEqual(dispatch_pose_work(dict(owner=None),{},0,prepare=unexpected,evaluate=unexpected),0)

    def test_original_output_gate_slices(self):
        from reference.animation_work_dispatch import pose_output_route
        receipt=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/pose_output_gates_validation.json').read_text())
        self.assertEqual(receipt['cases'],90)
        for row in receipt['rows']:
            self.assertEqual(pose_output_route(row['extra_work'],row['owner_present'],row['skip_result'],row['result_header']),row['route'])

    def test_encoded_flags_are_not_result_count(self):
        from reference.animation_work_dispatch import pose_output_route
        self.assertEqual(pose_output_route(1,True,0,0xe0000001),'insufficient_results')
        self.assertEqual(pose_output_route(1,True,0,0xe0000002),'publish_output')
