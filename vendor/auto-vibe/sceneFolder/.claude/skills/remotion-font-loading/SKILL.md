---
name: remotion-font-loading
description: Use when a scene needs a non-system font or when touching delayRender() for typography in a Remotion composition. Prefer @remotion/fonts loadFont(), but call it from the scene component's mount useEffect() — NOT at module top level, which times out the render. Avoid brittle manual document.fonts/delayRender gates.
---

# Remotion font loading

Use this skill before adding custom fonts or any `delayRender()` related to text rendering.

Official sources:

- https://www.remotion.dev/docs/fonts
- https://www.remotion.dev/docs/fonts-api/load-font
- https://www.remotion.dev/docs/use-delay-render
- https://www.remotion.dev/docs/delay-render
- https://www.remotion.dev/docs/troubleshooting/font-loading-errors
- https://www.remotion.dev/docs/timeout

## Decision order

1. If the design system's fallback stack already looks close enough, use it and stop.
2. If you have a reliable font file, put it in `public/fonts/` and load it with `@remotion/fonts` `loadFont()` — but **call `loadFont()` from the scene component's mount `useEffect()`, not at module top level**. Module-scope `loadFont()` times out the render (see the failure mode below). Export a loader function from `remotion/load-fonts.ts` and invoke it from the component.
3. Only if `@remotion/fonts` cannot cover the case (e.g. you need to swallow a load failure and fall back gracefully instead of failing the render), use a component-scoped `useDelayRender()` with a manual `FontFace`/`document.fonts` gate inside React. Do not invent a module-scope `document.fonts.load()` gate unless there is no simpler official path.

## Common failure mode: module-scope font gate

Do not do this at module top level:

```ts
const waitForFont = delayRender("Sofia Sans");

document.fonts.load('400 16px "Sofia Sans"').then(() => {
  continueRender(waitForFont);
});
```

Why this is dangerous:

- The handle is created during module evaluation, not inside a React component render lifecycle.
- A still render may appear fine because only one frame is captured and the timing happens to line up.
- A multi-frame render can still time out on some frame with an error like `A delayRender() "..." was called but not cleared after 28000ms`.

The same failure applies to `@remotion/fonts` `loadFont()` when called at module top level: it uses the global `delayRender()` internally (no special handling), so a top-level `loadFont()` is just a module-scope `delayRender()` and times out the same way — `FontFace.load()` does not resolve in the headless render context when started during module evaluation. Always invoke `loadFont()` from inside a component's mount `useEffect()` (see the preferred pattern below).

Safe alternatives:

- Best: use `@remotion/fonts` `loadFont()`, invoked from the scene component's mount `useEffect()` (export a loader from `remotion/load-fonts.ts`); never at module top level.
- If manual waiting is unavoidable, create the handle inside a component with `useDelayRender()` or `useState(() => delayRender("font:..."))`, start the async work in `useEffect()`, and make sure every path calls `continueRender()` or `cancelRender()`.
- Keep a CSS fallback stack so the scene can degrade gracefully if the exact font is unavailable.

## Preferred pattern: local fonts with `@remotion/fonts`

`@remotion/fonts` is already included in this template. `loadFont()` is async and gates itself with `delayRender()`/`continueRender()`, so the frame waits until the font is ready — **but only when `loadFont()` is called from inside the React render lifecycle**. Called at module top level it creates its `delayRender()` handle during module evaluation, `FontFace.load()` does not resolve in the headless render context, and the render times out after 28000ms (`A delayRender() "Loading font ..." was called but not cleared`). So: **never call `loadFont()` at module top level.**

Correct pattern — export a loader from `remotion/load-fonts.ts`, call it from the scene component's mount `useEffect()`:

`remotion/load-fonts.ts`:

```ts
import {loadFont} from "@remotion/fonts";
import {staticFile} from "remotion";

export const BrandSans = "Brand Sans";

// Export a loader; do NOT call loadFont() at module top level.
export const loadBrandFonts = () =>
  Promise.all([
    loadFont({
      family: BrandSans,
      url: staticFile("fonts/brand-sans-regular.woff2"),
      weight: "400",
    }),
    loadFont({
      family: BrandSans,
      url: staticFile("fonts/brand-sans-semibold.woff2"),
      weight: "600",
    }),
  ]);
```

Scene component:

```tsx
import {useEffect, useRef} from "react";
import {loadBrandFonts} from "../remotion/load-fonts";

export const MyScene = () => {
  const started = useRef(false);
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    loadBrandFonts();
  }, []);
  // ...rest of the scene
};
```

Why this is safe:

- `loadFont()` runs inside the component mount effect, so its `delayRender()` handle lives in the render lifecycle and `continueRender()` fires after `FontFace.load()` resolves. Each parallel frame tab mounts once and loads the font once.
- The `useRef` guard avoids duplicate loads if the effect fires more than once.
- `loadFont()` calls `cancelRender()` on failure, which fails the render fast (no silent hang). If you need to fall back to the CSS stack instead of failing, use the manual `FontFace` pattern in the next section.

Use it in styles with a fallback stack, for example:

```ts
fontFamily: '"Brand Sans", var(--font-body)'
```

Rules:

- Store font files only under `public/fonts/`.
- Load only the weights, styles, and subsets actually used in the scene. Extra variants increase timeout risk.
- Prefer local `.woff2` files over remote URLs.
- Keep a fallback stack in CSS even after loading the custom font — e.g. a CJK face (PingFang SC / Hiragino Sans GB) when the custom font's latin subset omits CJK glyphs.
- **Never call `loadFont()` at module top level.** It times out the render.

## If the exact font is unavailable

- Many design systems reference proprietary fonts. Match the character using the system's fallback stack or a close system font.
- Reliability matters more than perfect brand fidelity. A clean fallback is better than a render that times out.
- Do not scrape or hotlink fonts from random websites.

## Manual async fallback pattern

Only use this when `@remotion/fonts` cannot solve the problem:

```tsx
import {useEffect, useState} from "react";
import {useDelayRender} from "remotion";

const useAsyncTypographyReady = () => {
  const {delayRender, continueRender, cancelRender} = useDelayRender();
  const [handle] = useState(() => delayRender("font:custom"));

  useEffect(() => {
    let mounted = true;

    Promise.resolve()
      .then(async () => {
        // Perform the async typography work here.
      })
      .then(() => {
        if (mounted) {
          continueRender(handle);
        }
      })
      .catch((err) => {
        if (mounted) {
          cancelRender(err);
        }
      });

    return () => {
      mounted = false;
    };
  }, [cancelRender, continueRender, handle]);
};
```

Rules:

- Scope the handle to a React component.
- Never create a typography `delayRender()` handle at module scope.
- Ensure every path ends in `continueRender()` or `cancelRender()`.
- Give `delayRender()` a readable label so timeout errors point to the right code.
- If the font cannot be loaded quickly, fall back to the CSS stack and continue; do not block render forever.

## Verification

- `pnpm run verify` catches type/lint/composition issues, but it does not prove async font loading is safe.
- After adding async font loading, run a full `pnpm run remotion:render`.
- Do not treat `remotion still`, even on several sampled frames, as a proxy for a real render. It does not exercise the same multi-frame lifecycle and timing behavior.
- A still render or Studio preview can succeed while a multi-frame render still times out.
