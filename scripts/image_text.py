"""Bounded offline OCR for testbench captures; never captures or sends input."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time


def recognize(image, *, timeout=8, executable=None):
    image = Path(image).resolve(strict=True)
    if not image.is_file():
        raise ValueError('OCR input must be a file')
    if not 0 < timeout <= 30:
        raise ValueError('OCR timeout must be within (0, 30] seconds')
    executable = executable or shutil.which('tesseract')
    if not executable:
        raise RuntimeError('Tesseract executable is required')
    start = time.monotonic()
    result = subprocess.run([str(executable), str(image), 'stdout', '--psm', '11'],
                            capture_output=True, text=True, timeout=timeout, check=True)
    return {'ocr_backend': 'tesseract', 'ocr_seconds': time.monotonic() - start,
            'recognized_text': [line.strip() for line in result.stdout.splitlines() if line.strip()]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('--timeout', type=float, default=8)
    args = parser.parse_args()
    print(json.dumps(recognize(args.image, timeout=args.timeout)))
