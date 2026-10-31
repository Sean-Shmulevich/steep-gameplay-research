import unittest
from engine.pose_body_loading_bench import run


class BodyLoadingRuntimeTests(unittest.TestCase):
    def test_joined_load_allocates_parameters_transform_and_finalizes_resource(self):
        result=run()
        self.assertEqual(result['reader_error'],0)
        self.assertEqual(result['registered_objects'],2)
        self.assertEqual(result['decoded_entry_attempts'],1)
        self.assertEqual(result['motion'],[1,2,3,4,5,6])
        self.assertEqual(result['resource_owner_index'],[10,0])
        self.assertEqual(result['local_translation'],[2,3,4])
        self.assertEqual(result['scalar_vector'],[3,4,5,2])
        self.assertEqual(result['parameters'],[-1,6,-1])
        self.assertEqual(result['events'],['transform allocation','scalar_vector allocation','triple allocation'])
