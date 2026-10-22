import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('image_text', Path(__file__).resolve().parents[1]/'scripts/image_text.py')
ocr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ocr)


class OfflineOCRTests(unittest.TestCase):
    def test_arguments_are_literal_and_lines_are_normalized(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root)/'image with spaces;literal.png'; path.touch()
            with patch.object(ocr.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, ' A \n\nB\n')) as run:
                result = ocr.recognize(path, executable='/fixture/tesseract')
            self.assertEqual(result['recognized_text'], ['A', 'B'])
            self.assertEqual(run.call_args.args[0], ['/fixture/tesseract', str(path.resolve()), 'stdout', '--psm', '11'])
            self.assertTrue(run.call_args.kwargs['check'])
            self.assertEqual(run.call_args.kwargs['timeout'], 8)

    def test_failure_and_timeout_are_not_empty_success(self):
        with tempfile.NamedTemporaryFile() as image:
            for error in (subprocess.TimeoutExpired('ocr', 8), subprocess.CalledProcessError(1, 'ocr')):
                with self.subTest(error=type(error)), patch.object(ocr.subprocess, 'run', side_effect=error):
                    with self.assertRaises(type(error)):
                        ocr.recognize(image.name, executable='/fixture/tesseract')

    def test_invalid_deadline_does_not_start_process(self):
        with tempfile.NamedTemporaryFile() as image, patch.object(ocr.subprocess, 'run') as run:
            for timeout in (0, -1, 31, float('nan')):
                with self.assertRaises(ValueError):
                    ocr.recognize(image.name, timeout=timeout)
            run.assert_not_called()
