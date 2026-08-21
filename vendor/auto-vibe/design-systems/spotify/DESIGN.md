# Spotify Visual Style Reference

> Category: Media & Consumer
> Music streaming: near-black immersion, vivid green accents, bold compact type, album-art color.

## Core Look

Spotify should feel like a dark stage for audio content. Use near-black charcoal surfaces so text, cover art, and the Spotify green accent become the brightest signals. The interface voice is compact, rounded, and direct rather than editorial or decorative.

The palette is intentionally narrow. Most of the frame should live in black, charcoal, white, and muted silver. Let album art or media thumbnails provide secondary color; do not invent a broad decorative palette.

## Color Roles

- **Background**: `#121212` for the deepest canvas.
- **Surface**: `#181818`, `#1f1f1f`, `#252525`, `#272727` for layered dark panels.
- **Primary text**: `#ffffff` or `#fdfdfd`.
- **Muted text**: `#b3b3b3` and `#cbcbcb`.
- **Accent**: Spotify green `#1ed760`; older green variant `#1db954` can appear as a secondary brand green.
- **Borders and separators**: `#4d4d4d`, `#7c7c7c`, or muted silver on dark surfaces.

## Typography

- **Display / title**: `SpotifyMixUITitle`.
- **Body / UI**: `SpotifyMixUI`.
- **Local substitute**: use `Manrope` for `SpotifyMixUITitle` and `SpotifyMixUI` via `fonts/Manrope.ttf`. This Google Fonts file is OFL-licensed and covers the practical 400 / 600 / 700 weights needed for Remotion scenes.
- Use a strong title/body contrast: bold titles and compact labels against regular supporting text.
- Labels can be uppercase with slightly open tracking.
- Keep text dense and functional; this style is closer to a music app than a magazine.

## Visual Traits

- Prefer pill and circle geometry for play symbols, avatars, and active indicators.
- Use rounded dark surfaces.
- Green marks playback and active state.
- Use high-contrast white text for primary phrases and muted silver for secondary metadata.
- Album art, playlist covers, and artist imagery are the main color source. The surrounding system should stay mostly achromatic.
- Depth comes from darker surfaces and selective dark separation.
