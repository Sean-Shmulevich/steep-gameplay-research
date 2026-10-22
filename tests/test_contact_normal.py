import unittest
from reference.contact_normal import accumulate,normalize


class ContactNormalTests(unittest.TestCase):
    def test_eligibility_weight_and_fourth_lane(self):
        result=accumulate([
            {'eligible':False,'weight':100,'normal':[1,1,1,1]},
            {'eligible':True,'weight':2,'normal':[1,0,1,3]},
            {'eligible':True,'weight':1,'normal':[-1,0,1,2]}])
        self.assertEqual(result,{'eligible_count':2,'weighted_normal':(1,0,3,8)})

    def test_normalization_clears_w_and_uses_supplied_seed(self):
        seen=[]
        def seed(squared):seen.append(squared);return .2
        result=normalize((3,4,0,99),reciprocal_sqrt=seed)
        self.assertEqual(seen,[25])
        self.assertAlmostEqual(result[0],.6,places=6)
        self.assertAlmostEqual(result[1],.8,places=6)
        self.assertEqual(result[3],0)

    def test_no_fabricated_normal_for_empty_or_cancelled_contacts(self):
        self.assertEqual(accumulate([])['weighted_normal'],(0,0,0,0))
        with self.assertRaises(ValueError):normalize((0,0,0,1),reciprocal_sqrt=lambda x:0)
        with self.assertRaises(TypeError):normalize((1,0,0,0))
