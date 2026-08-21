# Design System Inspired by Pacman

> Category: Themed & Unique
> Brand signals: black maze space, pixel type, electric blue structure, yellow hero signal.

## 1. Essence

Pacman should feel like a playable 8-bit arcade screen: dark cabinet background, pixel typography, hard-edged color blocks, dotted paths, maze lines, score counters, and bright game-state colors. The frame stays playful, high-contrast, and clearly arcade-like.

## 2. Color Roles

- **Arcade Black** (`#050505`): Primary background and cabinet darkness.
- **Maze Surface** (`#101014`): Slightly lifted black surface for panels, score areas, or layered maze fields.
- **Cream Pixel** (`#fff7d6`): Primary foreground on dark backgrounds.
- **Pale Yellow Text** (`#f6e79c`): Secondary foreground and soft arcade lettering.
- **Pac Yellow** (`#ffcc00`): Signature hero accent for Pacman, pellets, rewards, key score moments, and the main point of attention.
- **Pac Yellow On** (`#050505`): Foreground over yellow fills.
- **Maze Blue** (`#2338ff`): Electric maze walls, hard outlines, and structural frame lines.
- **Ghost Green** (`#00ff66`): Success, bonus, extra life, or positive game state.
- **Fruit Orange** (`#ff9900`): Warning, urgency, fruit reward, or timed event.
- **Ghost Red** (`#ff3b3b`): Danger, enemy, fail state, or collision moment.

Black should dominate. Yellow and blue create the recognizable arcade identity; green, orange, and red should behave like game-state signals.

## 3. Typography

- **Display / pixel voice**: `"Press Start 2P"`, fallback `"Arial Black", system-ui, sans-serif`.
- **Body / readable support**: `Inter`, fallback `system-ui, sans-serif`.
- **Mono / score-like text**: `"Press Start 2P"`, fallback `ui-monospace, monospace`.

Actual bundled fonts: `fonts/PressStart2P-Regular.ttf` for the pixel display / mono voice, and `fonts/Inter.ttf` for readable body text. Both are open Google Fonts files.

Use pixel type for titles, score counters, labels, level text, and short callouts. Because pixel fonts are visually dense, reserve them for compact text and let simpler sans text carry longer explanations if needed.

Letterforms should feel blocky, mechanical, and game-like. All-caps labels, fixed-width scores, short words, and numeric counters fit this style better than paragraph-heavy compositions.

## 4. Visual Tendencies

- **Arcade screen logic**: Maze paths, pellets, score rows, level markers, lives, fruit icons, and enemy states are the natural motifs.
- **Pixel hardness**: Prefer square corners, stepped shapes, dotted paths, hard outlines, and crisp edges.
- **High contrast**: Cream or yellow text over black should feel luminous without becoming a soft glow theme.
- **Blue structure**: Use Maze Blue for borders, walls, tracks, and graphic scaffolding.
- **Yellow focal point**: Pac Yellow should identify the hero object, reward, pellet trail, or main callout.
- **State-color discipline**: Green means success or bonus, orange means urgency or reward event, red means danger.
- **Chunky rhythm**: Repetition, aligned dots, maze steps, and score increments can drive the scene visually.
