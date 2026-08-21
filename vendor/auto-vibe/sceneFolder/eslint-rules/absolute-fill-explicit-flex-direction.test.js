import { RuleTester } from "eslint";
import tseslint from "typescript-eslint";
import rule from "./absolute-fill-explicit-flex-direction.js";

const ruleTester = new RuleTester({
  languageOptions: {
    ecmaVersion: "latest",
    parserOptions: { ecmaFeatures: { jsx: true } },
    sourceType: "module",
  },
});

ruleTester.run("absolute-fill-explicit-flex-direction", rule, {
  valid: [
    '<AbsoluteFill style={{ alignItems: "center", flexDirection: "row" }} />',
    '<AbsoluteFill style={{ justifyContent: "center", flexDirection: "column" }} />',
    '<AbsoluteFill style={{ backgroundColor: "black" }} />',
    "<AbsoluteFill style={styles.root} />",
    "const style = makeStyle(); <AbsoluteFill style={style} />",
    "const style = condition ? rowStyle : columnStyle; <AbsoluteFill style={style} />",
    'let style = { alignItems: "center" }; <AbsoluteFill style={style} />',
    'const style = { alignItems: "center", flexDirection: "row" }; <AbsoluteFill style={style} />',
    'const style = { alignItems: "center" }; const View = () => { const style = makeStyle(); return <AbsoluteFill style={style} />; };',
    '<div style={{ alignItems: "center" }} />',
    '<AbsoluteFill style={{ ["justifyContent"]: "center", "flexDirection": "row" }} />',
  ],
  invalid: [
    {
      code: '<AbsoluteFill style={{ alignItems: "center" }} />',
      errors: [{ messageId: "missingFlexDirection" }],
    },
    {
      code: '<AbsoluteFill style={{ justifyContent: "center" }} />',
      errors: [{ messageId: "missingFlexDirection" }],
    },
    {
      code: '<AbsoluteFill style={{ ...base, alignItems: "center" }} />',
      errors: [{ messageId: "missingFlexDirection" }],
    },
    {
      code: '<AbsoluteFill style={{ ["alignItems"]: "center" }} />',
      errors: [{ messageId: "missingFlexDirection" }],
    },
    {
      code: 'const style = { alignItems: "center" }; <AbsoluteFill style={style} />',
      errors: [{ messageId: "missingFlexDirection" }],
    },
    {
      code: 'const baseStyle = { justifyContent: "center" }; const style = baseStyle; <AbsoluteFill style={style} />',
      errors: [{ messageId: "missingFlexDirection" }],
    },
    {
      code: 'const View = () => <AbsoluteFill style={style} />; const style = { alignItems: "center" };',
      errors: [{ messageId: "missingFlexDirection" }],
    },
  ],
});

const typeScriptRuleTester = new RuleTester({
  languageOptions: {
    parser: tseslint.parser,
    parserOptions: { ecmaFeatures: { jsx: true } },
  },
});

typeScriptRuleTester.run(
  "absolute-fill-explicit-flex-direction (TypeScript)",
  rule,
  {
    valid: [
      {
        filename: "scene.tsx",
        code: 'const style = { alignItems: "center", flexDirection: "row" } satisfies React.CSSProperties; <AbsoluteFill style={style} />',
      },
      {
        filename: "scene.tsx",
        code: 'const styles = { root: { alignItems: "center" } }; <AbsoluteFill style={styles.root} />',
      },
      {
        filename: "scene.tsx",
        code: "const getStyle = (): React.CSSProperties => ({}); <AbsoluteFill style={getStyle()} />",
      },
    ],
    invalid: [
      {
        filename: "scene.tsx",
        code: 'const style = { alignItems: "center" } as React.CSSProperties; <AbsoluteFill style={style} />',
        errors: [{ messageId: "missingFlexDirection" }],
      },
      {
        filename: "scene.tsx",
        code: 'const style: React.CSSProperties = { alignItems: "center" }; <AbsoluteFill style={style} />',
        errors: [{ messageId: "missingFlexDirection" }],
      },
      {
        filename: "scene.tsx",
        code: 'const style = { justifyContent: "center" } satisfies React.CSSProperties; <AbsoluteFill style={style} />',
        errors: [{ messageId: "missingFlexDirection" }],
      },
      {
        filename: "scene.tsx",
        code: 'const style = { alignItems: "center" } as const; <AbsoluteFill style={style as React.CSSProperties} />',
        errors: [{ messageId: "missingFlexDirection" }],
      },
    ],
  },
);
