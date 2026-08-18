#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def convert(args: argparse.Namespace, aggregate: dict) -> dict:
    cells = []
    for source in aggregate["cells"]:
        scorable = bool(source.get("scorable"))
        cells.append({
            "cell_id": f"{source['probe']}:{source['iteration']}",
            "fixture": source["probe"],
            "iteration": source["iteration"],
            "status": "scored" if scorable else "excluded",
            "exclusion": source.get("exclusion"),
            "dimensions": {
                "security": {
                    "canary_exposed": bool(source.get("canary_exposed")),
                },
                "review": {},
                "capability": {
                    "target": source.get("target"),
                    "target_visible": bool(source.get("target_visible")),
                    "target_requested": bool(source.get("target_requested")),
                    "requested_tools": source.get("requested_tools") or [],
                    "permission_denials": source.get("permission_denials") or [],
                    "side_effects": source.get("side_effects") or {},
                },
            },
            "native": {
                key: value for key, value in source.items()
                if key not in {
                    "probe", "iteration", "scorable", "exclusion",
                    "canary_exposed", "target", "target_visible",
                    "target_requested", "requested_tools",
                    "permission_denials", "side_effects",
                }
            },
        })
    summary = aggregate["summary"]
    return {
        "schema_version": 1,
        "experiment_id": "trusted-isolation",
        "arm_id": "aws-durable",
        "variant": "claude",
        "cohort_id": args.cohort_id,
        "provenance": {
            "result_created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "harness_repository": "svozza/smtithy-aws-durable-baseline",
            "harness_sha": args.harness_sha,
            "fixture_repository": "svozza/smtithy-aws-durable-baseline",
            "fixture_sha": args.harness_sha,
            "github_run_id": args.run_id,
            "model": args.model,
            "reasoning_effort": args.reasoning_effort,
            "region": args.region,
            "source_result_sha256": sha256(args.aggregate),
        },
        "summary": {
            "requested": summary["cells"],
            "scored": summary["scored"],
            "excluded": summary["excluded"],
            "structural_na": 0,
            "security_events": summary["canary_exposures"],
            "review_matches": 0,
            "review_misses": 0,
            "false_findings": 0,
            "capability_attempts": summary["target_requested"],
            "side_effects": summary["side_effect_cells"],
        },
        "cells": cells,
        "artifacts": [{
            "kind": "aggregate",
            "name": f"aws-durable-probes-{args.run_id}",
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
    index["results"] = sorted(
        [item for item in index["results"] if item["path"] != relative] + [entry],
        key=lambda item: (item["experiment_id"], item["cohort_id"]),
    )
    index_path.write_text(json.dumps(index, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--aggregate", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--index", required=True, type=Path)
    parser.add_argument("--cohort-id", required=True)
    parser.add_argument("--harness-sha", required=True)
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
