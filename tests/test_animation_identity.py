import unittest
from engine.animation_identity import identity_bucket, lookup_identity


class AnimationIdentityTests(unittest.TestCase):
    def setUp(self):
        self.key = bytes(range(16))
        self.empty = b'\xff' * 16
        self.deleted = b'\xfe' * 16
        self.kw = dict(empty_key=self.empty, deleted_key=self.deleted)

    def test_failure_output_distinction(self):
        self.assertEqual(lookup_identity(bytes(16), (), initial_value=123, **self.kw), (False, 123))
        rows = [(self.empty, 0)] * 8
        self.assertEqual(lookup_identity(self.key, rows, **self.kw), (False, 0))
        self.assertEqual(lookup_identity(self.key, (), counter_a=4, counter_b=4, **self.kw), (False, 0))

    def test_collisions_and_tombstones(self):
        rows = [(self.empty, 0)] * 8
        start = identity_bucket(self.key, 8)
        rows[start] = (self.deleted, 99)
        rows[(start + 1) % 8] = (b'\x22' * 16, 8)
        rows[(start + 3) % 8] = (self.key, 0xffffffff)
        self.assertEqual(lookup_identity(self.key, rows, tombstones_enabled=True, **self.kw), (True, 0xffffffff))
        rows = [(self.empty, 0)] * 8
        rows[identity_bucket(self.deleted, 8)] = (self.deleted, 5)
        self.assertEqual(lookup_identity(self.deleted, rows, **self.kw), (True, 5))
        self.assertEqual(lookup_identity(self.deleted, rows, tombstones_enabled=True, **self.kw), (False, 0))

    def test_invalid_snapshot_bounds(self):
        for capacity in (0, 3, True):
            with self.assertRaises(ValueError):
                identity_bucket(self.key, capacity)
        with self.assertRaises(ValueError):
            lookup_identity(self.key, [(b'\x44' * 16, 0)] * 8, **self.kw)
        with self.assertRaises(ValueError):
            identity_bucket(b'short', 8)

    def test_compile_preserves_class_and_unique_dependencies(self):
        from engine.animation_identity import compile_identity
        rows = [(self.empty, 0)] * 8
        rows[identity_bucket(self.key, 8)] = (self.key, 17)
        dependencies = [4]
        for _ in range(2):
            self.assertEqual(compile_identity(self.key, rows, dependencies=dependencies, **self.kw),
                             dict(binding_class=0, value=17, error=0))
        self.assertEqual(dependencies, [4, 17])
        self.assertEqual(compile_identity(bytes(16), rows, dependencies=dependencies, **self.kw),
                         dict(binding_class=0, value=0xffffffff, error=1))
        self.assertEqual(compile_identity(b'\x77' * 16, rows, dependencies=dependencies, **self.kw),
                         dict(binding_class=0, value=0, error=1))
        self.assertEqual(dependencies, [4, 17])
