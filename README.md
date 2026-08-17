# AWS durable Claude reviewer baseline

Evaluation harness for the Claude reviewer in
`aws/aws-durable-execution-ci@51823b4b37af88c9d2b6afd4d3714ff3970bc8a2`.

The repository vendors only the pinned workflow inputs and trusted scripts.
Fixtures remain canonical in `svozza/smtithy`; every workflow run requires an
exact fixture-source commit and records source/adapted byte hashes.

Run deterministic tests with:

```bash
python3 -m unittest discover -s tests -v
```
