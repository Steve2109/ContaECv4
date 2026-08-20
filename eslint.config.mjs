import { FlatCompat } from "@eslint/eslintrc";
import { dirname } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// ponytail: FlatCompat is required by Next.js 15 + ESLint 9 to bypass
// @rushstack/eslint-patch's "calling module not recognized" error
const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    rules: {
      // TypeScript rules - core enabled, permissive on edge cases
      "@typescript-eslint/no-empty-object-type": "warn",
      "@typescript-eslint/no-explicit-any": "warn",
      "@typescript-eslint/no-unused-vars": ["warn", { "argsIgnorePattern": "^_", "varsIgnorePattern": "^_" }],
      "@typescript-eslint/no-non-null-assertion": "warn",
      "@typescript-eslint/ban-ts-comment": "warn",
      "@typescript-eslint/prefer-as-const": "off",
      "@typescript-eslint/no-unused-disable-directive": "off",

      // React rules
      "react-hooks/exhaustive-deps": "warn",
      "react/no-unescaped-entities": "off",
      "react/display-name": "off",
      "react/prop-types": "off",
      "react-compiler/react-compiler": "off",

      // Next.js rules
      "@next/next/no-img-element": "warn",
      "@next/next/no-html-link-for-pages": "off",

      // General JavaScript rules - core safety enabled
      "prefer-const": "warn",
      "no-unused-vars": "off", // Covered by @typescript-eslint/no-unused-vars
      "no-console": "off",
      "no-debugger": "warn",
      "no-empty": "warn",
      "no-irregular-whitespace": "error",
      "no-case-declarations": "off",
      "no-fallthrough": "warn",
      "no-mixed-spaces-and-tabs": "error",
      "no-redeclare": "error",
      "no-undef": "off", // TypeScript catches undefined identifiers via `tsc`; ESLint's no-undef isn't scope-aware for globals like React/RequestInit
      "no-unreachable": "error",
      "no-useless-escape": "warn",
    },
  },
  {
    ignores: ["node_modules/**", ".next/**", "src/.next/**", "out/**", "build/**", "next-env.d.ts", "examples/**", "skills", "tailwind.config.ts", "mini-services/**", ".venv/**"],
  },
];

export default eslintConfig;
