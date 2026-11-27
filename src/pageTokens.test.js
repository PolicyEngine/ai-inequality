import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";

// The page takes its colours from @policyengine/ui-kit. Tailwind writes a
// theme variable such as --color-teal-500 into the built CSS only when
// something uses it, and a var() naming a missing token draws nothing. So
// check that each exported page links CSS defining, outside dark mode, every
// custom property the page's own styles and inline styles name.
// kitTheme.test.js does the same for chart tokens.

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

const OUT = join(ROOT, "out");

// Each exported page and the stylesheets it links. A token counts as defined
// for a page only if a stylesheet that page links defines it, so a definition
// in an unlinked or leftover chunk doesn't count.
function exportedPages() {
  if (!existsSync(OUT)) return null;
  return readdirSync(OUT)
    .filter((name) => name.endsWith(".html"))
    .map((name) => {
      const html = readFileSync(join(OUT, name), "utf8");
      const sheets = [...html.matchAll(/href="[^"]*?(\/_next\/[^"]+\.css)"/g)]
        .map(([, href]) => join(OUT, href))
        .filter((path, i, all) => all.indexOf(path) === i);
      return { name, sheets };
    })
    .filter(({ sheets }) => sheets.length > 0);
}

// A selector or @media prelude that applies only in dark mode. Nothing on the
// site sets the kit's .dark class, so a token defined only there is missing.
function darkOnly(prelude) {
  if (prelude.startsWith("@media"))
    return /prefers-color-scheme:\s*dark/.test(prelude);
  return prelude
    .split(",")
    .every((part) => /\.dark\b|data-theme=["']?dark/.test(part));
}

// Custom properties a stylesheet defines outside dark-only rules.
function definedTokens(css) {
  const defined = new Set();
  const open = [];
  let text = "";
  let quote = null;
  for (const ch of css.replace(/\/\*[\s\S]*?\*\//g, "")) {
    if (quote) {
      text += ch;
      if (ch === quote) quote = null;
    } else if (ch === '"' || ch === "'") {
      quote = ch;
      text += ch;
    } else if (ch === "{") {
      open.push(text.trim());
      text = "";
    } else if (ch === ";" || ch === "}") {
      const name = /^(--[\w-]+)\s*:/.exec(text.trim())?.[1];
      if (name && !open.some(darkOnly)) defined.add(name);
      if (ch === "}") open.pop();
      text = "";
    } else {
      text += ch;
    }
  }
  return defined;
}

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

test("the site's sources build no custom property name at runtime", () => {
  // The scan below reads var() names from the source text, so it can't see a
  // name assembled at runtime.
  const built = SOURCES.filter(({ text }) =>
    /var\(\s*--[\w-]*(\$\{|["'`]\s*\+)/.test(withoutComments(text)),
  ).map(({ path }) => path);
  expect(built).toEqual([]);
});

const PAGES = exportedPages();

describe.skipIf(!PAGES && !process.env.CI)("the export", () => {
  test("exists and is newer than the sources it was built from", () => {
    expect(PAGES, "build the export (bun run build) first").not.toBeNull();
    const built = statSync(join(OUT, "index.html")).mtimeMs;
    const newer = SOURCES.filter(
      ({ path }) => statSync(join(ROOT, path)).mtimeMs > built,
    ).map(({ path }) => path);
    expect(newer, "rebuild the export (bun run build)").toEqual([]);
  });

  test("links CSS from every page", () => {
    const names = PAGES.map(({ name }) => name);
    for (const page of [
      "index.html",
      "research.html",
      "policy-analysis.html",
      "income-shift.html",
      "references.html",
      "budget-lab.html",
    ]) {
      expect(names, page).toContain(page);
    }
  });

  test("defines, on every page, each token the page's styles use", () => {
    const tokens = [...tokensNamed()];
    const problems = PAGES.flatMap(({ name, sheets }) => {
      const css = sheets.map((path) => readFileSync(path, "utf8")).join("\n");
      const defined = definedTokens(css);
      return [
        ...(RETIRED_PALETTE.test(css) ? [`${name}: --pe-* in its CSS`] : []),
        ...tokens
          .filter(([token]) => !defined.has(token))
          .map(([token, path]) => `${name}: ${token} (${path})`),
      ];
    });
    expect(problems).toEqual([]);
  });
});
