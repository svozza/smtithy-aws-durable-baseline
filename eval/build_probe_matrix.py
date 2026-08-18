#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).parents[1]


def build(names: str, runs: int) -> dict:
    manifest = json.loads((ROOT / "eval/tool_probes.json").read_text())
    if runs < 1:
        runs = manifest["comparison_n"]
    requested = None if names == "all" else set(names.split(","))
    known = {probe["name"] for probe in manifest["probes"]}
    if requested is not None and (unknown := requested - known):
        raise ValueError(f"unknown probes: {sorted(unknown)}")
    selected = [
        probe for probe in manifest["probes"]
        if requested is None or probe["name"] in requested
    ]
    return {"include": [
        {"probe": probe["name"], "iteration": iteration}
        for probe in selected
        for iteration in range(1, runs + 1)
    ]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probes", default="all")
    parser.add_argument("--runs", type=int, default=0)
    args = parser.parse_args()
    print(json.dumps(build(args.probes, args.runs), separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
