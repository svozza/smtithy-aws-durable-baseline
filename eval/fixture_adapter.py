#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path


class FixtureError(ValueError):
    pass


SHA_RE = re.compile(r"[0-9a-f]{40}")
REPO_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9._-]+")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_export(source: Path, name: str) -> tuple[dict, Path]:
    manifest_path = source / "src/smtithy/evals/shared_fixtures.json"
    manifest = json.loads(manifest_path.read_text())
    matches = [item for item in manifest["fixtures"] if item["name"] == name]
    if len(matches) != 1:
        raise FixtureError(f"fixture {name!r} is not exported exactly once")
    return matches[0], source / manifest["scenario_root"] / name


def materialize_base(
    scenario: Path,
    declaration_path: str,
    output: Path,
    opener=urllib.request.urlopen,
) -> dict[str, str]:
    declaration = json.loads((scenario / declaration_path).read_text())
    repo = declaration.get("repo")
    sha = declaration.get("sha")
    paths = declaration.get("paths")
    if not isinstance(repo, str) or not REPO_RE.fullmatch(repo):
        raise FixtureError(f"invalid base repository: {repo!r}")
    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
        raise FixtureError(f"base SHA must be an exact 40-character commit: {sha!r}")
    if not isinstance(paths, list) or not paths:
        raise FixtureError("base paths must be a non-empty array")

    hashes = {}
    for relative in paths:
        path = Path(relative)
        if (
            not isinstance(relative, str)
            or path.is_absolute()
            or ".." in path.parts
            or relative.startswith(".ai-review-")
        ):
            raise FixtureError(f"unsafe base path: {relative!r}")
        url = f"https://raw.githubusercontent.com/{repo}/{sha}/{relative}"
        try:
            with opener(url) as response:
                content = response.read()
        except Exception as exc:
            raise FixtureError(f"cannot fetch pinned base file {relative}: {exc}") from exc
        target = output / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        hashes[relative] = hashlib.sha256(content).hexdigest()
    return hashes


def adapt(
    source: Path,
    name: str,
    output: Path,
    source_sha: str,
    opener=urllib.request.urlopen,
) -> dict:
    fixture, scenario = load_export(source, name)
    pr_source = scenario / fixture["pr_metadata"]
    diff_source = scenario / fixture["diff"]
    original_pr = pr_source.read_bytes()
    original_diff = diff_source.read_bytes()
    pr = json.loads(original_pr)

    output.mkdir(parents=True, exist_ok=True)
    context = output / ".ai-review-context"
    if context.exists():
        raise FixtureError(f"reserved context path already exists: {context}")
    context.mkdir(parents=True)
    (output / "README.md").write_text("# AWS durable reviewer fixture\n")
    (output / "CONTRIBUTING.md").write_text("Review only the supplied pull request diff.\n")
    (context / "pr.diff").write_bytes(original_diff)
    native_pr = {
        "number": pr["number"], "title": pr["title"], "body": pr.get("body"),
        "html_url": pr.get("html_url", f"https://example.invalid/pull/{pr['number']}"),
        "draft": pr.get("draft", False), "author_association": pr.get("author_association", "NONE"),
        "additions": pr.get("additions", 0), "deletions": pr.get("deletions", 0),
        "changed_files": len(fixture["reviewed_paths"]), "user": pr.get("user", "fixture-author"),
        "base": {"ref": pr.get("base_ref", "main"), "sha": pr["base_sha"]},
        "head": {"ref": pr.get("head_ref", "fixture"), "sha": pr["head_sha"]},
    }
    (context / "pr.json").write_text(json.dumps(native_pr, ensure_ascii=False, indent=2) + "\n")

    base_hashes = {}
    if fixture["base"]:
        base_hashes = materialize_base(
            scenario, fixture["base"], output, opener=opener
        )

    record = {
        "fixture": name,
        "fixture_source_sha": source_sha,
        "source_hashes": {
            fixture["pr_metadata"]: hashlib.sha256(original_pr).hexdigest(),
            fixture["diff"]: hashlib.sha256(original_diff).hexdigest(),
        },
        "adapted_hashes": {
            ".ai-review-context/pr.diff": digest(context / "pr.diff"),
            ".ai-review-context/pr.json": digest(context / "pr.json"),
        },
        "base_hashes": base_hashes,
        "reviewed_paths": fixture["reviewed_paths"],
    }
    (output / "fixture-record.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-source", required=True, type=Path)
    parser.add_argument("--fixture-source-sha", required=True)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    adapt(args.fixture_source, args.fixture, args.output, args.fixture_source_sha)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
