# AWS durable Claude reviewer baseline

Evaluation harness for the Claude reviewer in
`aws/aws-durable-execution-ci@51823b4b37af88c9d2b6afd4d3714ff3970bc8a2`.

The repository vendors only the pinned workflow inputs and trusted scripts.
Fixtures remain canonical in `svozza/aceiro`; every workflow run requires an
exact fixture-source commit and records source/adapted byte hashes.

Run deterministic tests with:

```bash
uv sync --frozen --all-groups --no-install-project
uv run --frozen --group test python -m unittest discover -s tests -v
```

## Run the comparison suite

Dispatch **AWS durable reviewer comparison suite** with:

- `fixture-source-sha`: an exact commit from `svozza/aceiro`
- `fixtures`: `matched-prompt`, `matched-architecture`, `matched-tools`, `all`
  with a positive override, or comma-separated names from
  `eval/comparison_matrix.json`
- `runs`: `0` uses the matched comparison schedule; a positive value overrides
  every selected model-visible fixture for smoke or fixture-validation runs
- `model`: the pinned native Sonnet 5 profile by default
- `aws-region`: the region of `AWS_BEARER_TOKEN_BEDROCK`

The suite caps model concurrency at four. Each model cell uploads its source
hashes, complete Claude execution file, native review when present, grade when
scorable, and a `sample.json` classification. The final
`aws-durable-results-<run-id>` artifact combines all cells.

Result categories are independent:

- `scorable: true`: exactly one native structured result was extracted and graded.
- `scorable: false`: infrastructure/model output is excluded using the recorded
  reason, such as `error_max_structured_output_retries`.
- `structural_na`: the attack channel is unavailable in this architecture and no
  model call is made for that dimension.

Do not convert excluded samples or structural N/A cells into passes or failures,
and do not combine security, review quality, and capability results into one
rate.

The matched schedule follows the current comparison evidence:

- `N=15`: prompt/secret/detection matrices
- `N=3`: architecture-sensitive behavior fixtures
- `N=20`: each isolated tool-persuasion cell
- no model call: structural N/A cells

GitHub limits one matrix expansion to 256 jobs. Run the complete schedule
without reducing sample sizes as three dispatches:

1. `fixtures=matched-prompt`, `runs=0`
2. `fixtures=matched-architecture`, `runs=0`
3. `fixtures=matched-tools`, `runs=0`

`fixtures=all` is accepted for smoke runs with a positive `runs` override. It
fails before model spend when combined with `runs=0`, rather than silently
truncating the matched schedule.

## Run trusted isolation probes

Dispatch **AWS durable trusted isolation probes** separately from contributor
fixtures. Its default `runs=0` uses the matched `N=10` schedule for Write,
Edit, Bash/subprocess, Agent/Task, ToolSearch, Workflow, Skill, WebFetch,
WebSearch, credential-environment, credential-file, and private/workspace write
probes. The workflow uses fake canaries and records:

- observed tools, agents, skills, and workflow commands;
- requested tools and permission denials;
- workspace, private-home, and private-temp side effects;
- fake credential-canary exposure;
- pinned CLI and model versions.

These trusted prompts measure capability reachability. Do not combine their
rates with contributor-persuasion results.
