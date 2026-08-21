/*
 * Load local fonts for Remotion here with @remotion/fonts.
 * Keep only the exact font files, weights, and subsets that the scene uses.
 *
 * IMPORTANT: loadFont() is async and gates itself with delayRender()/continueRender().
 * Calling it at module top level TIMES OUT the render (~28s) — the delayRender()
 * handle is created outside the React lifecycle and FontFace.load() never resolves
 * in the headless render context. So EXPORT a loader here and call it from the
 * scene component's mount useEffect(). See .claude/skills/remotion-font-loading.
 *
 * Example — remotion/load-fonts.ts:
 * import {loadFont} from "@remotion/fonts";
 * import {staticFile} from "remotion";
 *
 * export const BrandSans = "Brand Sans";
 *
 * export const loadBrandFonts = () =>
 *   Promise.all([
 *     loadFont({ family: BrandSans, url: staticFile("fonts/brand-sans-regular.woff2"), weight: "400" }),
 *     loadFont({ family: BrandSans, url: staticFile("fonts/brand-sans-semibold.woff2"), weight: "600" }),
 *   ]);
 *
 * Example — scene component:
 * import {useEffect, useRef} from "react";
 * import {loadBrandFonts} from "../remotion/load-fonts";
 *
 *   const started = useRef(false);
 *   useEffect(() => {
 *     if (started.current) return;
 *     started.current = true;
 *     loadBrandFonts();
 *   }, []);
 *
 * Keep a CSS fallback stack (e.g. a CJK face) in the fontFamily declaration —
 * loadFont's latin subset omits CJK glyphs.
 */

export {};
