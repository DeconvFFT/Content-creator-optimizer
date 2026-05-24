import tseslint from "typescript-eslint";

export default [
  {
    ignores: [".next/**", ".test-build/**", "node_modules/**", "out/**", "next-env.d.ts"]
  },
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    rules: {
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }
      ]
    }
  }
];
