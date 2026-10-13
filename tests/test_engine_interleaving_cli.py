import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class InterleavingCLITests(unittest.TestCase):
    def test_standalone_report_and_incomplete_exit_status(self):
        scenario = Path(__file__).resolve().parents[1] / 'engine/examples/interleaving_scenario.json'
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'report.json'
            command = [sys.executable, '-m', 'engine.interleavings', str(scenario), '--output', str(output)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            report = json.loads(output.read_text())
            self.assertEqual((report['nodes'],report['quiescent_leaves']), (315,96))
            result = subprocess.run(command+['--max-nodes','1'],capture_output=True,text=True)
            self.assertEqual(result.returncode,2,result.stderr)
            self.assertFalse(json.loads(output.read_text())['complete'])

    def test_rejects_overwriting_source(self):
        source = Path(__file__).resolve().parents[1] / 'engine/examples/interleaving_scenario.json'
        with tempfile.TemporaryDirectory() as directory:
            scenario = Path(directory) / 'scenario.json'
            text = source.read_text();scenario.write_text(text)
            result = subprocess.run([sys.executable,'-m','engine.interleavings',str(scenario),
                '--output',str(scenario),'--max-nodes','1'],capture_output=True,text=True)
            self.assertEqual(result.returncode,1)
            self.assertEqual(scenario.read_text(),text)
