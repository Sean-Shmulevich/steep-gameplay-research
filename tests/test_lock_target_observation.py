import unittest
from engine.lock_target_observation import (
    LOCK_TARGET_PROFILES, decode_target, observe_lock_targets)


class LockTargetTests(unittest.TestCase):
    def test_modular_decode_and_bad_inputs(self):
        self.assertEqual(decode_target(2**64-7, 12), 5)
        for args in ((True, 1), (-1, 1), (2**64, 0)):
            with self.assertRaises(ValueError):
                decode_target(*args)

    def test_supplied_slots_and_observation_boundary(self):
        base = 0x140000000
        targets = {'enter_helper': 0x70001000, 'leave_helper': 0x70002000}
        memory = {base+offset: ((targets[name]-delta) % 2**64).to_bytes(8, 'little')
                  for name, (offset, delta) in LOCK_TARGET_PROFILES.items()}
        report = observe_lock_targets(lambda a, n: memory[a], image_base=base, image_size=0x6000000)
        self.assertEqual(report['targets'], targets)
        self.assertEqual(report['reads'], 4)
        self.assertEqual(report['requested_bytes'], 32)
        self.assertFalse(report['atomic_snapshot'])
        self.assertFalse(report['api_identity_proved'])
        self.assertFalse(report['native_lock_semantics_proved'])

    def test_changed_slot_does_not_publish_targets(self):
        calls = []
        def read(a, n):
            calls.append(a)
            return (len(calls)//3).to_bytes(8, 'little')
        report = observe_lock_targets(read, image_base=1, image_size=0x6000000)
        self.assertEqual(report['status'], 'unstable')
        self.assertNotIn('targets', report)
        self.assertEqual(len(calls), 4)

    def test_static_garbage_is_not_called_or_classified_as_api(self):
        report = observe_lock_targets(lambda a, n: b'\x7f'*8,
                                      image_base=1, image_size=0x6000000)
        self.assertEqual(report['status'], 'observed')
        self.assertFalse(report['all_targets_in_lower_48bit_user_range'])
        self.assertFalse(report['api_identity_proved'])

    def test_short_and_failed_reads_and_invalid_image(self):
        report = observe_lock_targets(lambda a, n: b'', image_base=1, image_size=0x6000000)
        self.assertEqual(report['status'], 'short_read')
        self.assertEqual(report['reads'], 1)
        def fail(a, n):
            raise OSError('unavailable')
        self.assertEqual(observe_lock_targets(fail, image_base=1, image_size=0x6000000)['status'], 'read_failed')
        with self.assertRaises(ValueError):
            observe_lock_targets(fail, image_base=1, image_size=1)

    def test_optional_initializer_preserves_default_read_budget(self):
        from engine.lock_target_observation import INITIALIZE_TARGET_PROFILE
        profiles = dict(LOCK_TARGET_PROFILES, initialize_helper=INITIALIZE_TARGET_PROFILE)
        targets = {name: 0x70001000 + i * 4096 for i, name in enumerate(profiles)}
        memory = {1 + offset: ((targets[name] - delta) % 2**64).to_bytes(8, 'little')
                  for name, (offset, delta) in profiles.items()}
        report = observe_lock_targets(lambda a, n: memory[a], image_base=1,
                                      image_size=0x6000000, include_initializer=True)
        self.assertEqual(report['targets'], targets)
        self.assertEqual((report['reads'], report['requested_bytes']), (6, 48))
        self.assertFalse(report['api_identity_proved'])
        with self.assertRaises(ValueError):
            observe_lock_targets(lambda a, n: memory[a], image_base=1,
                                 image_size=0x6000000, include_initializer=1)
