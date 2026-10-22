import json
from pathlib import Path
import unittest
from reference.animation_pose_blend import blend_regular_pose


class RegularPoseBlendTests(unittest.TestCase):
    def test_original_instruction_receipt(self):
        receipt=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/regular_pose_wrapper_validation.json').read_text())
        self.assertEqual(receipt['cases'],64)
        for row in receipt['rows']:
            with self.subTest(row=row):
                events=[]; output={'flags':5}; first={}; second={}
                destination=dict(primary=None if row['missing_primary'] else output,
                    component=dict(pool='pool',flags16=row['selector']<<3),
                    index=row['destination_mask'],request_byte=row['request_byte'])
                source=dict(index=row['source_mask'])
                def acquire(pool,index,mode):
                    self.assertEqual((pool,index,mode),('pool',row['destination_mask'],row['request_byte']&1))
                    events.append('acquire');return output
                def select(wrapper):
                    events.append('select_source' if wrapper is source else 'select_destination')
                    return second if wrapper is source else first
                def remove(wrapper,bank):
                    self.assertIs(bank,second if wrapper is source else first)
                    events.append('unscale_source' if wrapper is source else 'unscale_destination');return bank
                def blend(dst,a,b,w,selector,mask,*,exclusion_mask):
                    self.assertIs(dst,output);self.assertIs(a,first);self.assertIs(b,second)
                    self.assertEqual((selector,mask,exclusion_mask),(row['selector'],row['source_mask']&row['destination_mask'],0))
                    self.assertAlmostEqual(w,row['weight']);events.append('blend');return 'result'
                self.assertEqual(blend_regular_pose(destination,source,row['weight'],acquire=acquire,
                    select_bank=select,remove_scale=remove,blend_bank=blend),'result')
                self.assertEqual(events,row['events']);self.assertEqual(output['flags'],row['final_flags'])

    def test_failed_blend_does_not_publish_ready(self):
        destination=dict(primary={'flags':5},component=dict(flags16=0),index=0)
        def fail(*args,**kwargs):raise RuntimeError('service failed')
        with self.assertRaises(RuntimeError):
            blend_regular_pose(destination,dict(index=0),.5,acquire=fail,
                select_bank=lambda w:{},remove_scale=lambda w,b:b,blend_bank=fail)
        self.assertEqual(destination['primary']['flags'],5)

    def test_cached_selection_and_final_primary_reload(self):
        old={'flags':0};new={'flags':3}
        destination=dict(primary=old,component=dict(flags16=16),index=7)
        source=dict(index=3)
        def select(w):
            destination['index']=0;destination['component']['flags16']=0
            return {}
        def blend(dst,a,b,w,selector,mask,**kw):
            self.assertEqual((selector,mask),(2,3));self.assertIs(dst,old)
            destination['primary']=new
        blend_regular_pose(destination,source,.5,acquire=None,select_bank=select,
            remove_scale=lambda w,b:b,blend_bank=blend)
        self.assertEqual(old['flags'],0);self.assertEqual(new['flags'],3|(1<<27))
