# Scene Context Isolation Contract

This contract is mandatory for every scene authoring and revision Worker.

## Core rule

禁止使用单一长上下文连续生成全部镜头。每个 `scene-NNN` 必须启动独立、无历史继承的 Worker 调用。Controller 保留全片理解，Worker 只处理当前 Scene。

A retry or revision is also a new independent invocation. It may reuse the current scene files and explicit revision request, but it must not inherit another model session or another scene's conversation history.

## Allowed inputs

Each Scene Worker may receive only:

1. the Director contract for the current scene;
2. current-scene subtitles, narration facts, approved visible copy and visual goal;
3. current brand/design-system rules;
4. compact semantic summaries of the immediately previous and next scenes;
5. bounded Style Memory containing abstract lessons only;
6. authorized local asset metadata/materials selected for the current scene;
7. current-scene revision requests and current-scene technical reports.

The previous/next summaries may describe section, subject, visual goal, grammar, energy, density, reset intent and transition intent. They must not contain neighboring scene source code or full generation history.

## Forbidden inputs

A Scene Worker must not receive or read:

- another scene's complete prompt;
- another scene's `frame.md`;
- another scene's `DefaultScene.tsx` or other source code;
- another scene's artifacts, worker state or revision history;
- another Worker's conversation/tool history;
- accumulated full-run generation logs;
- a concatenation of previously generated scene outputs;
- historical Style Memory source code, full layouts or complete prompts.

The purpose is to inherit **experience and boundary intent**, not inherit **generation history**.

## Context budgets

Default production budgets are configured under `[context]`:

- `max_prompt_chars = 18000`
- `max_neighbor_summary_chars = 700` per neighboring scene summary
- `max_style_memory_chars = 3500`

Style Memory defaults to no more than two examples for a grammar. Memory records store critique lessons, not scene source code or prompts.

If an isolated scene prompt exceeds the configured production budget, the invocation must fail before the model is called. Do not solve budget overflow by adding more historical context.

## Provider requirements

- Claude Workers must use non-persistent one-shot sessions.
- Codex Workers must use ephemeral executions.
- Generic CLI Workers must consume a unique per-invocation `{prompt_file}` and must not point to a persistent conversation/session.
- Subagents are disabled for Scene Workers. The outer Harness owns orchestration.

Provider fallback does not relax this contract. A fallback attempt is a fresh invocation with the same isolated scene scope.

## Filesystem scope

The current `scene-NNN` directory is the Worker workspace. The Worker must not inspect sibling directories under `../scenes/`.

Cross-scene consistency is supplied by `fact-contract.json -> boundary_context`, not by reading neighboring scene files.

## Style Memory rules

Style Memory may store and retrieve:

- successful visual goals;
- recurring failure modes;
- Critic problems;
- concise revision lessons;
- stable brand/style rules.

Style Memory must not store or inject:

- complete `frame.md` files;
- TSX/source files;
- raw model transcripts;
- full prompts;
- full neighboring-scene descriptions;
- a reusable full-layout template copied from a prior generated scene.

Prefer reusable primitives and lessons over full-scene cloning.

## Auditability

Each fresh scene invocation writes `.harness/invocation-context.json` containing only context metadata:

- policy version;
- scene id;
- provider/model;
- prompt character count and SHA-256;
- fresh-context flag;
- confirmation that session history and sibling-scene history are not allowed.

The manifest intentionally does not duplicate the full prompt.

## Failure behavior

If the isolation contract cannot be satisfied, the Harness must fail closed rather than silently widening context. Examples:

- generic CLI lacks a per-invocation prompt file;
- prompt exceeds context budget;
- an adapter requires a persistent session;
- the requested workflow depends on reading another scene's full source/history.

## Design principle

**Global understanding lives in the Controller. Local execution lives in a fresh Worker. Cross-scene consistency travels as compact contracts, not as accumulated chat history.**
