import unittest
from engine.animation_sampling import Channel, Resource, SampleState, sample_channel


class SamplingTests(unittest.TestCase):
    def test_recursive_terminal_width_and_shared_outputs(self):
        terminal = Resource([Channel('terminal', 'payload', 32)], hashes=[1])
        middle = Resource([Channel('middle', None, 8)], 8, [1], terminal)
        first = Resource([Channel('first', None, 16)], 8, [1], middle)
        output, state, calls = [], SampleState(60), []
        def decoder(desc, payload, width, time, out, scratch):
            self.assertIs(out, output)
            self.assertIs(scratch, state)
            calls.append((desc, payload, width, time))
            out.append('decoded')
            scratch.hint, scratch.cursor = 61, 2
        self.assertEqual(sample_channel(first, 0, 1, output, state, decoder, extra_byte=7), 3)
        self.assertEqual(calls, [('terminal', 'payload', 32, 1.0)])
        self.assertEqual(output, ['decoded'])
        self.assertEqual((state.hint, state.cursor), (61, 2))

    def test_routing_rechecked_at_each_resource(self):
        last = Resource([Channel('last', None, 4)])
        middle = Resource([Channel('middle', None, 8)], 8, [0], last)
        first = Resource([Channel('first', None, 16)], 8, [1], middle)
        called = []
        hops = sample_channel(first, 0, 0, [], SampleState(0),
                              lambda desc, *args: called.append(desc))
        self.assertEqual((hops, called), (2, ['middle']))

    def test_out_of_range_first_can_route_to_valid_alternate(self):
        terminal = Resource([Channel('valid', None, 16)])
        first = Resource([], 8, [], terminal)
        self.assertEqual(sample_channel(first, 0, 0, [], SampleState(0), lambda *a: None), 2)

    def test_cycle_and_terminal_bounds_fail_before_decoder(self):
        resource = Resource([Channel('x', None, 16)], 8, [1])
        resource.alternate = resource
        def forbidden(*args):
            self.fail('decoder should not run')
        with self.assertRaisesRegex(ValueError, 'cycle'):
            sample_channel(resource, 0, 0, [], SampleState(0), forbidden)
        with self.assertRaisesRegex(ValueError, 'bounds'):
            sample_channel(Resource([]), 0, 0, [], SampleState(0), forbidden)
