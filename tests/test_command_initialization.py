import struct
import unittest

from engine.command_initialization import initialize_manager, initialize_and_publish, allocate_construct_publish


def services_for(events, failure_mask=0, clear_first=False):
    allocations = []

    def lock(storage, offset, receiver):
        events.append(('lock', offset))
        struct.pack_into('<Q', storage, offset, receiver + offset + 8)

    def container(storage, offset, zero):
        events.append(('container', offset, zero))
        storage[offset:offset+12] = bytes(12)
        if clear_first and offset == 0x150:
            struct.pack_into('<I', storage, 0x114, 128)

    def allocate(size, alignment, context):
        index = len(allocations)
        pointer = 0 if failure_mask & (1 << index) else 0x200000 + index * 0x100000
        allocations.append(size)
        events.append(('allocate', size, alignment, context))
        return pointer

    def allocation_context(size, mode, source):
        events.append(('context', size, mode, source))
        return 123

    return dict(lock=lock, container=container, allocate=allocate,
                allocation_context=allocation_context, read_allocator_source=lambda: 456,
                release_buffer=lambda b, o: events.append(('release', o)),
                clear_buffer=lambda b, o: events.append(('clear', o)))


class CommandInitializationTests(unittest.TestCase):
    def test_normal_initialization_then_publication(self):
        events = []
        storage = bytearray([0xa5] * 512)
        result = initialize_and_publish(storage, 0x100000, services=services_for(events),
                                        publish=lambda value: events.append(('publish', value)))
        self.assertEqual(result, 0x100000)
        self.assertEqual(events[-1], ('publish', result))
        self.assertEqual([e[1] for e in events if e[0] == 'allocate'], [319488, 64, 13312, 13312])
        for offset, capacity in ((0x30, 3072), (0x88, 4), (0x100, 128), (0x160, 128)):
            self.assertEqual(struct.unpack_from('<I', storage, offset+20)[0], capacity)
            self.assertEqual(storage[offset+8:offset+20], bytes(12))
            self.assertEqual(storage[offset+24], 1)
        self.assertEqual(storage[0x179:], bytes([0xa5]) * (512-0x179))
        self.assertEqual(storage[0xbc], 0)

    def test_null_allocations_preserve_distinct_ownership_initialization(self):
        storage = bytearray([0xa5] * 512)
        initialize_manager(storage, 0x100000, services=services_for([], 15))
        for offset in (0x30, 0x88, 0x100, 0x160):
            self.assertEqual(struct.unpack_from('<Q', storage, offset)[0], 0)
            self.assertEqual(struct.unpack_from('<I', storage, offset+20)[0], 0)
        self.assertEqual([storage[o+24] for o in (0x30, 0x88, 0x100, 0x160)], [0xa5, 0xa5, 1, 1])

    def test_supplied_service_can_select_existing_capacity_branch(self):
        events = []
        initialize_manager(bytearray(512), 0x100000, services=services_for(events, clear_first=True))
        self.assertIn(('clear', 0x100), events)
        self.assertNotIn(('release', 0x100), events)
        self.assertEqual([e[1] for e in events if e[0] == 'allocate'], [319488, 64, 13312])

    def test_invalid_contract_rejected_before_services(self):
        events = []
        with self.assertRaises(ValueError):
            initialize_manager(bytearray(0x178), 1, services=services_for(events))
        with self.assertRaises(ValueError):
            initialize_manager(bytearray(512), True, services=services_for(events))
        self.assertEqual(events, [])

    def test_service_exception_does_not_publish(self):
        events = []
        services = services_for(events)
        def fail(*args):
            raise RuntimeError('supplied service failed')
        services['allocate'] = fail
        with self.assertRaises(RuntimeError):
            initialize_and_publish(bytearray(512), 0x100000, services=services,
                                   publish=lambda value: events.append(('publish', value)))
        self.assertFalse(any(e[0] == 'publish' for e in events))

    def test_manager_allocation_arguments_and_constructor_return_publication(self):
        events = []
        services = dict(read_allocator_source=lambda: 77,
                        allocation_context=lambda *args: events.append(('context', args)) or 88,
                        allocate=lambda *args: events.append(('allocate', args)) or 99)
        result = allocate_construct_publish(services=services, fallback=17,
                    construct=lambda token: events.append(('construct', token)) or 100,
                    publish=lambda token: events.append(('publish', token)))
        self.assertEqual(result, 100)
        self.assertEqual(events, [('context', (384, 8, 77)), ('allocate', (384, 8, 88)),
                                  ('construct', 99), ('publish', 100)])

    def test_null_manager_allocation_skips_constructor_and_preserves_fallback(self):
        for fallback in (0, 123, 2**64-1):
            with self.subTest(fallback=fallback):
                events = []
                services = dict(read_allocator_source=lambda: 0,
                                allocation_context=lambda *args: 1, allocate=lambda *args: 0)
                result = allocate_construct_publish(services=services, fallback=fallback,
                    construct=lambda token: self.fail('null allocation must not construct'),
                    publish=events.append)
                self.assertEqual(result, fallback)
                self.assertEqual(events, [fallback])

    def test_startup_service_exception_has_no_synthetic_fallback_publication(self):
        events = []
        def fail(*args):
            raise RuntimeError('supplied allocator failed')
        services = dict(read_allocator_source=lambda: 0, allocation_context=fail, allocate=fail)
        with self.assertRaises(RuntimeError):
            allocate_construct_publish(services=services, construct=lambda value: value,
                                       publish=events.append, fallback=0)
        self.assertEqual(events, [])
