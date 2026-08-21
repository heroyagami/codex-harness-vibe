# Design System Inspired by OpenCode

> Category: AI & LLM
> Brand signals: warm dark canvas, mono type, sparse system-color signals.

## 1. Essence

OpenCode should feel like a refined terminal session for an AI coding agent: quiet, technical, open source, and code-first. The identity comes from a warm near-black background, warm off-white text, and a single monospace voice across display, body, labels, and code.

## 2. Color Roles

- **OpenCode Dark** (`#201d1d`): Primary background and strongest brand anchor; a warm near-black with a subtle reddish-brown cast.
- **Dark Surface** (`#302c2c`): Slightly lifted dark surface for terminal panes, code blocks, or layered technical moments.
- **OpenCode Light** (`#fdfcfc`): Primary foreground on dark backgrounds; warm off-white rather than pure white.
- **Soft Light** (`#c8c6c4`): Secondary foreground on dark surfaces.
- **Warm Gray** (`#9a9898`): Muted labels, secondary text, quiet metadata, and subdued terminal chrome.
- **Warm Border** (`#464343`): Thin structural lines, terminal frames, dividers, and code-panel boundaries.
- **Accent Blue** (`#007aff`): Occasional command highlight, link, cursor state, selected token, or informational signal.
- **Success Green** (`#30d158`): Completed command, passing check, positive system response.
- **Warning Orange** (`#ff9f0a`): Caution, pending operation, or warning state.
- **Danger Red** (`#ff3b30`): Error, failed command, destructive state, or blocked status.

The palette should stay mostly dark, warm, and monochrome. Blue, green, orange, and red are system signals, not decorative colors.

## 3. Typography

- **Universal / display / body / mono**: `Berkeley Mono`.
- **Local substitute**: `IBM Plex Mono` (Google Fonts / OFL) for actual Remotion loading; use `fonts/IBMPlexMono-Regular.ttf`, `fonts/IBMPlexMono-Medium.ttf`, and `fonts/IBMPlexMono-Bold.ttf`.
- **Fallbacks**: `ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace`.

OpenCode has one typographic voice: everything feels like code. Use the same monospace family for headlines, prompts, output, labels, file paths, and numbers. Hierarchy should come from contrast, alignment, density, and selective weight rather than switching fonts.

Favor medium and bold moments for commands, filenames, status labels, and short headlines. Keep body text compact and technical. Numerals, paths, flags, command prefixes, and shell-like fragments should align cleanly and can carry much of the visual rhythm.

## 4. Visual Tendencies

- **Terminal first**: CLI prompts, command output, logs, diffs, stack traces, file trees, and code fragments are natural visual material.
- **Warm dark mood**: The dark field feels slightly brown and tactile.
- **Single mono voice**: One monospace family carries headlines, labels, prose, and code.
- **Flat technical surfaces**: Prefer flat panels, tonal separation, and thin borders over glossy depth.
- **Sparse system signals**: Blue, green, orange, and red should map to technical state and appear in small amounts.
- **Text as interface**: Let punctuation, brackets, cursors, ASCII shapes, status chips, and terminal rhythm create the composition.
- **Utilitarian geometry**: Corners and frames should feel sharp, practical, and compact rather than soft or playful.
- **Open-source restraint**: The overall feel should be direct, developer-native, and unpolished in a deliberate way.
