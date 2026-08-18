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
suite = load("build_suite_matrix", ROOT / "eval/build_suite_matrix.py")
aggregate = load("aggregate_results", ROOT / "eval/aggregate_results.py")


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

    def test_invalid_native_result_is_excluded_not_crashed(self):
        sample = runner.classify_execution([{
            "type": "result", "subtype": "error_max_structured_output_retries",
            "is_error": True, "num_turns": 10,
        }])
        self.assertFalse(sample["scorable"])
        self.assertEqual(sample["exclusion"], "error_max_structured_output_retries")

    def test_comparison_matrix_matches_naive_fixture_names(self):
        matrix = json.loads((ROOT / "eval/comparison_matrix.json").read_text())
        names = [item["comparison_name"] for item in matrix["fixtures"]]
        self.assertEqual(len(names), 26)
        self.assertEqual(len(names), len(set(names)))
        model_runs = {
            item["comparison_name"]: item["comparison_n"]
            for item in matrix["fixtures"] if item["mode"] == "model"
        }
        self.assertEqual(model_runs["secret_echo_in_diff"], 15)
        self.assertEqual(model_runs["forged_provenance"], 3)
        self.assertEqual(model_runs["tool_injection_write"], 20)

    def test_suite_matrix_expands_runs_and_structural_na(self):
        matrix, structural = suite.build("forged_context,subtle_vuln", 3)
        self.assertEqual(len(matrix["include"]), 3)
        self.assertEqual(matrix["include"][0]["fixture"], "subtle_timing_vuln")
        self.assertEqual(structural[0]["comparison_fixture"], "forged_context")

    def test_suite_matrix_uses_matched_per_fixture_n_by_default(self):
        matrix, _ = suite.build("fake_approval_injection,secret_echo_in_diff,tool_injection_write", 0)
        counts = {}
        for cell in matrix["include"]:
            counts[cell["comparison_fixture"]] = counts.get(cell["comparison_fixture"], 0) + 1
        self.assertEqual(counts, {
            "fake_approval_injection": 3,
            "secret_echo_in_diff": 15,
            "tool_injection_write": 20,
        })

    def test_matched_cohorts_fit_github_matrix_limit_without_lowering_n(self):
        core, core_structural = suite.build("matched-core", 0)
        tools, tool_structural = suite.build("matched-tools", 0)
        self.assertEqual(len(core["include"]), 240)
        self.assertEqual(len(tools["include"]), 100)
        self.assertEqual(len(core_structural), 1)
        self.assertEqual(tool_structural, [])
        self.assertLessEqual(len(core["include"]), suite.MAX_MATRIX_JOBS)
        self.assertLessEqual(len(tools["include"]), suite.MAX_MATRIX_JOBS)

    def test_all_matched_schedule_refuses_unrunnable_340_job_matrix(self):
        with self.assertRaisesRegex(ValueError, "matched-core and matched-tools"):
            suite.build("all", 0)

    def test_suite_skips_model_job_for_structural_only_selection(self):
        workflow = (ROOT / ".github/workflows/aws-durable-suite.yml").read_text()
        self.assertIn("model-count: ${{ steps.matrix.outputs.model-count }}", workflow)
        self.assertIn("if: needs.prepare.outputs.model-count != '0'", workflow)

    def test_aggregate_counts_scored_excluded_and_structural(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, scorable in (("good", True), ("invalid", False)):
                artifact = root / name
                (artifact / "eval-record").mkdir(parents=True)
                (artifact / "result").mkdir()
                (artifact / "eval-record/run-record.json").write_text(json.dumps({
                    "comparison_fixture": name, "run_index": 1, "fixture": name,
                }))
                (artifact / "result/sample.json").write_text(json.dumps({
                    "scorable": scorable,
                    **({} if scorable else {"exclusion": "provider_error"}),
                }))
                if scorable:
                    (artifact / "result/grade.json").write_text(json.dumps({
                        "review": {"defects": [{"matched": True}]},
                    }))
            structural = root / "structural"
            structural.mkdir()
            (structural / "structural-results.json").write_text(json.dumps([
                {"comparison_fixture": "na", "structural_na": ["write"]}
            ]))
            result = aggregate.aggregate(root)
            self.assertEqual(result["summary"]["scored"], 1)
            self.assertEqual(result["summary"]["excluded"], 1)
            self.assertEqual(result["summary"]["structural"], 1)

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
