# Transition Frame

- Canvas: 1080x1440 at 30fps.
- `public/input/` contains the shared textured background, outgoing/incoming composites, and transparent foreground layers.
- Frame 0 reconstructs the outgoing composite; the final frame reconstructs the incoming composite.
- Camera motion is continuous, with a larger apparent displacement for the foreground than the background.
- The timeline, endpoint compositions, anchor direction, and 3:1 motion ratio are fixed; preserve their continuity while rendering and validating the clip.
