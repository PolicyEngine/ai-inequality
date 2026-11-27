import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";

// The page takes its colours from @policyengine/ui-kit. Tailwind writes a
// theme variable such as --color-teal-500 into the built CSS only when
// something uses it, and a var() naming a missing token draws nothing. So
// check the export defines every custom property the page's own styles and
// inline styles name. kitTheme.test.js does the same for chart tokens.

const ROOT = process.cwd();

function filesUnder(dir, keep) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return filesUnder(path, keep);
    return keep(path) ? [path] : [];
  });
}

// The site's own sources: stylesheets, components and the app shell. Tests
// are left out; they style nothing.
const SOURCES = [
  ...filesUnder(join(ROOT, "src"), () => true),
  ...filesUnder(join(ROOT, "app"), () => true),
]
  .filter((path) => /\.(css|jsx?|mjs)$/.test(path))
  .filter((path) => !/\.test\.jsx?$/.test(path))
  .map((path) => ({
    path: relative(ROOT, path),
    text: readFileSync(path, "utf8"),
  }));

// Comments can name a token without using it, so drop block comments and
// whole-line // comments before scanning.
function withoutComments(text) {
  return text.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
}

function tokensNamed() {
  const found = new Map();
  for (const { path, text } of SOURCES) {
    for (const [, name] of withoutComments(text).matchAll(
      /var\(\s*(--[\w-]+)/g,
    )) {
      if (!found.has(name)) found.set(name, path);
    }
  }
  return found;
}

const CSS_DIR = join(ROOT, "out", "_next", "static", "chunks");
const BUILT_CSS = existsSync(CSS_DIR)
  ? readdirSync(CSS_DIR)
      .filter((name) => name.endsWith(".css"))
      .map((name) => readFileSync(join(CSS_DIR, name), "utf8"))
      .join("\n")
  : null;

const RETIRED_PALETTE = /--pe-[\w-]+/;

test("the site's sources name no --pe-* colour", () => {
  const left = SOURCES.filter(({ text }) => RETIRED_PALETTE.test(text)).map(
    ({ path }) => path,
  );
  expect(left).toEqual([]);
});

test("the page names kit tokens, which the scan finds", () => {
  const tokens = tokensNamed();
  for (const token of [
    "--foreground",
    "--muted-foreground",
    "--primary",
    "--border",
    "--color-teal-500",
  ]) {
    expect(tokens.has(token), token).toBe(true);
  }
});

it.skipIf(!BUILT_CSS && !process.env.CI)(
  "the export's CSS defines every token the page's styles use",
  () => {
    expect(BUILT_CSS, "build the export (bun run build) first").not.toBeNull();
    expect(BUILT_CSS).not.toMatch(RETIRED_PALETTE);
    const missing = [...tokensNamed()]
      .filter(
        ([token]) => !new RegExp(`(?<![\\w-])${token}\\s*:`).test(BUILT_CSS),
      )
      .map(([token, path]) => `${token} (${path})`);
    expect(missing).toEqual([]);
  },
);
