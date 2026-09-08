# Architecture

The Worker seam is provider-neutral: Claude is the default, while writable Codex Workers and explicit generic CLI adapters can fill the same role.

Production quality additions:

- ffmpeg freeze detection enforces the configured 0.8-second ceiling, alongside the existing sampled-motion check.
- Low-motion 30fps windows are checked for raster oscillation; delivery rendering defaults to concurrency 1.
- Optional word timestamps bind visual beats to spoken anchors and produce before/anchor/after evidence for the Critic.
- Optional `sfx-cues.json` triggers final-mix audibility analysis; productions without sound effects report `not_applicable`.
- Style memory, licensed asset metadata and model-call metrics reuse production knowledge without cloning prior layouts.
- Scene Workers obey the mandatory [Scene Context Isolation Contract](CONTEXT-ISOLATION.md): no long shared generation session, no sibling-scene history, bounded neighbor summaries and bounded Style Memory only.

1. `direct` reads the complete SRT, asks a semantic Director for cue ranges, meaning, visual goals, grammar and approved copy, then rejects gaps, overlaps, invented copy and monotonous grammar. Director v3 also emits subject, energy, density, visual-reset, contrast and transition-intent metadata. `plan-from-director` remains the reviewed-JSON import path.
2. `director_overlay` converts those semantic decisions into production contracts. It enriches each scene fact contract with rhythm, safe-zone and compact previous/next boundary summaries, and replaces the old position-based transition cadence with semantic transition intent. Section changes and contrast default to hard cuts; rendered transitions are reserved for genuine carry/flow/temporal/settle relationships.
3. `prepare` creates isolated Remotion projects and transition workspaces, assigns a design system, shared background and Windows dependency junction. Style Memory is reduced to bounded abstract guidance rather than historical source/layout injection.
4. `run-scenes` launches every Scene Worker as a fresh provider invocation. Claude uses non-persistent one-shot sessions, Codex uses ephemeral execution, and generic CLI workers must consume a per-invocation prompt file. The adapter injects the Context Isolation Contract before the task prompt.
5. Each Worker designs `frame.md` and authors code for only the current scene, then rendering is blocked until fact and local-frame audits pass. Workers must not read sibling `../scenes/scene-*` prompts, code, artifacts or generation history.
6. Rendering is followed by technical verification, a configured safe-zone visibility/edge gate and an eight-category visual Critic.
7. A rejected creative review starts a new isolated revision invocation, rewrites only the current scene, repeats fact/timing audits, renders again and is scored again within a bounded revision budget.
8. `review` builds the sequence contact sheet, reports missing/deferred work and evaluates the Director's whole-film energy, density, grammar and visual-reset curves. A video can therefore fail sequence review even when every isolated scene passed.
9. `run-transitions` stages read-only boundary artifacts and renders only semantically planned non-hard-cut transitions.
10. `assemble` first requires every scene to pass fact, timing, visibility and Critic gates plus sequence review, follows the exact frame ledger, then adds narration and bottom-safe subtitles.

Global understanding stays with the Controller. A Scene Worker receives only its current-scene contract, current subtitles/facts, brand/design rules, compact boundary summaries, bounded Style Memory and current authorized assets. It does not receive another scene's full prompt, `frame.md`, source code, artifacts, Worker conversation history or accumulated run logs.

Temporary Worker quota failures are first-class resumable states. The controller stops launching queued work after a quota error instead of converting an external limit into repeated failed generations. Resuming or falling back still creates a fresh isolated provider invocation.

## Control plane

- `harness.toml` routes Director, scene author, revision author, transition author and visual Critic independently. Empty model names inherit the provider's configured default; a fallback model is attempted once after a retryable or command failure.
- `[context]` owns Scene Worker isolation and context budgets. Prompt overflow fails before the model is called; the Harness must not solve overflow by appending more historical context.
- `harness.toml` also owns the video profile and platform safe zone. The visual gate reads those values instead of maintaining a second hard-coded geometry definition.
- Director prompt/schema versions are part of the directed-state fingerprint. Updating the Director contract therefore invalidates stale downstream work instead of silently reusing an old scene plan.
- `harness-state.json` and per-scene `scene-state.json` form a hash-addressed dependency graph. Nodes record their input and output fingerprints so changed narration, subtitles, prompts, models or authored code invalidate only downstream work.
- Each scene invocation writes `.harness/invocation-context.json` with policy/version/provider/prompt-hash metadata, proving fresh-context scope without duplicating the full prompt.
- The usage ledger reserves a model call before launch. Call-count budgets always work; dollar budgets require explicit per-role estimates and therefore cannot silently undercount.
- Visual criticism is fail-closed. Supported production providers are image-capable Codex and an explicit manual report. Disabled or image-inaccessible critics cannot pass assembly.
- The purchased upstream tree is read-only. Harness behavior changes are implemented in the controller/overlay layer rather than modifying `vendor/auto-vibe` directly.
