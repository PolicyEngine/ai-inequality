import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

import { SERIES, tokensUsed } from "./kitTheme";

// The CSS next build exported, or null before a build. CI builds before it
// tests; locally, rebuild (bun run build) to check current code.
const CSS_DIR = join(process.cwd(), "out", "_next", "static", "chunks");
const BUILT_CSS = existsSync(CSS_DIR)
  ? readdirSync(CSS_DIR)
      .filter((name) => name.endsWith(".css"))
      .map((name) => readFileSync(join(CSS_DIR, name), "utf8"))
      .join("\n")
  : null;

test("charts take six distinct series colours, all kit tokens", () => {
  expect(new Set(SERIES).size).toBe(6);
  for (const colour of SERIES) {
    expect(colour).toMatch(/^var\(--[\w-]+\)$/);
  }
});

test("the theme names its tokens, including the kit's own styles", () => {
  const tokens = tokensUsed();
  expect(tokens).toContain("--chart-1");
  expect(tokens).toContain("--color-gray-600");
  expect(tokens).toContain("--foreground");
  expect(tokens).toContain("--border");
});

it.skipIf(!BUILT_CSS && !process.env.CI)(
  "the export's CSS defines every token the charts use",
  () => {
    expect(BUILT_CSS, "build the export (bun run build) first").not.toBeNull();
    const missing = tokensUsed().filter(
      (token) => !new RegExp(`${token}\\s*:`).test(BUILT_CSS),
    );
    expect(missing).toEqual([]);
  },
);
