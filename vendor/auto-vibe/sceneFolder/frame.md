# Frame

- Canvas: 1080x1440, 30fps. The scene shell supplies one crop of the shared textured background; `DefaultScene` supplies the transparent MG foreground.
- Platform UI safe area: keep faces, numbers, conclusions, logos and all essential visuals inside x=110..970, y=145..1000. Only background texture and dispensable decoration may cross it.
- Subtitle reserve: keep y=1000..1440 as background-only space; subtitle glyphs must remain inside x=110..970 and above y=1295 to avoid short-video UI overlays.
- Define the shot intent as the change in audience perception before choosing shot size or camera movement.
- Store generated cinematic plates in `public/video/`; note their trim range, centered 3:4 crop, and MG anchor below.
- When `design-system/` contains a folder, use its `DESIGN.md`; otherwise define the visual language from the scene content.
- Implement the scene in `scenes/DefaultScene.tsx` and preserve the shell in `remotion/Root.tsx`.

Preserve these frame constraints above when adding scene-specific design and motion notes below.
