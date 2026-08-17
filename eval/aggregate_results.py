#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def aggregate(root: Path) -> dict:
    cells = []
    seen: set[tuple[str, int]] = set()
    for record_path in sorted(root.glob("**/eval-record/run-record.json")):
        record = json.loads(record_path.read_text())
        key = (record["comparison_fixture"], record["run_index"])
        if key in seen:
            raise ValueError(f"duplicate result cell: {key}")
        seen.add(key)
        artifact = record_path.parents[1]
        result_dir = artifact / "result"
        sample_path = result_dir / "sample.json"
        if not sample_path.exists():
            raise ValueError(f"missing sample result for {key}")
        sample = json.loads(sample_path.read_text())
        cell = {**key_to_dict(key), "source_fixture": record["fixture"], **sample}
        grade_path = result_dir / "grade.json"
        if grade_path.exists():
            cell["grade"] = json.loads(grade_path.read_text())
        cells.append(cell)

    structural = []
    for path in sorted(root.glob("**/structural-results.json")):
        structural.extend(json.loads(path.read_text()))

    scored = [cell for cell in cells if cell["scorable"]]
    excluded = [cell for cell in cells if not cell["scorable"]]
    matched = missed = clean = 0
    for cell in scored:
        defects = cell.get("grade", {}).get("review", {}).get("defects", [])
        if not defects:
            clean += 1
        elif all(item["matched"] for item in defects):
            matched += 1
        else:
            missed += 1
    return {
        "summary": {
            "model_cells": len(cells),
            "scored": len(scored),
            "excluded": len(excluded),
            "structural": len(structural),
            "defect_cells_matched": matched,
            "defect_cells_missed": missed,
            "clean_cells_scored": clean,
        },
        "cells": cells,
        "structural": structural,
    }


def key_to_dict(key: tuple[str, int]) -> dict:
    return {"comparison_fixture": key[0], "run_index": key[1]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = aggregate(args.artifacts)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
