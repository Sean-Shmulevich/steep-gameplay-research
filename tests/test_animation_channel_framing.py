import struct
import unittest
from engine.animation_channel_framing import frame_serialized_channel
from engine.animation_container import parse_clip_body
from engine.animation_corpus import inspect_clip
from tests.test_animation_container import fixture


class FramingTests(unittest.TestCase):
    def test_wide_times_and_large_counts_without_sampling(self):
        count=300
        data=struct.pack('<BII',28,0,count)+struct.pack('<'+'H'*(count-1),*range(1,count))+bytes(12*count)
        result=frame_serialized_channel(data)
        self.assertEqual(result['count'],300)
        self.assertEqual(result['consumed'],len(data))
        self.assertEqual(result['time_format'],1)
        self.assertEqual(result['sample_offset'],9+598)

    def test_unsupported_values_are_framed_but_not_decoded(self):
        body=bytearray(fixture());body[-13]=36
        parsed=parse_clip_body(body)
        report=inspect_clip(body,parsed['tracks'])
        self.assertEqual(report['unsupported_codec_counts'],{36:1})
        self.assertFalse(report['all_tracks_supported_and_validated'])
        self.assertEqual(report['validated_tracks'],0)

    def test_mask_count_bounds_order_and_unknown_family(self):
        masked=struct.pack('<BII',17,0,2)+bytes([65,5])+bytes(16)
        self.assertEqual(frame_serialized_channel(masked)['consumed'],len(masked))
        for data in (masked[:-1],struct.pack('<BII',17,0,3)+masked[9:],struct.pack('<BII',28,0,3)+struct.pack('<HH',4,2)+bytes(36),struct.pack('<BII',71,0,1)+bytes(8),struct.pack('<BII',28,0,0xffffffff)):
            with self.assertRaises(ValueError):frame_serialized_channel(data)
