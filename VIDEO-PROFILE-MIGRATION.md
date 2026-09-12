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

## Runtime propagation phase completed

Scene and transition preparation no longer own fixed canvas constants.

Both `prepare-scenes.py` and `prepare-transitions.py` now read a shared scene-plan runtime profile and propagate:

- width
- height
- fps

into generated Remotion config, metadata, transition prompts and transition specs.

Backward compatibility is preserved. Existing scene plans without `runtime_profile` resolve to the current production renderer profile:

```json
{
  "width": 1080,
  "height": 1440,
  "fps": 30
}
```

A future scene plan may transport a profile explicitly:

```json
{
  "fps": 30,
  "runtime_profile": {
    "width": 1080,
    "height": 1920,
    "fps": 30
  }
}
```

This transport layer does not enable that profile for production. Existing higher-level renderer compatibility gates remain unchanged.

## Remaining verified 9:16 blocker

The current shared backgrounds are `1480 × 1840`, which is shorter than the target 1920-pixel canvas. Runtime preparation now validates background coverage against the transported profile and fails closed when the background cannot cover the canvas.

The legacy `scene_plan.py` background/theme contract also still assumes the current shared background assets. Native 9:16 background assets and the corresponding scene-plan background contract must therefore migrate before 1080 × 1920 can be enabled.

## What is parameterized now

- scene visual-gate geometry
- safe-zone reporting
- visual-attention analysis area
- platform-safe prompt wording helper
- subtitle margin/style helper
- renderer compatibility helper
- runtime-readiness reporting
- benchmark corpus used to compare production behavior before and after the migration
- scene workspace width/height/fps generation
- scene metadata width/height/fps generation
- transition workspace width/height/fps generation
- transition prompt/spec width/height/fps generation
- transition foreground travel scaled from canvas height

## Remaining work before enabling 1080 × 1920

1. Add native 9:16 shared backgrounds whose width and height cover the 1080 × 1920 canvas.
2. Migrate the legacy `scene_plan.py` background/theme contract to profile-aware background assets.
3. Migrate the Remotion root composition to consume generated dimensions everywhere it still owns layout assumptions.
4. Replace remaining hard-coded canvas/safe-zone strings in Worker/Critic prompts with `VideoProfile.safe_zone_prompt()`.
5. Replace final ffmpeg subtitle `original_size` and margins with profile-derived values.
6. Run the fixed `benchmarks/corpus-v1` corpus through visual, motion, transition, subtitle and assembly checks for both profiles.
7. Only after `check_video_profile.py --profile vertical_9_16` reports `ready`, relax renderer compatibility validation in `config.py`.

## Fixed regression corpus

The repository keeps six stable legal-video cases under `benchmarks/corpus-v1` covering timelines, relationships, process flows, numeric events, clause comparisons and evidence chains.

Validate it with:

```bash
python scripts/validate_benchmark_corpus.py
```

Do not replace these fixtures merely because a new Harness version performs poorly on them. They are regression anchors.
