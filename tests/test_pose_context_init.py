import struct
import unittest
from engine.pose_context_init import initialize_pose_jobs, initialize_pose_context_tail, bind_pose_jobs


class ContextInitTests(unittest.TestCase):
    def test_jobs_preserve_scalar_settings_and_alias_submission(self):
        context=bytearray([0xa5]*0x500)
        initialize_pose_jobs(context,context_token=0x10000)
        binding=bind_pose_jobs(context,context_token=0x10000)
        for i,token in enumerate(binding['arguments']):
            job=binding['jobs'][token]
            self.assertEqual(struct.unpack_from('<QI',job),(0x10000,i))
            self.assertEqual(bytes(job[12:]),b'\xa5'*12)
        struct.pack_into('<fQ',context,0x14+24*31,.25,0x9000)
        self.assertEqual(struct.unpack_from('<fQ',binding['jobs'][0x102f0],12),(.25,0x9000))
        struct.pack_into('<Q',context,0x308,777)
        self.assertEqual(binding['arguments'][0],777)
        self.assertEqual(context[0:8],b'\xa5'*8)

    def test_tail_defaults_callback_order_and_pointer_reload(self):
        context=bytearray([0xa5]*0x500)
        struct.pack_into('<QQ',context,0x408,123,456)
        events=[]
        def mark(token):
            events.append(token)
            self.assertEqual(context[0x44c],1)
            self.assertEqual(context[0x480:0x4a0],bytes(32))
            self.assertEqual(context[8:16],b'\xa5'*8)
            if token==123:struct.pack_into('<Q',context,0x410,789)
        initialize_pose_context_tail(context,context_token=0x10000,mark_inactive=mark)
        self.assertEqual(events,[123,789])
        for begin,end in ((0x44d,0x450),(0x46c,0x470),(0x4a0,0x500)):
            self.assertEqual(context[begin:end],b'\xa5'*(end-begin))
        self.assertEqual(struct.unpack_from('<I',context,0x2f8)[0],31)

    def test_binding_rejects_truncated_region(self):
        with self.assertRaises(ValueError):bind_pose_jobs(bytearray(20),context_token=0)


if __name__=='__main__':unittest.main()
