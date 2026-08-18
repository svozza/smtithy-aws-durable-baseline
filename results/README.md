# AWS durable experiment results

This repository owns redacted native evidence produced by the AWS durable
Claude reviewer. Cross-arm conclusions do not live here.

Result records follow the canonical schema at:

`svozza/smtithy:src/smtithy/evals/arm_result.schema.json`

Layout:

```text
results/index.json
results/experiments/<experiment>/<cohort>.json
```

Records are append-only. A replacement names the older record in
`supersedes`; history is not rewritten. Large execution transcripts remain
GitHub Actions artifacts and are referenced by run ID and SHA-256.

See smtithy ADR 0020, "Arm repositories own native experiment results", before
adding, moving, or interpreting results.
