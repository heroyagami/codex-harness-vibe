# Video profile migration

The Harness has a centralized `VideoProfile` abstraction for canvas dimensions, safe-zone geometry, subtitle margins and prompt wording.

## Current production profile

The current production renderer remains locked to:

- 1080 × 1440
- 30 fps
- profile: `compact_3_4`

`config.py` intentionally rejects unsupported production dimensions. This remains a fail-closed safeguard until the remaining prompt, subtitle and benchmark work is complete.

## 9:16 target

`VERTICAL_9_16_TARGET` is declared as a migration target:

- 1080 × 1920
- 30 fps
- content safe zone: x=90..990, y=180..1420
- subtitle bottom: y=1740

Declaring this target does **not** mean 1080 × 1920 is enabled for production yet.

## Machine-checkable runtime readiness

Run:

```bash
python scripts/check_video_profile.py --profile vertical_9_16
```

This command checks the low-level canvas runtime: dynamic scene/transition dimensions, background geometry and the bounded native-or-cover policy. A `ready` result means the runtime layer can represent the target profile; it does not bypass the higher-level production compatibility gate in `config.py`.

## Phase 1: runtime propagation completed

Scene and transition preparation no longer own fixed canvas constants.

Both `prepare-scenes.py` and `prepare-transitions.py` read the shared scene-plan runtime profile and propagate:

- width
- height
- fps

into generated Remotion config, metadata, transition prompts and transition specs.

Backward compatibility is preserved. Existing scene plans without `runtime_profile` resolve to:

```json
{
  "width": 1080,
  "height": 1440,
  "fps": 30
}
```

A future scene plan may transport the migration target explicitly:

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

## Phase 2: bounded native-or-cover background geometry completed

The shared backgrounds remain `1480 × 1840`, but raw source dimensions no longer need to exceed the canvas in both axes. Scene and parallax-transition runtimes now use the same anchored **native-or-cover** geometry.

The compatibility rule is important: the renderer never shrinks the existing shared texture. If the source already covers the canvas, scale remains exactly `1.0`, preserving the current 1080 × 1440 crop. Only a larger canvas may trigger the minimum required upscale.

For the 1080 × 1920 target, the existing background requires:

```text
1920 / 1840 = 1.043478...
```

or about a **4.35% upscale**. The runtime allows this because the global background-upscale ceiling is **1.10×**.

This is deliberately bounded. A background requiring more than 10% enlargement fails closed instead of silently producing soft texture or transition mismatch.

The geometry algorithm is shared by scene compositions and parallax transitions:

1. `scale = max(1, canvas_width / source_width, canvas_height / source_height)`
2. render the background at the resulting dimensions
3. compute overflow after scaling
4. apply the existing background anchor to that overflow

This preserves both the old 3:4 crop and the top-left/top-right/bottom-right/bottom-left anchor language across 3:4 and 9:16.

`render-transition-handles.mjs`, rendered-clip verification and `stage-transition.py` now also use generated runtime width/height/fps rather than remembered 1080 × 1440 constants. Scene-manifest generation and transition staging therefore share the same canvas contract.

## Asset identity vs render coverage

The legacy `scene_plan.py` still owns the identity contract for the approved light/dark shared background assets. That contract intentionally remains exact: it verifies the expected source path and the actual source-image dimensions.

Profile-specific render coverage is a separate responsibility of `runtime_profile.py`. This avoids coupling the large semantic scene-plan validator to render geometry while still keeping the selected asset deterministic and auditable.

## What is parameterized now

- scene visual-gate geometry
- safe-zone reporting
- visual-attention analysis area
- platform-safe prompt wording helper
- subtitle margin/style helper
- renderer compatibility helper
- runtime-readiness reporting
- fixed benchmark corpus
- scene workspace width/height/fps generation
- scene metadata width/height/fps generation
- transition workspace width/height/fps generation
- transition prompt/spec width/height/fps generation
- transition foreground travel scaled from canvas size
- scene background native-or-cover geometry
- parallax transition background native-or-cover geometry
- transition-handle artifact and scene-manifest width/height/fps validation
- transition staging manifest width/height/fps validation
- rendered-clip width/height/fps verification
- bounded background upscaling with a 1.10× fail-closed ceiling
- CI TypeScript checks for both scene and transition Remotion templates

## Remaining work before enabling 1080 × 1920 production

1. Replace remaining hard-coded canvas/safe-zone wording in Worker and Critic prompts with `VideoProfile.safe_zone_prompt()` or equivalent generated contracts.
2. Replace final ffmpeg subtitle `original_size` and margins with profile-derived values everywhere in the delivery path.
3. Run the fixed `benchmarks/corpus-v1` corpus through visual, motion, transition, subtitle and assembly checks for both profiles.
4. Add an explicit production-profile benchmark comparison so 9:16 must meet or beat the 3:4 baseline on quality and failure rate.
5. Only after those checks pass, relax the 1080 × 1440 production compatibility validation in `config.py`.

## Fixed regression corpus

The repository keeps six stable legal-video cases under `benchmarks/corpus-v1` covering timelines, relationships, process flows, numeric events, clause comparisons and evidence chains.

Validate it with:

```bash
python scripts/validate_benchmark_corpus.py
```

Do not replace these fixtures merely because a new Harness version performs poorly on them. They are regression anchors.
