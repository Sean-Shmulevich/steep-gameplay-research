import unittest
from engine.snow_pose_record import pack_pose_record, pose_submission_notification


class PoseRecordTests(unittest.TestCase):
    def test_packing_preserves_bits_and_padding_and_swaps_only_frame_blocks(self):
        source=bytes(range(256));initial=b'\xa5'*0x120
        mask=b'\xff'*12+b'\0'*4
        a=pack_pose_record(source,initial,mask);b=pack_pose_record(source,initial,mask,True)
        self.assertEqual(a[:12],source[:12]);self.assertEqual(a[12:16],b'\x00'*4)
        self.assertEqual(a[0xfa:0xfc],b'\xa5'*2)
        self.assertEqual(b[:0x40],a[0x40:0x80])
        self.assertEqual(b[0x40:0x80],a[:0x40]);self.assertEqual(b[0x80:],a[0x80:])

    def test_notification_is_exact_one_not_nonzero(self):
        self.assertEqual([pose_submission_notification(x) for x in (0,1,2,255)],
                         [False,True,False,False])

    def test_mask_is_supplied_and_applies_to_overlapping_fourth_lane(self):
        source=bytes(range(256));initial=b'\xa5'*288
        result=pack_pose_record(source,initial,b'\xff'*16)
        self.assertEqual(result[:16],source[:16])
        self.assertEqual(result[16:32],source[12:28])
        self.assertEqual(pack_pose_record(source,initial,b'\0'*16)[:128],b'\0'*128)
