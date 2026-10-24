import struct
import unittest
from engine.markup_provider_observation import capture_markup_provider


class ProviderTests(unittest.TestCase):
    def fixture(self, mode=0, count=1, attached=True):
        memory={}
        def put(a,fmt,*v):
            for i,b in enumerate(struct.pack('<'+fmt,*v)):memory[a+i]=b
        base=0x140000000
        put(0x10000,'Q',99)
        put(0x10038,'Q',0x11000);put(0x110b0,'Q',0x12000)
        put(0x12000,'Q',base+0x2909790);put(base+0x2909848,'Q',base+0x12f2d20)
        put(0x12020,'Q',0x13000 if attached else 0)
        put(0x13080,'Q',0x14000);put(0x15a10,'Q',0x16000)
        flags=((mode&1)<<62)|(((mode>>1)&1)<<61)|count
        put(0x16000,'QQ',0x1000 if mode==1 else 0x17000,flags)
        put(0x17050,'IIIIB',0xc00002,0x3f800000,0,0x7f7fffff,2)
        def read(plan):return [bytes(memory[a+i] for i in range(n)) for a,n in plan]
        def capture(reader=read):return capture_markup_provider(reader,0x10000,base,0x4000000,[(0x10000,struct.pack('<Q',99))])
        return memory,put,read,capture

    def test_pointer_modes_and_scalar_record(self):
        for mode in range(4):
            _,_,_,capture=self.fixture(mode)
            got=capture()
            self.assertEqual(got['records'][0]['key'],0xc00002)
            self.assertEqual(got['relative_records'],mode==1)
            self.assertFalse(got['atomic'])
            self.assertFalse(got['callback_execution_proved'])

    def test_null_attachment_and_empty_collection(self):
        self.assertFalse(self.fixture(attached=False)[3]() ['attachment_present'])
        self.assertEqual(self.fixture(count=0)[3]() ['records'],[])

    def test_reject_wrong_table_target_and_count(self):
        for address in [0x12000,0x140000000+0x2909848]:
            _,put,_,capture=self.fixture();put(address,'Q',0x18000)
            with self.assertRaises(ValueError):capture()
        with self.assertRaises(ValueError):self.fixture(count=65)[3]()

    def test_content_change_and_short_read(self):
        _,put,read,capture=self.fixture()
        def changing(plan):
            result=read(plan)
            if (0x17050,17) in plan:put(0x17050,'I',77)
            return result
        with self.assertRaises(ValueError):capture(changing)
        with self.assertRaises(ValueError):capture(lambda plan:[b'']*len(plan))
