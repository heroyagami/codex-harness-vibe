# Video profile migration

The Harness now has a centralized `VideoProfile` abstraction for canvas dimensions, safe-zone geometry, subtitle margins and prompt wording.

## Current production profile

The purchased/current vendor renderer remains locked to:

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

## What is parameterized now

- scene visual-gate geometry
- safe-zone reporting
- visual-attention analysis area
- platform-safe prompt wording helper
- subtitle margin/style helper
- renderer compatibility check helper

## Remaining work before enabling 1080 × 1920

1. Migrate the Remotion root composition and purchased `sceneFolder` runtime dimensions.
2. Migrate background images/crop assumptions and transition workspaces.
3. Replace remaining hard-coded canvas/safe-zone strings in Worker/Critic prompts with `VideoProfile.safe_zone_prompt()`.
4. Replace final ffmpeg subtitle `original_size` and margins with profile-derived values.
5. Re-run visual, motion, transition, subtitle and assembly benchmark fixtures at 1080 × 1920.
6. Only then relax the renderer compatibility validation in `config.py`.

The migration should be benchmarked against the existing 1080 × 1440 profile rather than switched blindly.
