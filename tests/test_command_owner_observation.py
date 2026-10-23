import struct
import unittest
from engine.command_owner_observation import observe_command_owner


class CommandOwnerObservationTests(unittest.TestCase):
    def fixture(self):
        memory = {}
        def put(a, *values):
            memory[a] = struct.pack('<'+'Q'*len(values), *values)
        put(0x1100, 0x5000); put(0x1110, 0x54b8)
        put(0x5000, 0x1800); put(0x54b8, 0x1700)
        put(0x1700, 0x2100, 0x2200)
        for slot, method in zip((0, 0x90, 0xc8), (0x2300, 0x2400, 0x2500)):
            put(0x1800+slot, method)
        def read(a, n):
            return memory.get(a, b'')[:n]
        args = dict(owner_global=0x1100, participant_global=0x1110,
                    embedded_offset=0x4b8, participant_table=0x1700,
                    participant_methods=(0x2100, 0x2200),
                    owner_profiles={0x1800: dict(name='SyntheticOwner', methods=(0x2300, 0x2400, 0x2500))},
                    image_range=(0x1000, 0x4000), code_range=(0x2000, 0x3000))
        return args, read, put

    def test_identity_and_every_short_read(self):
        args, read, _ = self.fixture()
        result = observe_command_owner(read, **args)
        self.assertEqual(result['identity']['owner_type'], 'SyntheticOwner')
        self.assertEqual((result['reads'], result['bytes']), (16, 144))
        self.assertFalse(result['registration_proved'])
        for fail in range(1, 17):
            calls = 0
            def short(a, n):
                nonlocal calls
                calls += 1
                return b'' if calls == fail else read(a, n)
            result = observe_command_owner(short, **args)
            self.assertEqual(result['status'], 'short_read')
            self.assertNotIn('identity', result)

    def test_mismatches_reject_without_identity(self):
        for a, values, status in [
            (0x1100, (0,), 'owner_unavailable'),
            (0x1110, (0x54c0,), 'owner_link_mismatch'),
            (0x54b8, (0x1750,), 'participant_table_mismatch'),
            (0x1700, (0x2100, 0x2210), 'participant_methods_mismatch'),
            (0x5000, (0x1900,), 'unknown_owner_table'),
            (0x1890, (0x2410,), 'owner_methods_mismatch'),
        ]:
            args, read, put = self.fixture(); put(a, *values)
            result = observe_command_owner(read, **args)
            self.assertEqual(result['status'], status)
            self.assertNotIn('identity', result)

    def test_valid_identity_replacement_between_samples(self):
        args, read, put = self.fixture(); calls = 0
        def replace(a, n):
            nonlocal calls
            calls += 1
            if calls == 9:
                put(0x1100, 0x6000); put(0x1110, 0x64b8)
                put(0x6000, 0x1800); put(0x64b8, 0x1700)
            return read(a, n)
        result = observe_command_owner(replace, **args)
        self.assertEqual(result['status'], 'unstable')
        self.assertNotIn('identity', result)

    def test_invalid_profiles_do_not_read(self):
        for field, value in [('owner_global', 0x5000), ('embedded_offset', -1),
                             ('participant_methods', (0x2100, 0x4500)),
                             ('owner_profiles', {})]:
            args, _, _ = self.fixture(); args[field] = value
            def no_read(a, n):
                self.fail('invalid profile must not perform reads')
            with self.assertRaises(ValueError):
                observe_command_owner(no_read, **args)
