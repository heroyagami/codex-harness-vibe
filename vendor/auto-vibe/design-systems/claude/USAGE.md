# Claude (Anthropic) Video Usage

Design package guide for Remotion scenes and video-producing agents.

## Read Order

1. Read this file first to understand the package contract.
2. Read `DESIGN.md` for visual intent, frame rules, and typography scale.
3. Use `tokens.css` as the source of truth for Remotion CSS variables.
4. Use `components.manifest.json` for the compact video component inventory; open `components.html` for visual examples.
5. Inspect `preview/` pages when checking color, type, and spacing.

## Design Highlights

- Warm parchment canvas (`#f5f4ed`) evoking premium paper, not screens
- Serif for titles, Sans for subtitles/labels, Mono for code and timestamps
- Terracotta brand accent (`#c96442`) for one clear signal per frame
- Exclusively warm-toned neutrals — every gray has a yellow-brown undertone
- Video-first type scale for 3:4 vertical readability
- Safe-area aware composition for subtitles, title cards, and information overlays

## Do

- Preserve the schema token names exactly so cross-brand switching stays reliable.
- Use `--accent` for the main visual signal, highlighted phrase, or chapter marker.
- Keep subtitles and small labels large enough for rendered video playback.
- Reuse video component groups from `components.manifest.json` before inventing new scene patterns.
- Treat `source/` files as audit notes for the bundled video fixture.

## Keep Lean

- Keep raw hex values inside token files.
- Keep Tailwind/design-token values aligned with `tokens.css`.
- Keep scene prompts focused on frames, subtitles, overlays, and timing.
- Keep each frame focused on one idea.
