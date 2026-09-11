# Production Observability and Benchmarking

This layer answers a simple question: **did a Harness change make production better, or merely different?**

## Scene provenance

Every `build_production_report(run_dir)` call now rebuilds `reports/scene-provenance.json` and each scene's `artifacts/provenance.json`.

The manifest records hashes and compact metadata only. It does not duplicate raw model prompts or conversation transcripts.

Tracked fields include:

- Director/fact contract hash;
- Context Isolation policy version and prompt hash;
- model/provider calls scoped to the scene;
- Style Memory guidance hash;
- revision-call count;
- Critic verdict, total and rubric scores;
- scene state nodes;
- frame/source/render hashes.

## Failure taxonomy

Failed model calls are normalized into stable categories such as:

- `provider_quota`;
- `provider_timeout`;
- `context_budget`;
- `context_policy`;
- `fact_violation`;
- `timing_violation`;
- `render_toolchain`;
- `visibility_safe_zone`;
- `motion_quality`;
- `creative_rejection`;
- `sequence_rejection`.

This makes reports comparable across providers and across time instead of grouping failures by free-form exception text.

## Benchmark two or more runs

First rebuild production reports for each run if necessary, then execute:

```bash
python scripts/benchmark_runs.py path/to/run-a path/to/run-b --output benchmark-report.json
```

The benchmark compares:

- completion and sequence-review status;
- model calls and failure rate;
- agent time;
- estimated cost;
- revision calls per scene;
- average/minimum Critic score;
- Director rhythm indicators.

The report also identifies the completed run with the highest Critic average, lowest revision rate, lowest failure rate and lowest estimated cost.

## Rule for future Harness changes

Any substantial Director, Worker, Critic, Memory or motion-policy change should be evaluated against the same representative runs/fixtures. Do not accept a more complex implementation merely because it appears conceptually stronger; require measurable quality, reliability or cost improvement.
