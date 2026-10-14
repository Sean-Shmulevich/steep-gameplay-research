import math
import struct
import unittest
import zlib
from engine.animation_decisions import scalar_compare,EPSILON,decode_comparison,predicate_expression
from engine import animation,graph


class DecisionTests(unittest.TestCase):
    def test_float32_equality_boundaries_and_unordered(self):
        self.assertTrue(scalar_compare('Equals',0,EPSILON))
        self.assertFalse(scalar_compare(0,0,EPSILON*1.01))
        self.assertTrue(scalar_compare(2,-90,-90))
        self.assertFalse(scalar_compare(1,-90,-90))
        self.assertTrue(scalar_compare(0,16777216,16777217))
        self.assertFalse(scalar_compare(0,math.inf,math.inf))
        for op in range(6):self.assertEqual(scalar_compare(op,math.nan,0),op==5)
        self.assertFalse(scalar_compare(99,0,0))
        self.assertTrue(scalar_compare(5,1e300,1e300))

    def test_selected_record_resolves_parameter_not_destination(self):
        p=bytearray(184);struct.pack_into('<I',p,0,zlib.crc32(b'AtomCompareValuesNode'))
        for offset,binding in zip((16,72,128),(4,0,3)):struct.pack_into('<II',p,offset,zlib.crc32(b'AtomInputPort'),binding)
        struct.pack_into('<I',p,24,2);struct.pack_into('<I',p,80,0);struct.pack_into('<f',p,144,-90)
        inputs=[{'name':'GrabPadAngle','type':'scalar'}]
        result=decode_comparison(p,inputs)
        self.assertEqual(result,{'parameter':'GrabPadAngle','operator':'GreaterThanOrEquals','threshold':-90})
        self.assertEqual(predicate_expression(result)['left'],{'input':'GrabPadAngle'})
        struct.pack_into('<I',p,76,1)
        with self.assertRaises(ValueError):decode_comparison(p,inputs)
        with self.assertRaises(ValueError):decode_comparison(p[:-1],inputs)

    def test_graph_boundary_selects_explicit_branch_and_retains_clocks(self):
        rig,clips=animation.default_resources();names=list(clips)
        definition={'schema_version':1,'root':'choose','nodes':{'a':{'type':'clip','clip':names[0]},'b':{'type':'clip','clip':names[1]},'choose':{'type':'select','condition':{'compare':0,'left':{'input':'GrabPadIntensity'},'right':0},'if_true':'a','if_false':'b'}}}
        first=graph.evaluate_pose(rig,clips,{},.1,definition,{'GrabPadIntensity':.000005})
        self.assertEqual(first['diagnostics']['contexts']['choose']['selected'],'a')
        second=graph.evaluate_pose(rig,clips,first['state'],.1,definition,{'GrabPadIntensity':.00002})
        self.assertEqual(second['diagnostics']['contexts']['choose']['selected'],'b')
        self.assertEqual(second['state']['nodes']['a'],first['state']['nodes']['a'])
        definition['nodes']['a']['rate']={'compare':0,'left':1}
        with self.assertRaises(ValueError):graph.evaluate_pose(rig,clips,{},0,definition,{'GrabPadIntensity':1})
