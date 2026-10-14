import struct
import unittest
from engine.animation_corpus import inspect_clip


class CorpusInspectionTests(unittest.TestCase):
    def test_complete_supported_record(self):
        body=bytes([27])+struct.pack('<II',12,1)+struct.pack('<3f',1,2,3)
        result=inspect_clip(body,[{'codec':27,'serialized_start':0,'serialized_end':len(body)}])
        self.assertTrue(result['all_tracks_supported_and_validated'])
        self.assertEqual(result['sample_checks'],7)
        self.assertEqual(result['failures'],[])
        self.assertNotIn('value',result)

    def test_unsupported_and_shared_are_not_success(self):
        result=inspect_clip(b'',[{'codec':36},{'shared_track_reference':0}])
        self.assertFalse(result['all_tracks_supported_and_validated'])
        self.assertEqual(result['unsupported_codec_counts'],{36:1})
        self.assertEqual(result['unresolved_shared_records'],1)
        self.assertEqual(result['validated_tracks'],0)

    def test_bad_boundaries_and_metadata_report_failure(self):
        result=inspect_clip(b'',[{'codec':27,'serialized_start':0,'serialized_end':8},
                                {'codec':'payload must not escape'}])
        self.assertEqual(len(result['failures']),2)
        self.assertNotIn('payload must not escape',str(result))
