import unittest
from engine.world import World
from engine.assets import ResourceStore
from engine.input import validate
class WorldTests(unittest.TestCase):
    def test_slope_and_patch_boundaries(self):
        w=World({'slope':[-.2,0], 'patches':[{'bounds':[0,0,2,2],'material':{'name':'ice','grip':.1}}]})
        self.assertAlmostEqual(w.sample(2,0)['height'],-.4)
        self.assertEqual(w.sample(1,1)['material']['name'],'ice')
        self.assertEqual(w.sample(2,1)['material']['name'],'synthetic_packed')
    def test_swept_tree_collision(self):
        w=World({'slope':[0,0],'obstacles':[{'center':[5,0],'radius':1,'height':5}]})
        hit=w.sweep([0,0,1],[10,0,1]);self.assertAlmostEqual(hit['fraction'],.38)
        self.assertIsNone(w.sweep([0,0,10],[10,0,10]))
    def test_invalid_descriptors(self):
        with self.assertRaises(ValueError):World({'material':{'density':-1}})
        with self.assertRaises(ValueError):validate({'steer':float('nan')})
        with self.assertRaises(ValueError):validate({'jump':1})
    def test_registry_categories_and_isolation(self):
        store=ResourceStore();record={'id':'test','kind':'clip','category':'synthetic','data':{'v':[1]}}
        store.add(record);record['data']['v'][0]=2
        self.assertEqual(store.get('test')['data']['v'],[1])
        with self.assertRaises(ValueError):store.add(record)
        store.add(record,replace=True);self.assertEqual(store.generation,2)
