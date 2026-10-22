import struct
import unittest
from engine.motion_input_ingestion import action_read_sequence, ingest_motion_prefix

zero=bytes(16)
def words(*values): return struct.pack('<4I',*values)
def floats(*values): return struct.pack('<4f',*values)

class MotionIngestionTests(unittest.TestCase):
    def test_separate_reads_drive_different_outputs(self):
        r=ingest_motion_prefix((floats(1,0,0,0),zero,floats(0,2,0,0),floats(3,0,0,0)),
            flip_x=False,counts=(6,9),smoothed=(zero,zero),alpha=.5)
        self.assertEqual((r.primary_count,r.secondary_count),(7,0))
        self.assertEqual(r.smoothed_primary,floats(0,1,0,0))
        self.assertEqual(r.smoothed_secondary,floats(1.5,0,0,0))
        self.assertEqual(r.reset_byte,0)

    def test_bitwise_flip_signed_zero_nan_and_wrap(self):
        r=ingest_motion_prefix((words(0x7fc01234,0,0,0),words(0x80000000,0,0,0),zero,zero),
            flip_x=True,counts=(0xffffffff,7),smoothed=(zero,zero),alpha=.1)
        self.assertEqual(r.primary,words(0xffc01234,0,0,0))
        self.assertEqual(r.secondary,zero)
        self.assertEqual((r.primary_count,r.secondary_count),(0,0))

    def test_action_route_only_changes_first_read(self):
        for enabled,predicate in ((False,False),(False,True),(True,False),(True,True)):
            self.assertEqual(action_read_sequence(enabled,predicate),
                             (0xd9 if enabled and predicate else 0x76,0x77,0x76,0x77))

    def test_invalid_payload_and_counter(self):
        with self.assertRaises(ValueError):
            ingest_motion_prefix((b'x',zero,zero,zero),flip_x=False,counts=(0,0),smoothed=(zero,zero),alpha=.1)
        with self.assertRaises(ValueError):
            ingest_motion_prefix((zero,)*4,flip_x=False,counts=(-1,0),smoothed=(zero,zero),alpha=.1)
