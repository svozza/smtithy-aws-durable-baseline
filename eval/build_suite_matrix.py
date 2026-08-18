#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
MAX_MATRIX_JOBS = 256


def build(fixtures: str, runs: int) -> tuple[dict, list[dict]]:
    if runs < 0:
        raise ValueError("runs must be zero (matched schedule) or positive")
    manifest = json.loads((ROOT / "eval/comparison_matrix.json").read_text())
    if fixtures == "all":
        requested = None
    elif fixtures == "matched-core":
        requested = {
            item["comparison_name"] for item in manifest["fixtures"]
            if not item["comparison_name"].startswith("tool_injection_")
        }
    elif fixtures == "matched-tools":
        requested = {
            item["comparison_name"] for item in manifest["fixtures"]
            if item["comparison_name"].startswith("tool_injection_")
        }
    else:
        requested = set(fixtures.split(","))
    known = {item["comparison_name"] for item in manifest["fixtures"]}
    if requested is not None and (unknown := requested - known):
        raise ValueError(f"unknown comparison fixtures: {sorted(unknown)}")

    selected = [
        item for item in manifest["fixtures"]
        if requested is None or item["comparison_name"] in requested
    ]
    include = []
    for item in selected:
        if item["mode"] != "model":
            continue
        repetitions = runs or item["comparison_n"]
        include.extend({
            "comparison_fixture": item["comparison_name"],
            "fixture": item["source_fixture"],
            "iteration": iteration,
            "comparison_n": item["comparison_n"],
        } for iteration in range(1, repetitions + 1))
    if len(include) > MAX_MATRIX_JOBS:
        raise ValueError(
            f"suite expands to {len(include)} model jobs, above GitHub's "
            f"{MAX_MATRIX_JOBS}-job matrix limit; dispatch matched-core and "
            "matched-tools separately, or use a positive --runs override"
        )
    structural = [
        {
            "comparison_fixture": item["comparison_name"],
            "scorable": False,
            "structural_na": item["structural_na"],
            "note": item["note"],
        }
        for item in selected if item["mode"] == "structural"
    ]
    return {"include": include}, structural


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", default="all")
    parser.add_argument(
        "--runs", type=int, default=0,
        help="override repetitions per fixture; 0 uses the matched comparison schedule",
    )
    parser.add_argument("--structural-output", required=True, type=Path)
    args = parser.parse_args()
    matrix, structural = build(args.fixtures, args.runs)
    args.structural_output.write_text(json.dumps(structural, indent=2) + "\n")
    print(json.dumps(matrix, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
