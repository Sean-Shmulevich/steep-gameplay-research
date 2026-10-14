import unittest
from engine.animation_provider import (
    Handle, Row, Provider, Wrapper, Outputs, select_replacement)


class ProviderLookupTests(unittest.TestCase):
    def test_primary_wins_without_calling_availability(self):
        original, replacement = Handle(7), Handle(8)
        outputs = Outputs()
        def forbidden(_):
            self.fail('primary must bypass wrapper availability')
        selected = select_replacement(
            Provider([Row(7, 0x7fc01234, 9, True, replacement)]),
            [Wrapper(None)], original, outputs, forbidden)
        self.assertIs(selected, replacement)
        self.assertEqual((outputs.scalar_bits, outputs.flag), (0x7fc01234, 9))

    def test_failed_matching_rows_keep_outputs_and_original_identity(self):
        original = Handle(7)
        outputs = Outputs(1, 2)
        selected = select_replacement(
            Provider([Row(7, 3, 4, False, Handle(8))]),
            [None, Wrapper(Provider([Row(9, 5, 6, True, Handle(10))])),
             Wrapper(Provider([Row(7, 11, 12, False, Handle(13))]))],
            original, outputs, lambda _: True)
        self.assertIs(selected, original)
        self.assertEqual((outputs.scalar_bits, outputs.flag), (11, 12))

    def test_duplicate_keys_continue_and_first_available_wins(self):
        original, replacement = Handle(7), Handle(8)
        outputs = Outputs()
        provider = Provider([Row(7, 1, 2, False, Handle(9)),
                             Row(7, 3, 4, True, replacement),
                             Row(7, 5, 6, True, Handle(10))])
        self.assertIs(select_replacement(None, [Wrapper(provider)], original,
                                         outputs, lambda _: True), replacement)
        self.assertEqual((outputs.scalar_bits, outputs.flag), (3, 4))

    def test_rejected_and_null_wrappers_do_not_reset_outputs(self):
        original = Handle(7)
        outputs = Outputs(0x80000000, 255)
        provider = Provider([Row(7, 1, 2, True, Handle(8))])
        calls = []
        def reject(pointer):
            calls.append(pointer)
            return False
        self.assertIs(select_replacement(None, [None, Wrapper(provider),
                           Wrapper(None, 0x80000000)], original, outputs, reject),
                      original)
        self.assertEqual(calls, [provider])
        self.assertEqual((outputs.scalar_bits, outputs.flag), (0x80000000, 255))

    def test_callback_pointer_replacement_is_observed(self):
        original, replacement = Handle(7), Handle(8)
        old = Provider([])
        new = Provider([Row(7, 1, 2, True, replacement)])
        wrapper = Wrapper(old)
        def swap(pointer):
            self.assertIs(pointer, old)
            wrapper.pointer = new
            return True
        self.assertIs(select_replacement(None, [wrapper], original, Outputs(),
                                         swap), replacement)
        wrapper.control_word = 0x80000000
        self.assertIs(select_replacement(None, [wrapper], original, Outputs(),
                            lambda _: self.fail('sign bit bypasses callback')),
                      replacement)
