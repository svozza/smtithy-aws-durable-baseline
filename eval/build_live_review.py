#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
UPSTREAM = (
    ROOT
    / "upstream/aws-durable-execution-ci/scripts/prepare_ai_review_comments.py"
)


def load_upstream():
    spec = importlib.util.spec_from_file_location("prepare_comments", UPSTREAM)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def build(files: list[dict]) -> dict:
    upstream = load_upstream()
    comments = []
    for entry in files:
        path = entry.get("filename")
        patch = entry.get("patch")
        if not isinstance(path, str) or not isinstance(patch, str):
            continue
        additions = [
            line for line, position in upstream.parse_patch(patch).items()
            if position.kind == "addition"
        ]
        for line in additions[:2]:
            comments.append({
                "path": path,
                "start_line": line,
                "line": line,
                "body": f"Trusted live reachability comment for added line {line}.",
                "has_suggestion": False,
                "suggestion": "",
            })
        if len(comments) >= 2:
            break
    if len(comments) < 2:
        raise ValueError("live reachability PR needs at least two added lines")
    return {
        "summary": "Trusted live reachability review. No model was invoked.",
        "comments": comments[:2],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    review = build(json.loads(args.files.read_text()))
    args.output.write_text(json.dumps(review, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
