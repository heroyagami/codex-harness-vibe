# Frame

- Canvas: 1080x1440, 30fps. The scene shell supplies one crop of the shared textured background; `DefaultScene` supplies the transparent MG foreground.
- Content safe area: try to keep all non-background visuals inside x=80..1000, y=100..1000.
- Subtitle reserve: keep y=1000..1440 as background-only space for subtitles.
- Define the shot intent as the change in audience perception before choosing shot size or camera movement.
- Store generated cinematic plates in `public/video/`; note their trim range, centered 3:4 crop, and MG anchor below.
- When `design-system/` contains a folder, use its `DESIGN.md`; otherwise define the visual language from the scene content.
- Implement the scene in `scenes/DefaultScene.tsx` and preserve the shell in `remotion/Root.tsx`.

Preserve these frame constraints above when adding scene-specific design and motion notes below.
