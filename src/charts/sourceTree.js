// Read the site's source files as syntax trees, for the chart guards in
// noHex.test.js and chartText.test.jsx. Only tests import this module.
import { readdirSync } from "node:fs";
import { join } from "node:path";

import { parse } from "espree";

// Every .js and .jsx file under dir, tests excluded.
export function sourceFiles(dir) {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    return /\.(js|jsx)$/.test(entry.name) && !/\.test\.(js|jsx)$/.test(path)
      ? [path]
      : [];
  });
}

export function parseModule(source) {
  return parse(source, {
    ecmaVersion: "latest",
    sourceType: "module",
    ecmaFeatures: { jsx: true },
    comment: true,
    loc: true,
    range: true,
  });
}

// Calls visit on node and every node under it, parents first.
export function walk(node, visit) {
  if (!node || typeof node.type !== "string") return;
  visit(node);
  for (const [key, value] of Object.entries(node)) {
    if (key === "loc" || key === "range") continue;
    if (Array.isArray(value)) value.forEach((child) => walk(child, visit));
    else if (value && typeof value === "object") walk(value, visit);
  }
}
