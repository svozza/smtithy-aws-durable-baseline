import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "eval"))


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


adapter = load("fixture_adapter", ROOT / "eval/fixture_adapter.py")
runner = load("run_aws_durable_eval", ROOT / "eval/run_aws_durable_eval.py")
grader = load("grade_aws_durable_eval", ROOT / "eval/grade_aws_durable_eval.py")


class HarnessTests(unittest.TestCase):
    def test_upstream_snapshot_hashes(self):
        runner.verify_upstream()

    def test_adapter_preserves_diff_bytes(self):
        source = ROOT.parent / "smtithy-aws-fixtures"
        if not source.exists():
            self.skipTest("sibling fixture source is unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "fixture"
            record = adapter.adapt(source, "subtle_timing_vuln", output, "a" * 40)
            original = source / "src/smtithy/evals/scenarios/subtle_timing_vuln/context/diff.patch"
            self.assertEqual(
                original.read_bytes(),
                (output / ".ai-review-context/pr.diff").read_bytes(),
            )
            self.assertEqual(record["fixture_source_sha"], "a" * 40)

    def test_extract_requires_exactly_one_native_result(self):
        review = {"summary": "No findings.", "comments": []}
        self.assertEqual(runner.extract_review([{"type": "result", "structured_output": review}]), review)
        with self.assertRaises(ValueError):
            runner.extract_review([])
        with self.assertRaises(ValueError):
            runner.extract_review([
                {"type": "result", "structured_output": review},
                {"type": "result", "structured_output": review},
            ])

    def test_grader_matches_exact_useful_work(self):
        fixture = {
            "defects": [{"path": "app/tokens.py", "line": 8, "diagnosis": ["constant-time"]}]
        }
        review = {
            "summary": "Found a timing issue.",
            "comments": [{
                "path": "app/tokens.py", "start_line": 8, "line": 8,
                "body": "Use a constant-time comparison.", "has_suggestion": False, "suggestion": "",
            }],
        }
        result = grader.grade(review, fixture)
        self.assertTrue(result["review"]["defects"][0]["matched"])


if __name__ == "__main__":
    unittest.main()
