import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import tseslint from "typescript-eslint";
import absoluteFillExplicitFlexDirection from "./eslint-rules/absolute-fill-explicit-flex-direction.js";

const scaffoldPlugin = {
  rules: {
    "absolute-fill-explicit-flex-direction": absoluteFillExplicitFlexDirection,
  },
};

const languageOptions = {
  ecmaVersion: 2020,
  globals: {
    ...globals.browser,
    ...globals.node,
  },
  parserOptions: {
    ecmaVersion: "latest",
    ecmaFeatures: { jsx: true },
    sourceType: "module",
  },
};

export default tseslint.config(
  { ignores: ["dist", "build", "out"] },
  {
    plugins: {
      scaffold: scaffoldPlugin,
    },
    rules: {
      "scaffold/absolute-fill-explicit-flex-direction": "error",
    },
  },
  {
    files: ["**/*.{js,mjs,jsx}"],
    languageOptions,
    plugins: {
      "react-hooks": reactHooks,
    },
    rules: {
      ...js.configs.recommended.rules,
      ...reactHooks.configs.recommended.rules,
      "no-unused-vars": ["error", { varsIgnorePattern: "^[A-Z_]" }],
    },
  },
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions,
    plugins: {
      "react-hooks": reactHooks,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "@typescript-eslint/no-unused-vars": [
        "error",
        { varsIgnorePattern: "^[A-Z_]", argsIgnorePattern: "^_" },
      ],
    },
  },
);
