"""Runner guard and cleanup checks; these do not launch Wine or a game."""
import importlib.util
from pathlib import Path
import signal
import subprocess
import tempfile
import sys
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('late_load_runner', Path(__file__).resolve().parents[1]/'scripts/run_late_load.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class LateLoadRunnerTests(unittest.TestCase):
    def test_action_observer_missing_private_collector_fails_before_launch(self):
        for plan in ('action-observe', 'composite-observe', 'source-observe', 'chain-observe'):
            with self.subTest(plan=plan), tempfile.TemporaryDirectory() as tmp:
                with patch.object(sys, 'argv', ['runner', '--workspace', tmp,
                                  '--experiment', 'host', '--plan', plan, '--check']):
                    with patch.object(runner, 'preflight', return_value='/compiler'):
                        with self.assertRaisesRegex(RuntimeError, 'Private action observer'):
                            runner.main()
                self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_startup_probe_combination_refused_before_launch(self):
        with patch.object(sys, 'argv', ['runner', '--load-at', 'startup']):
            with self.assertRaisesRegex(RuntimeError, 'requires --experiment host'):
                runner.main()

    def test_native_navigator_requires_startup_load(self):
        with patch.object(sys, 'argv', ['runner', '--experiment', 'host', '--navigator', 'native']):
            with self.assertRaisesRegex(RuntimeError, 'requires --load-at startup'):
                runner.main()

    def test_startup_missing_workspace_reports_prerequisites(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(sys, 'argv', ['runner', '--workspace', tmp, '--experiment', 'host', '--load-at', 'startup', '--check']):
                with self.assertRaisesRegex(RuntimeError, 'Missing prerequisites'):
                    runner.main()
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_missing_workspace_fails_without_creating_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(RuntimeError, 'Missing prerequisites'):
                runner.preflight(root)
            self.assertEqual(list(root.iterdir()), [])

    def test_replacement_dll_is_refused_and_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in runner.REQUIRED:
                p = root/name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b'synthetic fixture')
            dll = root/'XINPUT1_3.dll'
            with patch.object(runner.shutil, 'which', return_value='/compiler'):
                with self.assertRaisesRegex(RuntimeError, 'hash differs'):
                    runner.preflight(root)
            self.assertEqual(dll.read_bytes(), b'synthetic fixture')

    def test_host_experiment_requires_private_adapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in runner.REQUIRED:
                p = root/name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b'synthetic fixture')
            with patch.object(runner.shutil, 'which', return_value='/compiler'):
                with self.assertRaisesRegex(RuntimeError, 'steep_adapter.c'):
                    runner.preflight(root, 'host')

    def test_watchdog_exit_aborts_pending_stage(self):
        child = Mock(); child.poll.return_value = None
        watchdog = Mock(); watchdog.poll.return_value = 0
        with self.assertRaisesRegex(RuntimeError, 'watchdog stopped'):
            runner.wait_stage(child, watchdog, 30)

    def test_failed_probe_is_not_success(self):
        child = Mock(); child.poll.return_value = 2; child.returncode = 2
        with self.assertRaisesRegex(RuntimeError, 'Stage failed'):
            runner.wait_stage(child, Mock(), 30)

    def test_finished_child_is_not_signalled(self):
        child = Mock(); child.poll.return_value = 0
        runner.stop_child(child, interrupt=True)
        child.send_signal.assert_not_called()

    def test_cleanup_first_allows_python_finally_to_run(self):
        child = Mock(); child.poll.return_value = None
        runner.stop_child(child, interrupt=True)
        child.send_signal.assert_called_once_with(signal.SIGINT)
        child.wait.assert_called_once_with(timeout=20)

    def test_timeout_kills_only_owned_process_group(self):
        child = Mock(); child.pid = 12345; child.poll.return_value = None
        child.wait.side_effect = [subprocess.TimeoutExpired('owned fixture', 20), 0]
        with patch.object(runner.os, 'killpg') as kill:
            runner.stop_child(child, interrupt=True)
        kill.assert_called_once_with(12345, signal.SIGKILL)


if __name__ == '__main__':
    unittest.main()


class IntelRuntimeTests(unittest.TestCase):
    def test_broken_translation_fails_preflight(self):
        with patch.object(runner.sys,'platform','darwin'), patch.object(runner.platform,'machine',return_value='arm64'), patch.object(runner.subprocess,'run',return_value=Mock(returncode=1,stderr='Bad CPU type')) as run:
            with self.assertRaisesRegex(RuntimeError,'requires working Rosetta'):
                runner.check_intel_runtime()
            self.assertEqual(run.call_args.args[0],['/usr/bin/arch','-x86_64','/usr/bin/true'])

    def test_working_translation_passes(self):
        with patch.object(runner.sys,'platform','darwin'), patch.object(runner.platform,'machine',return_value='arm64'), patch.object(runner.subprocess,'run',return_value=Mock(returncode=0)):
            runner.check_intel_runtime()

    def test_intel_mac_does_not_need_translation(self):
        with patch.object(runner.sys,'platform','darwin'), patch.object(runner.platform,'machine',return_value='x86_64'), patch.object(runner.subprocess,'run') as run:
            runner.check_intel_runtime();run.assert_not_called()
