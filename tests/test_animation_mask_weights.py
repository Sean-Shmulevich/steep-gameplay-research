import json
from pathlib import Path
import unittest
from reference.animation_mask_weights import iter_masked_channel_weights


class MaskWeightTests(unittest.TestCase):
    def test_original_instruction_receipt(self):
        r=json.loads((Path(__file__).resolve().parents[1]/'native/snow_host/masked_channel_weights_validation.json').read_text())
        self.assertEqual(r['cases'],24)
        for row in r['rows']:
            self.assertEqual(list(iter_masked_channel_weights(r['descriptors'],lambda o:row['byte'],
                row['weight'],row['mode'])),row['events'])

    def test_weight_reads_follow_consumer_mutations(self):
        descriptors=[dict(key=k,kind=t,offset=o) for k,t,o in ((1,1,0),(1,0,1),(2,1,2),(2,0,3))]
        data=bytearray([0,255,0,0]);walk=iter_masked_channel_weights(descriptors,lambda o:data[o],1.,1)
        self.assertEqual(next(walk)['weight'],1.)
        data[3]=255
        self.assertEqual(next(walk)['weight'],1.)
        self.assertEqual(list(walk),[])

    def test_same_key_reuses_weight_without_consuming_next_byte(self):
        descriptors=[dict(key=2,kind=t,offset=i) for i,t in enumerate((1,0,1,0))]
        calls=[]
        def read(o):calls.append(o);return 255
        rows=list(iter_masked_channel_weights(descriptors,read,.5,0))
        self.assertEqual(calls,[1]);self.assertEqual([r['index'] for r in rows],[0,2,3])
        self.assertEqual([r['weight'] for r in rows],[.5]*3)
