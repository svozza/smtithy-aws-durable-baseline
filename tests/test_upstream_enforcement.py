import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "upstream/aws-durable-execution-ci/scripts/prepare_ai_review_comments.py"
spec = importlib.util.spec_from_file_location("prepare_comments", SCRIPT)
comments = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(comments)

FILES = [{"filename": "app.py", "patch": "@@ -1,2 +1,3 @@\n old\n+added\n context"}]
VALID = {
    "summary": "Review summary.",
    "comments": [{
        "path": "app.py", "start_line": 2, "line": 2, "body": "Finding.",
        "has_suggestion": False, "suggestion": "",
    }],
}


class EnforcementTests(unittest.TestCase):
    def prepare(self, review):
        return comments.prepare_review(review, FILES, "claude", "1", "1", "a" * 40)

    def test_valid_comment_is_commit_bound(self):
        prepared = self.prepare(VALID)
        self.assertEqual(prepared["comments"][0]["commit_id"], "a" * 40)

    def test_unknown_path_rejected(self):
        review = {**VALID, "comments": [{**VALID["comments"][0], "path": "other.py"}]}
        with self.assertRaises(comments.ReviewValidationError):
            self.prepare(review)

    def test_unchanged_only_range_rejected(self):
        review = {**VALID, "comments": [{**VALID["comments"][0], "start_line": 1, "line": 1}]}
        with self.assertRaises(comments.ReviewValidationError):
            self.prepare(review)

    def test_extra_field_rejected(self):
        with self.assertRaises(comments.ReviewValidationError):
            self.prepare({**VALID, "extra": True})

    def test_active_markdown_and_secret_are_accepted(self):
        review = {
            "summary": "Ping @maintainer and visit [audit](https://example.invalid). SECRET-123",
            "comments": [{**VALID["comments"][0], "body": "<img src=x> user@example.com SECRET-123"}],
        }
        self.assertEqual(self.prepare(review)["summary"], review["summary"])


if __name__ == "__main__":
    unittest.main()
