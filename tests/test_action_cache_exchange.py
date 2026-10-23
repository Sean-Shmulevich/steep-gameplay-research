import unittest
from engine.action_cache_exchange import CACHE_SPAN,EXCHANGED_RANGES,exchange_input_cache

class CacheExchangeTests(unittest.TestCase):
    def test_field_ranges_and_double_exchange(self):
        a=bytes([17])*CACHE_SPAN;b=bytes([231])*CACHE_SPAN
        x,y=exchange_input_cache(a,b)
        for i in range(CACHE_SPAN):
            swapped=any(start<=i<end for start,end in EXCHANGED_RANGES)
            self.assertEqual(x[i],b[i] if swapped else a[i])
            self.assertEqual(y[i],a[i] if swapped else b[i])
        self.assertEqual(exchange_input_cache(x,y),(a,b))
    def test_nonfinite_bits_are_preserved(self):
        a=bytearray(CACHE_SPAN);b=bytearray(CACHE_SPAN)
        a[0x1f0:0x200]=bytes.fromhex('000000803412c07f0000807f000080ff')
        x,y=exchange_input_cache(bytes(a),bytes(b))
        self.assertEqual(y[0x1f0:0x200],a[0x1f0:0x200])
        self.assertEqual(x[0x1f0:0x200],bytes(16))
    def test_size_contract(self):
        with self.assertRaises(ValueError):exchange_input_cache(bytes(1),bytes(CACHE_SPAN))
