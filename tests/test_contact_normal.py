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

    def test_normal_rotation_identity_and_quarter_turn(self):
        from reference.contact_normal import rotate_normal
        import math
        seed=lambda x:1/math.sqrt(x)
        self.assertEqual(rotate_normal((1,0,0),(0,0,0,1),reciprocal_sqrt=seed),(1,0,0,0))
        result=rotate_normal((0,0,1),(0,math.sqrt(.5),0,math.sqrt(.5)),reciprocal_sqrt=seed)
        self.assertAlmostEqual(result[0],1,places=6)
        self.assertAlmostEqual(result[2],0,places=6)
        self.assertEqual(result[3],0)

    def test_normal_rotation_preserves_signed_zero_w(self):
        from reference.contact_normal import rotate_normal
        import math
        result=rotate_normal((1,0,0),(-.6,0,0,.8),reciprocal_sqrt=lambda x:1/math.sqrt(x))
        self.assertEqual(result[3],0)
        self.assertEqual(math.copysign(1,result[3]),-1)

    def test_normal_rotation_rejects_degenerate_and_bad_shape(self):
        from reference.contact_normal import rotate_normal
        with self.assertRaises(ValueError):rotate_normal((0,0,0),(0,0,0,1),reciprocal_sqrt=lambda x:1)
        with self.assertRaises(ValueError):rotate_normal((1,0),(0,0,0,1),reciprocal_sqrt=lambda x:1)

    def smoothing_services(self):
        import math
        from reference.decay_exp import cooker_table
        from reference.runtime_curve import evaluate
        table=cooker_table(vector_path='sse2',scalar_path='sse2')
        return dict(angle_lookup=lambda x:.6,decay_lookup=lambda x:evaluate(x,**table),
                    sine=math.sin,cosine=math.cos,reciprocal_sqrt=lambda x:1/math.sqrt(x))

    def test_composed_smoothing_rotates_toward_candidate(self):
        from reference.contact_normal import smooth_normal
        result=smooth_normal((0,0,1),(.6,0,.8),1,1/60,**self.smoothing_services())
        self.assertEqual(result['branch'],'rotated')
        self.assertGreater(result['normal'][0],0)
        self.assertLess(result['normal'][0],.6)
        self.assertEqual(result['gain']['value'],.75)

    def test_composed_bypasses_do_not_call_numerical_services(self):
        from reference.contact_normal import smooth_normal
        def forbidden(*args):raise AssertionError('Unexpected callback')
        services={k:forbidden for k in self.smoothing_services()}
        for old,new,control,branch in [((0,0,1),(1,0,0),.2,'control_bypass'),
                                     ((0,0,1),(0,0,-1),1,'axis_bypass')]:
            result=smooth_normal(old,new,control,.01,**services)
            self.assertEqual(result['branch'],branch)
            self.assertEqual(result['normal'],new+(0.,))
        services['angle_lookup']=lambda x:0
        result=smooth_normal((0,0,1),(1,0,0),1,.01,**services)
        self.assertEqual(result['branch'],'angle_bypass')
