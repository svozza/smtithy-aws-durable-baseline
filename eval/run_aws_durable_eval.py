#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from fixture_adapter import adapt


ROOT = Path(__file__).parents[1]


def verify_upstream() -> None:
    manifest = json.loads((ROOT / "upstream/manifest.json").read_text())
    base = ROOT / "upstream/aws-durable-execution-ci"
    for relative, expected in manifest["files"].items():
        actual = hashlib.sha256((base / relative).read_bytes()).hexdigest()
        if actual != expected:
            raise SystemExit(f"upstream hash mismatch: {relative}")


def extract_review(execution: list[dict]) -> dict:
    reviews = [
        event["structured_output"] for event in execution
        if event.get("type") == "result" and "structured_output" in event
    ]
    if len(reviews) != 1 or set(reviews[0]) != {"comments", "summary"}:
        raise ValueError("Claude returned invalid structured review output")
    return reviews[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-source", required=True, type=Path)
    parser.add_argument("--fixture-source-sha", required=True)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--execution-file", type=Path)
    args = parser.parse_args()
    verify_upstream()
    workspace = args.output_dir / "workspace"
    record = adapt(args.fixture_source, args.fixture, workspace, args.fixture_source_sha)
    (args.output_dir / "run-record.json").write_text(json.dumps(record, indent=2) + "\n")
    if args.execution_file:
        execution = json.loads(args.execution_file.read_text())
        (args.output_dir / "claude-execution.json").write_bytes(args.execution_file.read_bytes())
        (args.output_dir / "review.json").write_text(json.dumps(extract_review(execution), indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
