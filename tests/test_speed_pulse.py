"""Synthetic client tests. These do not establish game behavior."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('pulse_client', Path(__file__).resolve().parents[1] / 'scripts/snow_host_client.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class Host:
    def __init__(self, fail=None, held=False, resume='completed'):
        self.calls = []
        self.fail, self.held, self.resume = fail, held, resume

    def call(self, method, **params):
        self.calls.append((method, params))
        if method == self.fail:
            raise TimeoutError('synthetic lost response')
        if method == 'simulation.status':
            return {'host_paused': self.held}
        return {'synthetic': True}

    def request(self, method, **params):
        self.calls.append((method, params))
        if method == self.fail:
            raise ConnectionError('synthetic disconnect')
        return {'status': self.resume}


class SpeedPulseTests(unittest.TestCase):
    def test_signed_command_and_resume(self):
        for delta in (5, -5):
            h = Host()
            self.assertTrue(mod.speed_pulse(h, delta)['ok'])
            self.assertEqual(h.calls[2], ('player.adjust_speed', {'delta_speed': delta}))
            self.assertEqual([x[0] for x in h.calls], ['simulation.status', 'simulation.pause', 'player.adjust_speed', 'simulation.resume'])

    def test_invalid_never_contacts_host(self):
        for delta in (0, 11, -11, float('nan'), float('inf')):
            h = Host()
            with self.assertRaises(ValueError):
                mod.speed_pulse(h, delta)
            self.assertEqual(h.calls, [])

    def test_existing_hold_is_preserved(self):
        h = Host(held=True)
        self.assertFalse(mod.speed_pulse(h, 5)['ok'])
        self.assertEqual(len(h.calls), 1)

    def test_no_retry_and_resume_after_uncertain_mutation(self):
        for failure in ('simulation.pause', 'player.adjust_speed'):
            h = Host(fail=failure)
            result = mod.speed_pulse(h, 5)
            self.assertFalse(result['ok'])
            self.assertEqual(h.calls[-1][0], 'simulation.resume')
            self.assertEqual(sum(x[0] == failure for x in h.calls), 1)

    def test_failed_resume_is_failure(self):
        for h in (Host(resume='failed'), Host(fail='simulation.resume')):
            self.assertFalse(mod.speed_pulse(h, -5)['ok'])


if __name__ == '__main__':
    unittest.main()
