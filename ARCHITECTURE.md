# Architecture

1. `direct` reads the complete SRT, asks a semantic Director for cue ranges, meaning, visual goals, grammar and approved copy, then rejects gaps, overlaps, invented copy and monotonous grammar. `plan-from-director` remains the reviewed-JSON import path.
2. `prepare` creates isolated Remotion projects and transition workspaces, assigns a design system, shared background and Windows dependency junction.
3. `run-scenes` asks each Worker to design `frame.md` and author code, then blocks rendering until fact and local-frame audits pass.
4. Rendering is followed by technical verification, a three-frame visibility/edge gate and an eight-category visual Critic.
5. A rejected creative review rewrites the scene, repeats fact/timing audits, renders again and is scored again within a bounded revision budget.
6. `review` builds the sequence contact sheet and reports missing/deferred work.
7. `run-transitions` stages read-only boundary artifacts and renders only planned non-hard-cut transitions.
8. `assemble` first requires every scene to pass fact, timing, visibility and Critic gates, follows the exact frame ledger, then adds narration and bottom-safe subtitles.

Global understanding stays with the controller. A scene Worker receives only its SRT range, research brief, approved copy, design system and boundary contract.

Temporary Worker quota failures are first-class resumable states. The controller stops launching queued work after a quota error instead of converting an external limit into repeated failed generations.

## Control plane

- `harness.toml` routes Director, scene author, revision author, transition author and visual Critic independently. Empty model names inherit the provider's configured default; a fallback model is attempted once after a retryable or command failure.
- `harness-state.json` and per-scene `scene-state.json` form a hash-addressed dependency graph. Nodes record their input and output fingerprints so changed narration, subtitles, prompts, models or authored code invalidate only downstream work.
- The usage ledger reserves a model call before launch. Call-count budgets always work; dollar budgets require explicit per-role estimates and therefore cannot silently undercount.
- Visual criticism is fail-closed. Supported production providers are image-capable Codex and an explicit manual report. Disabled or image-inaccessible critics cannot pass assembly.
- The purchased upstream tree is read-only. `doctor` permits only the registered Windows browser-cache and shared-dependency overrides in `vendor/auto-vibe`.
