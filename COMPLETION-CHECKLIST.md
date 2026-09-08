# Harness completion checklist

- [x] Long-freeze and low-motion raster-jitter gates feed automatic scene rejection.
- [x] Optional word-aligned semantic beats produce three-frame timing evidence.
- [x] Optional sound-effect cues trigger final-mix audibility acceptance.
- [x] Delivery renders default to deterministic concurrency 1.
- [x] Every Scene Worker runs as a fresh independent invocation; retries/revisions do not inherit another model session.
- [x] Scene context excludes sibling prompts, `frame.md`, source code, artifacts, Worker history and accumulated run logs.
- [x] Previous/next-scene continuity is passed only through bounded semantic boundary summaries.
- [x] Style Memory is bounded and stores critique lessons rather than full historical layouts, prompts or source code.
- [x] Generic CLI scene workers require a per-invocation `{prompt_file}`; scene prompts fail before model launch when over budget.
- [x] Each scene invocation writes a context-policy manifest with prompt hash/length and fresh-context metadata.
- [ ] A full representative audio/SRT production passes every gate and is watched uninterrupted with fresh eyes.

- [x] Purchased auto-motion source is the single scene/transition/Remotion base.
- [x] Full-SRT semantic Director with exact cue coverage and grammar diversity gates.
- [x] Provider-neutral isolated Scene Workers with configurable default and fallback models.
- [x] Fact whitelist and local-frame timing audits before render.
- [x] Render visibility, clipping and subtitle-safe-area checks.
- [x] Image-capable three-frame Critic, 14/16 threshold, no-zero rule and automatic revision.
- [x] Sequence-level repeated-silhouette rejection and contact sheet.
- [x] Explicit hash-addressed state nodes and downstream invalidation.
- [x] Resumable quota handling and pre-call call/cost budgets.
- [x] Hard assembly preflight for every quality gate.
- [x] Windows dependency, Chromium, ffmpeg and directory-junction support.
- [x] One-command production entry and environment/source `doctor`.
- [x] Offline integration fixture and automated regression suite.

The reusable Harness is complete. A future full audio/SRT run is a production acceptance run for that work, not unfinished framework development.
