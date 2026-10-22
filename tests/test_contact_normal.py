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

    def test_no_history_keeps_weighted_and_tie_favors_fit(self):
        from reference.contact_normal import select_candidate
        seed=lambda x:1
        r=select_candidate((0,0,1),(.6,0,.8),(0,0,1),
                           had_previous_contact=False,reciprocal_sqrt=seed)
        self.assertEqual(r['source'],'weighted')
        r=select_candidate((0,.6,.8),(.6,0,.8),(0,0,1),
                           had_previous_contact=True,reciprocal_sqrt=seed)
        self.assertEqual(r['source'],'fitted')
        self.assertFalse(r['fit_corrected'])

    def test_low_fit_corrected_before_alignment_comparison(self):
        from reference.contact_normal import select_candidate
        import math
        r=select_candidate((0,0,1),(1,0,0),(-1,0,0),
                           had_previous_contact=True,reciprocal_sqrt=lambda x:1/math.sqrt(x))
        self.assertTrue(r['fit_corrected'])
        self.assertEqual(r['source'],'fitted')
        self.assertLess(r['normal'][0],-.99)
        self.assertGreater(r['normal'][2],0)
        self.assertEqual(math.copysign(1,r['normal'][3]),-1)

    def test_low_z_threshold_is_strict(self):
        from reference.contact_normal import select_candidate
        r=select_candidate((0,0,1),(1,0,.1),(-1,0,0),
                           had_previous_contact=True,reciprocal_sqrt=lambda x:1)
        self.assertFalse(r['fit_corrected'])

    def test_smoothing_gain_resets_and_uses_base_rate(self):
        from reference.contact_normal import smoothing_gain
        from reference.decay_exp import cooker_table
        from reference.runtime_curve import evaluate
        table=cooker_table(vector_path='sse2',scalar_path='sse2')
        lookup=lambda x:evaluate(x,**table)
        normal=smoothing_gain(1,1,1/60,decay_lookup=lookup)
        slow=smoothing_gain(0,1,1/60,decay_lookup=lookup)
        self.assertEqual(normal['base_rate'],60)
        self.assertEqual(normal['value'],.75)
        self.assertEqual(slow['base_rate'],1)
        self.assertLess(slow['value'],.02)
        self.assertEqual(slow['lookup_argument'],0)
        self.assertEqual(slow,smoothing_gain(0,1,1/60,decay_lookup=lookup))

    def test_slow_gain_thresholds_are_strict(self):
        from reference.contact_normal import smoothing_gain
        for old,new,expected in ((.15,1,60),(0,.3,60),(.1499,.3001,1)):
            self.assertEqual(smoothing_gain(old,new,.01,decay_lookup=lambda x:1)['base_rate'],expected)
