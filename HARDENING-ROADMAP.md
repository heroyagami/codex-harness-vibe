# Harness Hardening Roadmap

This document separates **mandatory production contracts** from **future quality upgrades**. Do not weaken an existing contract merely to make a provider easier to integrate.

## P0 — production invariants

Implemented or required now:

- Scene Context Isolation Contract: fresh Worker per scene/revision, no long shared scene-generation session.
- Controller owns global understanding; Workers own local execution only.
- Neighbor continuity uses compact semantic summaries, never sibling source/history.
- Style Memory carries lessons, not complete historical layouts or source code.
- Model/provider fallback remains within the same isolated scene scope.
- Prompt/context budgets fail closed.
- Fact, timing, visibility, motion, beat, Critic and sequence gates remain independent of Worker self-report.
- State fingerprints include model/prompt contracts so stale outputs are invalidated.
- Vendor source remains read-only; Harness policy lives in controller/adapters.

## P1 — next recommended upgrades

### 1. Context Leak Detector

Add a post-authoring audit that scans generated `frame.md` and source for suspicious references to sibling paths such as `../scene-`, copied scene ids, or imported sibling artifacts. This cannot prove a model never read a file, but it catches common leakage and cloning failures.

### 2. Scene provenance manifest

For every scene, write a compact provenance record containing:

- Director contract hash;
- context-policy version;
- model/provider actually used, including fallback;
- Style Memory guidance hash;
- asset ids/licenses used;
- current prompt hash, not raw prompt;
- revision count;
- Critic score progression;
- final source/render hashes.

This makes any scene reproducible and reviewable without storing full private model transcripts.

### 3. Style Memory quality scoring

Memory should not be “recent equals good.” Rank lessons by:

- Critic score;
- zero-revision success;
- recurrence across multiple runs;
- semantic/grammar relevance;
- age/decay;
- rejection frequency after reuse.

Automatically retire stale or repeatedly harmful lessons.

### 4. Memory deduplication and anti-template cloning

Cluster highly similar lessons and keep a small canonical set. Track layout/motion signatures so repeated successful scenes do not gradually become a single dominant template.

### 5. Benchmark corpus

Maintain 5–10 fixed representative SRT/audio fixtures covering:

- legal facts;
- relationship diagrams;
- evidence/documents;
- numbers;
- conflict/reversal;
- conclusion;
- long explanatory passages.

Every major Director/Worker/Critic change should run the same corpus and compare quality, rejection rate, cost, render time and revision count.

### 6. Cross-model regression

Run selected benchmark scenes through Claude, Codex Worker and one generic adapter. The Harness contract should remain provider-neutral; quality may differ, but facts, context isolation and gates must behave consistently.

### 7. Failure taxonomy

Normalize failures into stable classes:

- provider quota/rate limit;
- context budget overflow;
- context-policy violation;
- fact violation;
- timing/beat violation;
- render/toolchain failure;
- visibility/safe-zone failure;
- motion/freeze/jitter failure;
- creative Critic rejection;
- sequence-level rejection.

Use the taxonomy for resumability and production reports instead of relying on free-form exception strings.

### 8. Adaptive revision routing

Revision should be minimal and targeted:

- factual failure -> fact revision only;
- beat/timing failure -> timing revision only;
- empty/clipped scene -> composition revision;
- weak semantics -> creative rewrite;
- sequence repetition -> re-direct selected scenes, not whole-film regeneration.

Avoid sending every problem to one generic “rewrite everything” Worker.

## P2 — quality and efficiency

### 9. Semantic cache

Cache Director/asset-selection/style-memory retrieval by semantic input hashes. Never cache final generated scene code across unrelated scenes.

### 10. Dynamic context allocation

Simple scenes should receive smaller context budgets. Complex evidence/relationship scenes may receive more current-scene research context while still respecting the same isolation boundary.

### 11. Motion signature diversity

Beyond midpoint silhouette similarity, extract per-scene motion signatures such as entry direction, dominant scale curve, number of simultaneous movers and focal-point trajectory. Reject repeated motion grammar across long runs.

### 12. Visual attention map checks

Estimate whether multiple large elements compete for attention, whether the primary subject remains visually dominant, and whether important information appears near narration anchors.

### 13. Cost-quality telemetry

Track per-role calls, elapsed time, revisions and estimated/actual cost where available. Report cost per accepted scene and cost per finished minute so stronger models can be reserved for scenes that justify them.

### 14. Memory experiment controls

Support `memory = off`, `memory = rules-only`, and `memory = retrieved-lessons` benchmark modes. This proves whether Style Memory actually improves output rather than merely increasing prompt length.

## P3 — production governance

### 15. Contract versioning

Version these independently:

- Director schema/prompt;
- Context Isolation Contract;
- Style Memory schema;
- Worker contract;
- Critic rubric;
- visual/motion/beat gates;
- platform safe-zone profile.

Each relevant version must participate in downstream fingerprints.

### 16. Reproducible production report

Final reports should state exactly which contract/model versions produced a video and whether all automated gates plus the final human fresh-eyes watch passed.

### 17. Security boundary review

For any new provider/CLI adapter, verify:

- no persistent session reuse;
- no implicit repository-wide context upload;
- current-scene working-directory scope;
- no hidden auto-agent spawning;
- no unauthorized network asset retrieval;
- explicit prompt/output file behavior;
- logs do not contain secrets or unnecessary full prompts.

## Non-goals

The Harness should not:

- force every scene into a fixed template library;
- copy a successful historical scene wholesale;
- let a Worker read the whole film just to maintain continuity;
- weaken fact or context isolation to reduce model calls;
- treat a high Critic score as a substitute for final human viewing;
- add complexity without a benchmark showing quality, reliability or cost benefit.

## Guiding principle

**Accumulate knowledge globally, execute locally, validate independently, and only reuse abstractions—not generation history.**
