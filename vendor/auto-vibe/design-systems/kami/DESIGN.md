# Design System Inspired by kami

> Category: Editorial & Print
> Brand signals: parchment canvas, ink-blue signal, serif-led hierarchy.

## 1. Essence

kami should feel like high-quality content printed on warm paper: quiet, literary, dense, and composed. The identity comes from parchment surfaces, warm neutral ink, one restrained blue accent, and serif typography carrying most of the hierarchy.

## 2. Color Roles

- **Parchment** (`#f5f4ed`): Primary canvas. Warm paper, never cold white.
- **Ivory** (`#faf9f5`): Slightly lifted paper surface when the scene needs separation.
- **Warm Sand** (`#e8e6dc`): Subtle rule, divider, or soft neutral backing.
- **Deep Paper Black** (`#141413`): Primary foreground; gentler and warmer than pure black.
- **Dark Warm** (`#3d3d3a`): Secondary foreground and quieter title support.
- **Olive** (`#504e49`): Captions, metadata, and low-emphasis prose.
- **Stone** (`#6b6a64`): Tertiary text or very quiet labels.
- **Ink Blue** (`#1B365D`): The only saturated brand accent. Use for section numbers, key words, quote rules, selected values, or a single visual signal.
- **Tag Blue Pale** (`#EEF2F7`): Soft paper-safe blue tint.
- **Dark Surface** (`#30302e`): Warm charcoal panel.

The palette stays warm and print-like. Ink Blue remains a scarce signal over paper neutrals.

## 3. Typography

- **English display / body**: `Charter`, fallback `Georgia, Palatino, "Times New Roman", serif`.
- **Simplified Chinese display / body**: `"TsangerJinKai02", "Source Han Serif SC", "Noto Serif CJK SC", "Songti SC", "STSong", Georgia, serif`.
- **Traditional Chinese display / body**: `"Source Han Serif TC", "Noto Serif CJK TC", "Songti TC", "PMingLiU", Georgia, serif`.
- **Mono**: `"JetBrains Mono", "SF Mono", "Fira Code", Consolas, Monaco, "Source Han Serif SC", monospace`.
- **Local substitutes**: use `Source Serif 4` for the Charter-like English serif via `fonts/SourceSerif4.ttf`, `Noto Serif SC` for Simplified Chinese via `fonts/NotoSerifSC.ttf`, `Noto Serif TC` for Traditional Chinese via `fonts/NotoSerifTC.ttf`, and `JetBrains Mono` via `fonts/JetBrainsMono.ttf`. These Google Fonts files are OFL-licensed and cover the practical regular-to-medium editorial weights needed for Remotion scenes.

Typography should feel serif-first and editorial. Prefer regular-to-medium serif weight, with emphasis coming from scale, placement, color, and paper-like contrast rather than heavy bold. The system should feel typeset rather than app-like.

Use Chinese serif fonts when the content is Chinese-dominant; let English fall back naturally inside the same scene. Numerals can use tabular or mono treatment when values align in columns, counters, dates, or metrics.

## 4. Visual Tendencies

- **Paper before interface**: The frame should read as printed material, letter, white paper, portfolio page, or editorial spread.
- **Serif hierarchy**: Titles, quotes, captions, and labels share the serif voice.
- **Single ink signal**: Use Ink Blue to mark one key idea, section number, metric, or quote edge.
- **Warm restraint**: Neutral colors lean cream, sand, olive, and charcoal.
- **Quiet annotation**: Pale blue tags, marginal notes, rules, and footnote-like labels fit the brand when kept subtle.
- **Dense composition**: Content can feel compact and literary, but the overall frame should remain calm and readable.
