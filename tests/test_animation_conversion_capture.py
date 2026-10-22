import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('conversion_check',Path(__file__).resolve().parents[1]/'scripts/validate_animation_conversion.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class ConversionCaptureTests(unittest.TestCase):
    def capture(self):
        p=dict(found=True,bank_flags=0,conversion_direct=False,record_index=0,
               vector=[1,2,3,7],rotation=[0,0,0,1],parent_vector=[10,20,30,9],parent_rotation=[0,0,0,1],
               provider_vector=[11,22,33,9],provider_rotation=[0,0,0,1])
        return dict(rows=[dict(animation=dict(status='completed',result=p))])
    def test_composed_and_direct(self):
        c=self.capture();self.assertTrue(module.validate_conversion(c)['ok'])
        p=c['rows'][0]['animation']['result'];p.update(bank_flags=1<<26,conversion_direct=True,provider_vector=p['vector'])
        self.assertTrue(module.validate_conversion(c)['ok'])
    def test_mismatch_and_flags(self):
        for field,value in [('provider_vector',[11,22,34,9]),('conversion_direct',True),('record_index',65535),('parent_rotation',[0,0,0,float('nan')])]:
            c=self.capture();c['rows'][0]['animation']['result'][field]=value
            self.assertFalse(module.validate_conversion(c)['ok'])
    def test_no_success_from_missing_or_failed(self):
        c=self.capture();c['rows'][0]['animation']['status']='failed'
        self.assertFalse(module.validate_conversion(c)['ok'])
    def test_json_nine_digits_roundtrip(self):
        import json
        c=self.capture();p=c['rows'][0]['animation']['result']
        p['vector']=[.12345678,-.12345678,2.3456789,0]
        result=module.provider_pose_transform(p['vector'],p['rotation'],p['parent_vector'],p['parent_rotation'],False)
        p['provider_vector']=[float(format(x,'.9g')) for x in result['position']]
        self.assertTrue(module.validate_conversion(json.loads(json.dumps(c)))['ok'])
