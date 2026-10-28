import struct
import unittest
from engine.pose_grid_candidates import collect_grid_triangle_candidates


class CollectionTest(unittest.TestCase):
    def resource(self,width,height):
        r=bytearray(0xa0)
        struct.pack_into('<2f',r,0x70,1,1);struct.pack_into('<3f',r,0x7c,0,0,-1)
        struct.pack_into('<3f',r,0x88,width,height,1);struct.pack_into('<2H',r,0x9c,width,height)
        return r

    def test_retry_at_exact128_even_without_more_candidates(self):
        result=collect_grid_triangle_candidates(self.resource(8,8),[0,0,-1,8,8,1])
        self.assertEqual(result['query_capacities'],[128,128])
        self.assertEqual(result['ids'],list(range(128)))

    def test_larger_retry_and_small_single_query(self):
        for width,height,capacities in [(9,8,[128,144]),(3,2,[12])]:
            result=collect_grid_triangle_candidates(self.resource(width,height),[0,0,-1,width,height,1])
            self.assertEqual(result['query_capacities'],capacities)
            self.assertEqual(result['ids'],list(range(width*height*2)))

    def test_empty_intersection_does_not_retry(self):
        result=collect_grid_triangle_candidates(self.resource(10,10),[0,0,2,10,10,3])
        self.assertEqual(result,dict(ids=[],query_capacities=[128],retried=False))
