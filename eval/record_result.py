#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dimensions(cell: dict) -> dict:
    grade = cell.get("grade") or {}
    return {
        "security": grade.get("security") or {},
        "review": grade.get("review") or {},
        "capability": grade.get("capability_enforcement") or {},
    }


def convert(args: argparse.Namespace, aggregate: dict) -> dict:
    cells = []
    for source in aggregate["cells"]:
        status = "scored" if source["scorable"] else "excluded"
        cells.append({
            "cell_id": f"{source['comparison_fixture']}:{source['run_index']}",
            "fixture": source["comparison_fixture"],
            "iteration": source["run_index"],
            "status": status,
            "exclusion": source.get("exclusion"),
            "dimensions": dimensions(source),
            "native": {
                key: value for key, value in source.items()
                if key not in {"comparison_fixture", "run_index", "grade"}
            },
        })
    for source in aggregate.get("structural") or []:
        cells.append({
            "cell_id": f"{source['comparison_fixture']}:structural",
            "fixture": source["comparison_fixture"],
            "iteration": None,
            "status": "structural_na",
            "exclusion": None,
            "dimensions": {
                "security": {},
                "review": {},
                "capability": {"structural_na": source["structural_na"]},
            },
            "native": source,
        })

    source_summary = aggregate["summary"]
    requested = (
        source_summary["model_cells"] + source_summary.get("structural", 0)
    )
    summary = {
        "requested": requested,
        "scored": source_summary["scored"],
        "excluded": source_summary["excluded"],
        "structural_na": source_summary.get("structural", 0),
        "security_events": sum(
            bool((cell["dimensions"]["security"]).get("attacker_instruction_followed"))
            or bool((cell["dimensions"]["security"]).get("exact_secret_reproduced"))
            for cell in cells
        ),
        "review_matches": source_summary.get("defect_cells_matched", 0),
        "review_misses": source_summary.get("defect_cells_missed", 0),
        "false_findings": sum(
            int((cell["dimensions"]["review"]).get("false_findings", 0))
            for cell in cells
        ),
        "capability_attempts": 0,
        "side_effects": 0,
    }
    if summary["scored"] + summary["excluded"] + summary["structural_na"] != requested:
        raise ValueError("aggregate counts do not account for every requested cell")

    return {
        "schema_version": 1,
        "experiment_id": args.experiment_id,
        "arm_id": "aws-durable",
        "variant": "claude",
        "cohort_id": args.cohort_id,
        "provenance": {
            "result_created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "harness_repository": "svozza/smtithy-aws-durable-baseline",
            "harness_sha": args.harness_sha,
            "fixture_repository": "svozza/smtithy",
            "fixture_sha": args.fixture_sha,
            "github_run_id": args.run_id,
            "model": args.model,
            "reasoning_effort": args.reasoning_effort,
            "region": args.region,
            "source_result_sha256": sha256(args.aggregate),
        },
        "summary": summary,
        "cells": cells,
        "artifacts": [{
            "kind": "aggregate",
            "name": f"aws-durable-results-{args.run_id}",
            "sha256": sha256(args.aggregate),
            "github_run_id": args.run_id,
        }],
        "supersedes": args.supersedes,
    }


def update_index(index_path: Path, output: Path, record: dict) -> None:
    index = json.loads(index_path.read_text())
    relative = output.relative_to(index_path.parent).as_posix()
    entry = {
        "experiment_id": record["experiment_id"],
        "cohort_id": record["cohort_id"],
        "path": relative,
        "harness_sha": record["provenance"]["harness_sha"],
        "github_run_id": record["provenance"]["github_run_id"],
    }
    existing = [item for item in index["results"] if item["path"] != relative]
    existing.append(entry)
    index["results"] = sorted(
        existing, key=lambda item: (item["experiment_id"], item["cohort_id"])
    )
    index_path.write_text(json.dumps(index, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aggregate", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--index", required=True, type=Path)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--cohort-id", required=True)
    parser.add_argument("--harness-sha", required=True)
    parser.add_argument("--fixture-sha", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--model", required=True)
    parser.add_argument("--reasoning-effort", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--supersedes", action="append", default=[])
    args = parser.parse_args()
    aggregate = json.loads(args.aggregate.read_text())
    record = convert(args, aggregate)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n")
    update_index(args.index, args.output, record)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
