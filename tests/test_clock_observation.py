import struct
import unittest
from engine.clock_observation import capture_clocks, decode_clock


class ClockObservationTests(unittest.TestCase):
    def fixture(self, mutate=None):
        base, world, root, driver, slots = 0x140000000, 0x10000, 0x20000, 0x30000, 0x40000
        memory={}
        def put(a,b): memory.update({a+i:v for i,v in enumerate(b)})
        put(0x9000,b'identity')
        for a,v in [(base+0x32fb438,root),(base+0x32fb600,driver),(base+0x33060a0,10000)]:put(a,struct.pack('<Q',v))
        for a in [root,world+0x1048,world+0x10a0,world+0x10f8]:
            put(a,bytes(0x47));put(a+0x18,struct.pack('<f',.125))
        put(root+0x47,struct.pack('<QHH',slots,0x4003,3))
        put(slots,struct.pack('<QQQ',world+0x1048,world+0x10a0,world+0x10f8))
        put(driver,bytes(0x99));put(driver+0x94,struct.pack('<I',2))
        calls=[]
        def read(ranges):
            calls.append(ranges)
            if mutate:mutate(len(calls),put,root,driver,slots)
            return [bytes(memory[a+i] for i in range(n)) for a,n in ranges]
        return read,dict(image_base=base,world=world,guards=[(0x9000,b'identity')]),calls

    def test_membership_and_no_pointer_output(self):
        read,args,calls=self.fixture()
        r=capture_clocks(read,**args)
        self.assertEqual(r['world_child_indices'],dict(ordinary=[0],alternate=[1],third=[2]))
        self.assertEqual(r['clocks']['ordinary']['interval']['value'],.125)
        self.assertEqual(r['driver']['mode'],2)
        self.assertFalse(r['atomic']);self.assertFalse(r['safe_to_step_established'])
        self.assertEqual(len(calls),7)

    def test_mutated_membership_rejected(self):
        def mutate(n,put,root,driver,slots):
            if n==7:put(slots,struct.pack('<Q',0xdead))
        read,args,_=self.fixture(mutate)
        with self.assertRaisesRegex(ValueError,'changed'):capture_clocks(read,**args)

    def test_child_list_bounds(self):
        def mutate(n,put,root,driver,slots):
            if n==3:put(root+0x47,struct.pack('<QHH',slots,513,513))
        read,args,_=self.fixture(mutate)
        with self.assertRaisesRegex(ValueError,'bounds'):capture_clocks(read,**args)

    def test_short_transport_and_missing_guards(self):
        _,args,_=self.fixture()
        with self.assertRaisesRegex(ValueError,'short'):capture_clocks(lambda r:[b'']*len(r),**args)
        args['guards']=[]
        with self.assertRaises(ValueError):capture_clocks(lambda r:[],**args)

    def test_raw_nonfinite_and_signed_fields(self):
        b=bytearray(0x47);struct.pack_into('<I',b,0x18,0x7fc01234);struct.pack_into('<i',b,0x38,-1)
        r=decode_clock(bytes(b))
        self.assertEqual(r['interval'],dict(bits=0x7fc01234,value=None,finite=False))
        self.assertEqual(r['hold_count'],-1)
        with self.assertRaises(ValueError):decode_clock(b'')

    def test_divided_ticks_are_distinct_from_total_and_interval(self):
        from engine.clock_tree import ClockState, advance_clock
        from engine.action_axis_ramp import clock_scalar
        state = advance_clock(ClockState(), 16.)
        data = bytearray(0x47)
        struct.pack_into('<QQ',data,0,state.accumulated_ticks,state.divided_ticks)
        decoded = decode_clock(bytes(data))
        self.assertEqual(decoded['accumulated_ticks'],480)
        self.assertEqual(decoded['divided_ticks'],16)
        self.assertAlmostEqual(clock_scalar(decoded['divided_ticks']),.016,places=8)
        held = advance_clock(ClockState(accumulated_ticks=480,divided_ticks=16,hold_count=1),16.)
        self.assertEqual(held.divided_ticks,16)
