import json
import unittest
from pathlib import Path
from reference.animation_handle import resolve_channel_handle


class ChannelHandleTests(unittest.TestCase):
    def args(self, **changes):
        args = dict(raw_pointer=0x12345678, status_word=0, thread_mask=2**64-1,
                    cached_index=7, cached_generation=10, component_generation=11,
                    entries=[(1, 0x12340002)], key=1)
        args.update(changes)
        return args

    def test_native_receipt(self):
        r = json.loads((Path(__file__).resolve().parents[1] /
                        'native/snow_host/channel_handle_validation.json').read_text())
        for row in r['rows']:
            self.assertEqual(resolve_channel_handle(**row['inputs']), row['result'])

    def test_sign_bit_overrides_thread_mask(self):
        result = resolve_channel_handle(**self.args(status_word=0x80000000, thread_mask=0))
        self.assertEqual(result['pointer'], 0x12345678)
        self.assertEqual(result['cached_index'], 2)

    def test_partial_mask_is_bitwise(self):
        result = resolve_channel_handle(**self.args(thread_mask=0xffff0000))
        self.assertEqual(result['pointer'], 0x12340000)

    def test_null_preserves_cache_and_ignores_table(self):
        result = resolve_channel_handle(**self.args(thread_mask=0, entries='not accessed', component_generation=None))
        self.assertEqual((result['cached_index'], result['cached_generation']), (7, 10))
        self.assertFalse(result['refreshed'])

    def test_equal_generation_preserves_missing_cache(self):
        result = resolve_channel_handle(**self.args(cached_generation=11, cached_index=65535, entries='not accessed'))
        self.assertEqual(result['cached_index'], 65535)
        self.assertFalse(result['refreshed'])

    def test_miss_updates_generation(self):
        result = resolve_channel_handle(**self.args(entries=None))
        self.assertEqual(result['cached_index'], 65535)
        self.assertEqual(result['cached_generation'], 11)
        self.assertFalse(result['lifetime_retained'])


if __name__ == '__main__':
    unittest.main()
