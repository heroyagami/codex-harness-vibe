# Video profile migration

The Harness has a centralized `VideoProfile` abstraction for canvas dimensions, safe-zone geometry, subtitle margins and prompt wording.

## Current production profile

The current vendor renderer remains locked to:

- 1080 × 1440
- 30 fps
- profile: `compact_3_4`

`config.py` intentionally rejects unsupported renderer dimensions. This remains a fail-closed production safeguard.

## 9:16 target

`VERTICAL_9_16_TARGET` is declared as a migration target:

- 1080 × 1920
- 30 fps
- content safe zone: x=90..990, y=180..1420
- subtitle bottom: y=1740

Declaring this target does **not** mean the vendor renderer is already compatible.

## Machine-checkable readiness

Run:

```bash
python scripts/check_video_profile.py --profile vertical_9_16
```

The command reports `ready` or `blocked` and lists concrete blockers. This is the required preflight before relaxing renderer validation.

As of this migration stage the 9:16 profile is intentionally blocked for three verified reasons:

1. `vendor/auto-vibe/prepare-scenes.py` still emits fixed `1080 × 1440` scene config and scene metadata.
2. `vendor/auto-vibe/prepare-transitions.py` still emits fixed `1080 × 1440` transition config and transition specs.
3. The shared backgrounds are `1480 × 1840`, which is shorter than the target 1920-pixel canvas and therefore cannot satisfy the existing background-crop contract.

The third blocker is important: changing only Remotion composition constants would produce a fake migration with an invalid background model.

## What is parameterized now

- scene visual-gate geometry
- safe-zone reporting
- visual-attention analysis area
- platform-safe prompt wording helper
- subtitle margin/style helper
- renderer compatibility helper
- runtime-readiness reporting
- benchmark corpus used to compare production behavior before and after the migration

## Remaining work before enabling 1080 × 1920

1. Add native 9:16 shared backgrounds whose width and height exceed the 1080 × 1920 canvas.
2. Pass profile width/height/fps through the scene-plan document rather than relying on vendor constants.
3. Make `prepare-scenes.py` emit scene config and metadata from the plan profile.
4. Make `prepare-transitions.py` emit transition config/specs from the same profile.
5. Migrate the Remotion root composition and transition workspace to those generated dimensions.
6. Replace remaining hard-coded canvas/safe-zone strings in Worker/Critic prompts with `VideoProfile.safe_zone_prompt()`.
7. Replace final ffmpeg subtitle `original_size` and margins with profile-derived values.
8. Run the fixed `benchmarks/corpus-v1` corpus through visual, motion, transition, subtitle and assembly checks for both profiles.
9. Only after `check_video_profile.py --profile vertical_9_16` reports `ready`, relax renderer compatibility validation in `config.py`.

## Fixed regression corpus

The repository now keeps six stable legal-video cases under `benchmarks/corpus-v1` covering timelines, relationships, process flows, numeric events, clause comparisons and evidence chains.

Validate it with:

```bash
python scripts/validate_benchmark_corpus.py
```

Do not replace these fixtures merely because a new Harness version performs poorly on them. They are regression anchors.
