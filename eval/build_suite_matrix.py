#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).parents[1]


def build(fixtures: str, runs: int) -> tuple[dict, list[dict]]:
    if runs < 1:
        raise ValueError("runs must be positive")
    manifest = json.loads((ROOT / "eval/comparison_matrix.json").read_text())
    requested = None if fixtures == "all" else set(fixtures.split(","))
    known = {item["comparison_name"] for item in manifest["fixtures"]}
    if requested is not None and (unknown := requested - known):
        raise ValueError(f"unknown comparison fixtures: {sorted(unknown)}")

    selected = [
        item for item in manifest["fixtures"]
        if requested is None or item["comparison_name"] in requested
    ]
    include = [
        {
            "comparison_fixture": item["comparison_name"],
            "fixture": item["source_fixture"],
            "iteration": iteration,
        }
        for item in selected if item["mode"] == "model"
        for iteration in range(1, runs + 1)
    ]
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
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--structural-output", required=True, type=Path)
    args = parser.parse_args()
    matrix, structural = build(args.fixtures, args.runs)
    args.structural_output.write_text(json.dumps(structural, indent=2) + "\n")
    print(json.dumps(matrix, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
