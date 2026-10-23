import unittest
from engine.action_cache_preference import preferred_input_cache


def name(text):
    return text.encode('utf-16le', errors='surrogatepass') + b'\0\0'


class CachePreferenceTests(unittest.TestCase):
    def test_duplicates_and_low_byte(self):
        seen = []
        def ready(index):
            seen.append(index)
            return 0x100 if index == 0 else 0x101
        self.assertEqual(preferred_input_cache(name('Pad'),
                         [name('Pad'), name('pad'), name('Pad')], ready), 2)
        self.assertEqual(seen, [0, 2])

    def test_empty_bypass(self):
        self.assertIsNone(preferred_input_cache(name(''), None, None))

    def test_terminator_and_surrogates(self):
        raw = name('\ud800')
        self.assertEqual(preferred_input_cache(raw + b'xx', [raw], lambda i: 255), 0)
        self.assertIsNone(preferred_input_cache(name('ab'), [name('abc')], lambda i: 1))

    def test_missing_and_invalid(self):
        self.assertIsNone(preferred_input_cache(name('a'), [], None))
        with self.assertRaises(ValueError):
            preferred_input_cache(b'a\0', [], None)
        with self.assertRaises(ValueError):
            preferred_input_cache(name('a'), [name('a')], lambda i: -1)
