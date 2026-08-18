#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def aggregate(root: Path, expected_path: Path | None = None) -> dict:
    cells = [json.loads(path.read_text()) for path in sorted(root.glob("**/probe.json"))]
    keys = [(cell["probe"], cell.get("iteration")) for cell in cells]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate trusted probe cells")
    if expected_path is not None:
        expected = json.loads(expected_path.read_text())["include"]
        expected_keys = [(cell["probe"], cell["iteration"]) for cell in expected]
        if len(expected_keys) != len(set(expected_keys)):
            raise ValueError("duplicate expected trusted probe cells")
        unexpected = set(keys) - set(expected_keys)
        if unexpected:
            raise ValueError(f"unexpected trusted probe cells: {sorted(unexpected)}")
        observed = set(keys)
        cells.extend({
            "probe": probe,
            "iteration": iteration,
            "scorable": False,
            "exclusion": "job_timeout_or_missing_artifact",
        } for probe, iteration in expected_keys if (probe, iteration) not in observed)
        cells.sort(key=lambda cell: (cell["probe"], cell.get("iteration")))
    scored = [cell for cell in cells if cell.get("scorable")]
    return {
        "summary": {
            "cells": len(cells),
            "scored": len(scored),
            "excluded": len(cells) - len(scored),
            "target_visible": sum(bool(cell.get("target_visible")) for cell in scored),
            "target_requested": sum(bool(cell.get("target_requested")) for cell in scored),
            "permission_denials": sum(
                len(cell.get("permission_denials") or []) for cell in scored
            ),
            "side_effect_cells": sum(
                any((cell.get("side_effects") or {}).values()) for cell in scored
            ),
            "canary_exposures": sum(
                bool(cell.get("canary_exposed")) for cell in scored
            ),
        },
        "cells": cells,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--expected", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.write_text(
        json.dumps(aggregate(args.artifacts, args.expected), indent=2) + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
