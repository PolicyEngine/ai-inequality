import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";

import { PolicyEngineShell } from "@policyengine/ui-kit/layout";
import { fireEvent, render } from "@testing-library/react";
import { parse } from "espree";
import { useMemo, useState } from "react";
import { MemoryRouter } from "react-router-dom";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";

import { memoMarkdown } from "./data/memoContent";
import { COUNTRIES, countryFromSearchParams } from "./utils/countryConfig";

// Every view module, keyed by its path, so the sweep can render each route
// App.jsx declares.
const VIEW_MODULES = import.meta.glob(
  ["./views/*.jsx", "!./views/*.test.jsx"],
  { eager: true },
);

// Microcosm's pre-August name and the dataset it replaced as the default, in
// the spellings they take in prose, release ids and package names, such as
// ecps_2024. Published ids keep the old spelling in data and code; pages
// never show them.
const RETIRED =
  /populace|enhanced[\s_-]*(?:cps|current[\s_-]*population[\s_-]*survey)|(?<![a-z])e[\s_-]?cps(?![a-z])|policyengine[\s_-]*us[\s_-]*data/i;

// Exact phrases that match RETIRED but name no dataset, such as a reference
// title that uses the English noun. Add one only after reading it in context.
const ALLOWED_PHRASES = [];

// Pages that show a retired name today. Remove an entry once its page stops.
// A link to any other outside page passes, so read each new one by eye.
const PAGES_SHOWING_RETIRED_NAMES = [
  // The org page renders its profile README, which lists the earlier
  // dataset's repository, and the org's repository list shows retired names
  // in repository descriptions.
  /^https?:\/\/(?:www\.)?github\.com\/(?:orgs\/)?PolicyEngine(?:\/repositories)?\/?(?:[?#]|$)/i,
  /^https?:\/\/(?:www\.)?github\.com\/PolicyEngine\/\.github\/(?:tree|blob)\/[^/?#]+\/profile(?:\/README\.md)?\/?(?:[?#]|$)/i,
  // Their READMEs print Microcosm's release ids, link its pre-August pages or
  // use its old name, which microcosm-dynamics' description also uses. The
  // repository's page, a branch's root and the README itself show them.
  /^https?:\/\/(?:www\.)?github\.com\/PolicyEngine\/(?:microcosm|microcosm-dynamics|policyengine-us)(?:\/tree\/[^/?#]+|\/blob\/[^/?#]+\/README\.md)?\/?(?:[?#]|$)/i,
  // The landing site's home page names both.
  /^https?:\/\/(?:www\.)?microcosm\.institute(?:[/?#]|$)/i,
  // The Python page's example loads the earlier dataset. The model page's
  // comparison with peer models names it, whether a click or ?compare= opens
  // the comparison, and its data pipeline diagram names it too.
  /^https?:\/\/(?:www\.)?policyengine\.org\/us\/(?:python|model(?:\/data\/pipeline)?)\/?(?:[?#]|$)/i,
  // The research listing shows a card for a post that names the earlier
  // dataset.
  /^https?:\/\/(?:www\.)?policyengine\.org\/us\/research\/?(?:[?#]|$)/i,
];

// Links in @policyengine/ui-kit's shared header and footer, which wrap every
// route here, that open a page listed above. Remove one once its page stops
// showing a retired name.
const SHELL_LINKS_TO_RETIRED_PAGES = [
  "https://policyengine.org/us/model",
  "https://policyengine.org/us/python",
  "https://policyengine.org/us/research",
];

// Where policyengine.org serves the study, so links resolve as they do there.
const STUDY_URL = "https://policyengine.org/us/ai-inequality";
const STUDY_PATH = new URL(STUDY_URL).pathname;

const ROOT = process.cwd();

const entriesUnder = (dir) =>
  readdirSync(join(ROOT, dir), { recursive: true, withFileTypes: true });
const relative = (entry) =>
  join(entry.parentPath, entry.name).slice(ROOT.length + 1);

function pathsUnder(dir) {
  return entriesUnder(dir)
    .filter((entry) => entry.isFile())
    .map(relative);
}

// Next.js copies the file a symlink points at into the export, which could
// serve a file from outside the folders these tests read.
const symlinksUnder = (dir) =>
  entriesUnder(dir)
    .filter((entry) => entry.isSymbolicLink())
    .map(relative);

const read = (path) => readFileSync(join(ROOT, path), "utf8");
const bytes = (path) => readFileSync(join(ROOT, path));

// True for a file that holds UTF-8 text, which the name checks can read.
const UTF8 = new TextDecoder("utf-8", { fatal: true });
function isText(path) {
  const data = bytes(path);
  if (data.includes(0)) return false;
  try {
    UTF8.decode(data);
    return true;
  } catch {
    return false;
  }
}

// Folds compatibility characters and drops invisible ones, so a zero-width
// space or a soft hyphen can't split a name, then blanks the allowed phrases.
function normalize(text) {
  let folded = text
    .normalize("NFKC")
    .replace(/[\u00ad\u180e\u200b-\u200f\u2060-\u2064\ufeff]/g, "");
  for (const phrase of ALLOWED_PHRASES) {
    folded = folded.split(phrase).join(" ");
  }
  return folded;
}

const showsRetiredName = (text) => RETIRED.test(normalize(text));

function excerpt(text) {
  const folded = normalize(text);
  const at = folded.search(RETIRED);
  return folded.slice(Math.max(0, at - 40), at + 40);
}

// The text a browser shows for markup: tags dropped and entities decoded, so a
// name split across tags or joined by &nbsp; still matches.
function markupText(markup) {
  const char = (code) => (code <= 0x10ffff ? String.fromCodePoint(code) : "");
  return markup
    .replace(/<[^>]*>/g, "")
    .replace(/&nbsp;/gi, "\u00a0")
    .replace(/&shy;/gi, "\u00ad")
    .replace(/&#(\d+);/g, (_, code) => char(Number(code)))
    .replace(/&#x([0-9a-f]+);/gi, (_, code) => char(parseInt(code, 16)))
    .replace(/&amp;/gi, "&");
}

const linksRetiredPage = (url) =>
  PAGES_SHOWING_RETIRED_NAMES.some((pattern) => pattern.test(url));

// Resolves a link the way a browser on the given page would.
function resolve(target, base) {
  try {
    return new URL(target, base).href;
  } catch {
    return target;
  }
}

// The routes App.jsx declares, each with the view it renders. A route written
// any other way leaves the two counts in the route test unequal.
const APP = "src/App.jsx";
function appRoutes() {
  const app = read(APP);
  const modules = new Map(
    [...app.matchAll(/^import (\w+) from "(\.\/views\/[\w-]+)";$/gm)].map(
      ([, name, module]) => [name, `${module}.jsx`],
    ),
  );
  return [
    ...app.matchAll(
      /<Route\s+path="([^"]*)"\s+element=\{<(\w+)\s*\/>\}\s*\/>/g,
    ),
  ].map(([, path, name]) => ({
    path,
    View: VIEW_MODULES[modules.get(name)]?.default,
  }));
}
const ROUTES = appRoutes();

// Each route in each country, written as a visitor reaches it.
const DEFAULT_COUNTRY = countryFromSearchParams(new URLSearchParams());
const PAGES = ROUTES.flatMap(({ path, View }) =>
  Object.keys(COUNTRIES).map((country) => [
    country === DEFAULT_COUNTRY ? path : `${path}?country=${country}`,
    View,
  ]),
);

// The one module that recognizes the frozen release-id prefix, and the one
// token in it that may spell the old name.
const RELEASE_ID_PARSER = "src/utils/modelMetadata.js";
const RELEASE_ID_PREFIX = "(?:microcosm|populace)-us-";

// The study's address on policyengine.org in either country, with or without
// www, and the path, query and hash after it.
const STUDY_LINK =
  /^https?:\/\/(?:www\.)?policyengine\.org\/(?:us|uk)\/ai-inequality(\/[^?#]*)?(\?[^#]*)?(#.*)?$/i;

// True for a link into the study that opens neither a page the test renders
// nor a file public/ serves: a path App.jsx doesn't declare, or a page's query
// other than a known country, which could open a state the sweep never
// reached. Hashes pass, since site code never reads one (the behavior test
// checks), and so does a query on a served file, which serves the same file.
function opensUnrenderedPage(url) {
  const match = STUDY_LINK.exec(url);
  if (!match) return false;
  const path = (match[1] ?? "").replace(/\/+$/, "") || "/";
  const query = new URLSearchParams(match[2] ?? "");
  const keys = [...query.keys()];
  const knownQuery =
    keys.length === 0 ||
    (keys.length === 1 &&
      keys[0] === "country" &&
      Object.hasOwn(COUNTRIES, query.get("country")));
  if (knownQuery && ROUTES.some((route) => route.path === path)) return false;
  return ![`public${path}`, `public${path}.html`].some((file) =>
    publicFiles.includes(file),
  );
}

// True for a request for a file public/ serves at the study's address.
function servesFile(url) {
  const prefix = `${STUDY_URL}/`;
  if (!url.startsWith(prefix)) return false;
  const path = url.slice(prefix.length).replace(/[?#].*$/, "");
  return publicFiles.includes(`public/${decodeURIComponent(path)}`);
}

// Media can show text too, but this test can't read pixels, so check new images
// by eye. Documents, archives and any other file that isn't UTF-8 text hold
// text the name checks can't read, so each needs a reviewed entry.
const MEDIA =
  /\.(?:png|jpe?g|gif|webp|avif|bmp|ico|woff2?|ttf|otf|eot|mp3|mp4|webm|mov|wav)$/i;
const DOCUMENTS =
  /\.(?:pdf|rtf|epub|(?:doc|dot|xls|xlt|ppt|pot|pps)[xm]?|od[tpsg]|key|numbers|pages|zip|gz|tgz|tar|7z|rar|bz2|xz|zst|br|lz4?)$/i;
// The first bytes of a PDF, a zip (which every Office Open XML, OpenDocument
// and EPUB file is), an older Office file and the common compressed formats,
// so a document renamed as an image still counts as a document.
const DOCUMENT_SIGNATURES = [
  "%PDF",
  "PK\x03\x04",
  "\xd0\xcf\x11\xe0",
  "\x1f\x8b",
  "7z\xbc\xaf\x27\x1c",
  "Rar!",
  "BZh",
  "\xfd7zXZ",
  "\x28\xb5\x2f\xfd",
].map((signature) => Buffer.from(signature, "latin1"));
const startsLikeDocument = (path) => {
  const data = bytes(path);
  return DOCUMENT_SIGNATURES.some((signature) =>
    data.subarray(0, signature.length).equals(signature),
  );
};
// True for a file the name checks can't read: a document by name, media
// whose bytes start like a document, or anything else that isn't UTF-8 text.
const isUnreadable = (path) =>
  DOCUMENTS.test(path) ||
  (MEDIA.test(path) ? startsLikeDocument(path) : !isText(path));
// Documents in public/, src/ or app/ that someone has read in full and found
// clean.
const CHECKED_DOCUMENTS = [];
const MARKUP = /\.(?:html?|svg|xml)$/i;

// Tests and the test setup, which Vitest loads and the site never ships.
const isTest = (path) =>
  /\.test\.[cm]?[jt]sx?$|(?:^|\/)setupTests\.[cm]?[jt]sx?$/.test(path);
const isCode = (path) => /\.[cm]?[jt]sx?$/.test(path);
const isData = (path) => path.startsWith("src/data/") && !isCode(path);

const publicFiles = pathsUnder("public");
const publicText = publicFiles.filter(
  (path) => !MEDIA.test(path) && !isUnreadable(path),
);

// Everything src/ and app/ hold apart from tests. Data may keep published ids,
// so the name checks skip it; its keys get the read check below.
const siteFiles = [...pathsUnder("src"), ...pathsUnder("app")].filter(
  (path) => !isTest(path),
);
// The site's code, styles, copy and text assets, and the Next.js and Vercel
// settings, which can put strings in the bundle too.
const siteText = [
  ...siteFiles.filter(
    (path) => !isData(path) && !MEDIA.test(path) && !isUnreadable(path),
  ),
  ...readdirSync(ROOT).filter((name) =>
    /^(?:next\.config\.[cm]?[jt]s|vercel\.json)$/.test(name),
  ),
];
const siteCode = siteText.filter(isCode);
// Files that reach visitors under their own names.
const servedFiles = [
  ...publicFiles,
  ...siteFiles.filter((path) => !isData(path)),
];

const sourceText = (path) =>
  path === RELEASE_ID_PARSER
    ? read(path).replace(RELEASE_ID_PREFIX, "")
    : read(path);

const ABSOLUTE_URL = /https?:\/\/[^\s"'`<>()\\]+/g;
// A quoted or bracketed path from policyengine.org's root under a country,
// such as "/us/python", opens that page from wherever it sits.
const SITE_PATH = /["'`(=]\s*(\/(?:us|uk)\/[^\s"'`<>()\\]*)/g;
const PROTOCOL_RELATIVE = /["'`(=]\s*(\/\/[^\s"'`<>()\\]+)/g;
// Link and embed targets in markup that public/ serves, resolved against the
// address it serves the file at.
const MARKUP_LINK = /\b(?:href|src|action|data)\s*=\s*["']([^"']+)["']/gi;

function linksIn(path) {
  const text = read(path);
  const served = path.startsWith("public/");
  const base = served
    ? `${STUDY_URL}/${path.slice("public/".length)}`
    : `${STUDY_URL}/`;
  const targets = (pattern) =>
    [...text.matchAll(pattern)].map(([, target]) => resolve(target, base));
  return [
    ...(text.match(ABSOLUTE_URL) ?? []),
    ...targets(SITE_PATH),
    ...targets(PROTOCOL_RELATIVE),
    ...(served && MARKUP.test(path) ? targets(MARKUP_LINK) : []),
  ].map((url) => url.replace(/[.,;:!?]+$/, ""));
}

// Every way site code can ask the network for something, and the one form the
// site uses: a fetch of a file that public/ serves, named in the call or in a
// string constant that site code defines.
const REQUESTS =
  /\b(?:fetch|XMLHttpRequest|EventSource|WebSocket|sendBeacon|axios)\b/g;
const SERVED_FETCH = /\bfetch\(withBasePath\((?:"([^"]+)"|(\w+))\)\)/g;
const STRING_CONSTANT = /\bconst (\w+) = "([^"]*)";/g;

// The file a served fetch asks for, or null when it names a constant that site
// code never defines or defines with more than one value.
function fetchedFile([, literal, name], constants) {
  if (literal) return literal;
  const values = constants.get(name) ?? new Set();
  return values.size === 1 ? [...values][0] : null;
}

// Code with its comments blanked out, so the fetch check reads none. espree,
// the parser ESLint runs on this code, finds them, so a URL inside a string
// stays whole. espree reads no TypeScript, so a file it can't parse keeps its
// comments, and a request word in one of them still counts.
function withoutComments(source) {
  let comments;
  try {
    ({ comments } = parse(source, {
      ecmaVersion: "latest",
      sourceType: "module",
      ecmaFeatures: { jsx: true },
      comment: true,
      range: true,
    }));
  } catch {
    return source;
  }
  return comments.reduce(
    (code, { range: [start, end] }) =>
      code.slice(0, start) + " ".repeat(end - start) + code.slice(end),
    source,
  );
}

// Ways code can change a page after the step that set it off. The sweep
// records each state as soon as a step ends, so it would miss what these show.
const DEFERS = new Set([
  "setTimeout",
  "setInterval",
  "requestAnimationFrame",
  "requestIdleCallback",
  "queueMicrotask",
  "Promise",
  "lazy",
  "Suspense",
  "startTransition",
  "useTransition",
  "useDeferredValue",
  "useSyncExternalStore",
]);
const PROMISE_STEPS = new Set(["then", "catch", "finally"]);

// What a visitor's browser does that the sweep never does: resize, scroll,
// watch the page, change the address's hash, or press inside a clicked
// element's children.
const UNSWEPT_INPUTS = new Set([
  "addEventListener",
  "matchMedia",
  "innerWidth",
  "innerHeight",
  "outerWidth",
  "outerHeight",
  "IntersectionObserver",
  "ResizeObserver",
  "MutationObserver",
  "hash",
  "onhashchange",
  "onpopstate",
  "onresize",
  "onscroll",
  "srcElement",
  "composedPath",
  "relatedTarget",
  "elementFromPoint",
  "elementsFromPoint",
]);

// Routing that could serve a page App.jsx doesn't declare.
const ROUTING = new Set([
  "Routes",
  "Route",
  "Outlet",
  "useRoutes",
  "useOutlet",
  "matchRoutes",
  "createBrowserRouter",
  "createHashRouter",
  "createMemoryRouter",
  "createStaticRouter",
  "createRoutesFromElements",
  "createRoutesFromChildren",
  "RouterProvider",
]);

// The deferred load site code may make: Next.js loads the router app after
// the page, and the sweep renders App's views directly.
const ALLOWED_IMPORTS = [{ path: "src/ClientAppRouter.jsx", source: "./App" }];

// Parses a module with JSX, or returns null when espree can't.
function parseModule(source) {
  try {
    return parse(source, {
      ecmaVersion: "latest",
      sourceType: "module",
      ecmaFeatures: { jsx: true },
      loc: true,
    });
  } catch {
    return null;
  }
}

function walk(node, visit, parent = null) {
  visit(node, parent);
  for (const [key, value] of Object.entries(node)) {
    if (key === "loc" || key === "range") continue;
    for (const child of Array.isArray(value) ? value : [value]) {
      if (child && typeof child.type === "string") walk(child, visit, node);
    }
  }
}

const attributeName = (attribute) =>
  attribute.type === "JSXAttribute" ? attribute.name.name : null;

// True for a handler that only stops a click from reaching the element
// around it, such as a link inside a card that opens on a click. A visitor's
// click on the link then opens the link and nothing else.
function onlyStopsPropagation(attribute) {
  const handler = attribute.value?.expression;
  if (
    handler?.type !== "ArrowFunctionExpression" ||
    handler.params.length !== 1 ||
    handler.params[0].type !== "Identifier"
  ) {
    return false;
  }
  const { body } = handler;
  const call =
    body.type === "BlockStatement"
      ? body.body.length === 1 && body.body[0].type === "ExpressionStatement"
        ? body.body[0].expression
        : null
      : body;
  return (
    call?.type === "CallExpression" &&
    call.arguments.length === 0 &&
    call.callee.type === "MemberExpression" &&
    !call.callee.computed &&
    call.callee.object.type === "Identifier" &&
    call.callee.object.name === handler.params[0].name &&
    call.callee.property.name === "stopPropagation"
  );
}

// The ways a module could show a visitor something the sweep never reaches:
// it defers rendering, reacts to input the sweep never gives, handles an
// event the sweep never fires, reads more of a clicked element than the
// sweep sets, or routes outside App.jsx. Each finding names its line.
function unsweptBehavior(path, source) {
  const ast = parseModule(source);
  if (!ast) return [`${path}: espree can't parse it`];
  const found = [];
  const note = (node, what) =>
    found.push(`${path}:${node.loc.start.line}: ${what}`);
  const isKey = (node, parent) =>
    (parent?.type === "Property" &&
      parent.key === node &&
      !parent.computed &&
      !parent.shorthand) ||
    ((parent?.type === "MethodDefinition" ||
      parent?.type === "PropertyDefinition") &&
      parent.key === node &&
      !parent.computed);
  walk(ast, (node, parent) => {
    const named = node.type === "Identifier" || node.type === "JSXIdentifier";
    if (named && parent?.type !== "JSXAttribute" && !isKey(node, parent)) {
      if (DEFERS.has(node.name)) note(node, `defers rendering (${node.name})`);
      if (UNSWEPT_INPUTS.has(node.name)) {
        note(node, `reacts to input the sweep never gives (${node.name})`);
      }
      if (ROUTING.has(node.name) && path !== APP) {
        note(node, `routes outside App.jsx (${node.name})`);
      }
    }
    if (node.type === "AwaitExpression" || node.async === true) {
      note(node, "defers rendering (async)");
    }
    if (
      node.type === "ImportExpression" &&
      !ALLOWED_IMPORTS.some(
        (allowed) =>
          allowed.path === path && allowed.source === node.source.value,
      )
    ) {
      note(node, "defers rendering (import())");
    }
    // A promise chain may only follow fetch, which never settles in the
    // sweep and whose file the public checks read.
    if (
      node.type === "CallExpression" &&
      node.callee.type === "MemberExpression" &&
      !node.callee.computed &&
      PROMISE_STEPS.has(node.callee.property.name)
    ) {
      let root = node;
      while (
        root.type === "CallExpression" &&
        root.callee.type === "MemberExpression" &&
        !root.callee.computed &&
        PROMISE_STEPS.has(root.callee.property.name)
      ) {
        root = root.callee.object;
      }
      const fromFetch =
        root.type === "CallExpression" &&
        root.callee.type === "Identifier" &&
        root.callee.name === "fetch";
      if (!fromFetch) note(node, "defers rendering (a promise)");
    }
    // Code that sends the browser to another address opens a page the link
    // checks never see.
    if (
      node.type === "MemberExpression" &&
      !node.computed &&
      ["href", "assign", "replace", "reload"].includes(node.property.name) &&
      ((node.object.type === "Identifier" && node.object.name === "location") ||
        (node.object.type === "MemberExpression" &&
          !node.object.computed &&
          node.object.property.name === "location"))
    ) {
      note(node, `navigates without a link (location.${node.property.name})`);
    }
    // The sweep sets value and checked on the element it works, and nothing
    // else about the event's target.
    if (
      node.type === "MemberExpression" &&
      !node.computed &&
      node.property.name === "target" &&
      !(
        parent?.type === "MemberExpression" &&
        parent.object === node &&
        !parent.computed &&
        ["value", "checked"].includes(parent.property.name)
      )
    ) {
      note(node, "reads more of an event's target than the sweep sets");
    }
    if (node.type === "JSXOpeningElement") {
      const names = node.attributes.map(attributeName).filter(Boolean);
      const handled = node.attributes.filter((attribute) =>
        /^on[A-Z]/.test(attributeName(attribute) ?? ""),
      );
      for (const attribute of handled) {
        const event = attribute.name.name.replace(/Capture$/, "");
        const call = attribute.value?.expression;
        // A roving radio group's arrow keys choose among the same options
        // its clicks choose (src/utils/useRovingRadioGroup.jsx).
        const rovingKeys =
          event === "onKeyDown" &&
          call?.type === "CallExpression" &&
          call.callee.type === "MemberExpression" &&
          call.callee.property.name === "keyDownHandler";
        if (!SWEPT_EVENTS.has(event) && !rovingKeys) {
          note(attribute, `handles an event the sweep never fires (${event})`);
        }
      }
      if (
        handled.some((attribute) => !onlyStopsPropagation(attribute)) &&
        (names.includes("href") || names.includes("to"))
      ) {
        note(node, "a link handles an event, and the sweep never works links");
      }
    }
  });
  return found;
}

// The site modules a module imports, directly or by re-exporting them.
function importsOf(path) {
  const ast = parseModule(read(path));
  if (!ast) return [];
  const sources = [];
  walk(ast, (node) => {
    if (
      [
        "ImportDeclaration",
        "ExportNamedDeclaration",
        "ExportAllDeclaration",
        "ImportExpression",
      ].includes(node.type) &&
      typeof node.source?.value === "string" &&
      node.source.value.startsWith(".")
    ) {
      sources.push(join(dirname(path), node.source.value));
    }
  });
  return sources.flatMap((base) => {
    const found = [
      base,
      ...[".js", ".jsx", ".mjs", ".cjs"].map((extension) => base + extension),
      ...["index.js", "index.jsx"].map((index) => join(base, index)),
    ].find((candidate) => siteFiles.includes(candidate));
    return found ? [found] : [];
  });
}

// The code modules the site runs: what the Next.js layout and pages import,
// directly or through other site modules. A module nothing imports never
// renders.
function runningModules() {
  const running = new Set();
  const queue = siteFiles.filter((path) =>
    /^app\/(?:.*\/)?(?:layout|page)\.[cm]?[jt]sx?$/.test(path),
  );
  while (queue.length > 0) {
    const path = queue.pop();
    if (running.has(path) || !isCode(path)) continue;
    running.add(path);
    queue.push(...importsOf(path));
  }
  return running;
}

// A frozen id can reach a page only through code that names the data key
// holding it. AIScenarios names this one only inside the call below, which
// turns the id into a label. Any other mention of such a key fails until
// someone confirms that it prints no id.
const ALLOWED_READS = [
  {
    path: "src/components/AIScenarios.jsx",
    key: "certifiedDataBuildId",
    call: "microcosmBuildLabel(metadata.certifiedDataBuildId)",
  },
];

// React keeps each element's current props under a key with this prefix, so
// the sweep finds every element that handles a press or a hover, whatever role
// it declares.
const REACT_PROPS = "__reactProps$";
const PRESS_HANDLERS = [
  "onClick",
  "onDoubleClick",
  "onMouseDown",
  "onMouseUp",
  "onPointerDown",
  "onPointerUp",
];
const HOVER_HANDLERS = [
  "onMouseEnter",
  "onMouseOver",
  "onMouseMove",
  "onPointerEnter",
  "onPointerOver",
  "onPointerMove",
  "onFocus",
];

function handlers(element) {
  const key = Object.keys(element).find((name) => name.startsWith(REACT_PROPS));
  const props = (key && element[key]) || {};
  return new Set(
    [...PRESS_HANDLERS, ...HOVER_HANDLERS].filter(
      (name) =>
        typeof props[name] === "function" ||
        typeof props[`${name}Capture`] === "function",
    ),
  );
}

const hovers = (handled) => HOVER_HANDLERS.some((name) => handled.has(name));

// The events the sweep fires: presses, hovers, focus, and the change a click
// on a checkbox or radio or a select's new value sets off.
const SWEPT_EVENTS = new Set([
  ...PRESS_HANDLERS,
  ...HOVER_HANDLERS,
  "onChange",
]);

// Controls that change what a page shows without a handler of their own, such
// as a native disclosure, and anything styled with a pointer cursor.
const CONTROLS = [
  "button",
  "summary",
  "input[type=checkbox]",
  "input[type=radio]",
  "[aria-expanded]",
  "[aria-haspopup]",
  "[aria-pressed]",
  "[role=button]",
  "[role=checkbox]",
  "[role=menuitem]",
  "[role=menuitemcheckbox]",
  "[role=menuitemradio]",
  "[role=option]",
  "[role=radio]",
  "[role=switch]",
  "[role=tab]",
  "[role=treeitem]",
  '[style*="cursor: pointer"]',
].join(",");

// Links leave the page, and the test renders each page on its own.
const NAVIGATES = 'a[href]:not([href^="#"]),area[href]:not([href^="#"])';

// Elements whose target opens another page or shows it inside this one.
const LINKING =
  "[href],iframe[src],frame[src],embed[src],object[data],form[action]";

// Radio groups, tab lists, list boxes and selects each hold one value, and
// choosing one of their options sets that value whatever the page showed
// before. Native radios that share a name form a group too.
const SETTERS = "[role=radiogroup],[role=tablist],[role=listbox],select";
const SETTER_OPTIONS =
  "[role=radio],[role=tab],[role=option],input[type=radio]";

// Fields the sweep can't fill. A page that adds one fails until the sweep
// learns to try its values.
const FIELDS = [
  "input:not([type=checkbox]):not([type=radio]):not([type=hidden]):not([type=button]):not([type=submit]):not([type=reset])",
  "textarea",
  '[contenteditable]:not([contenteditable="false"])',
].join(",");

// The country switch swaps the whole page. PAGES renders each country on its
// own, so the sweep leaves the switch alone.
const COUNTRY_SWITCH = '[role=radiogroup][aria-label="Country"]';

// A pass that needs more clicks than this has met a control that remounts the
// others on every click, so it fails instead of looping.
const MAX_CLICKS_PER_PASS = 500;

// Each route costs a fresh render and a pass. A page that needs more than this
// has controls that remount on every click, so it fails instead of looping.
const MAX_ROUTES = 1000;

// What pages ask of the browser while the sweep runs, which the stubs in the
// describe block below collect: every address site code or a library asks the
// network for, every page code opens without a link, and every file a page
// hands over. blob: addresses map to the files they name.
const blobs = new Map();
const requested = [];
const opened = [];
const handed = [];
const handedUrls = new Set();

// The text a data: address holds, decoded as a browser would.
function dataUrlText(url) {
  const comma = url.indexOf(",");
  const meta = url.slice(0, comma);
  const payload = url.slice(comma + 1);
  let decoded = payload;
  try {
    decoded = decodeURIComponent(payload);
  } catch {
    // A browser keeps a malformed escape as written.
  }
  return /;base64$/i.test(meta)
    ? Buffer.from(decoded, "base64").toString("utf8")
    : decoded;
}

// Notes a file a page hands over or shows from a data: or blob: address, once.
function noteFile(name, url) {
  if (!/^(?:data|blob):/i.test(url) || handedUrls.has(url)) return;
  handedUrls.add(url);
  handed.push(
    url.toLowerCase().startsWith("data:")
      ? { name, text: dataUrlText(url) }
      : { name, blob: blobs.get(url), url },
  );
}

// Notes what a click on an anchor, or inside one, would do: hand over a file,
// or open a page.
function noteAnchor(anchor) {
  if (!anchor) return;
  const url = anchor.getAttribute("href") ?? "";
  if (anchor.hasAttribute("download") || /^(?:data|blob):/i.test(url)) {
    noteFile(anchor.getAttribute("download") ?? "", anchor.href || url);
  } else if (url && !url.startsWith("#")) {
    opened.push(anchor.href || url);
  }
}

// Each base a link on a page can resolve against. policyengine.org drops a
// trailing slash, so the home page sits at the study's address with none,
// while other hosts keep one, so the test resolves against both forms.
function pageUrls(entry) {
  const [path, query] = entry.split("?");
  const search = query === undefined ? "" : `?${query}`;
  const trimmed = path.replace(/\/+$/, "");
  return [
    `${STUDY_URL}${trimmed}${search}`,
    `${STUDY_URL}${trimmed}/${search}`,
  ];
}

// The data: and blob: addresses in an attribute value: the whole value, or a
// CSS url() inside a style.
function embeddedFiles(value) {
  return [
    value.trim(),
    ...[...value.matchAll(/url\(\s*["']?([^"')]+)/gi)].map(([, url]) => url),
  ].filter((url) => /^(?:data|blob):/i.test(url));
}

// Lets the event loop run whatever has queued, such as replies to the worker.
const breathe = () => new Promise((resolve) => setTimeout(resolve, 0));

// Renders a page, works each control and option, and checks the text, title
// and attribute values of every state it reaches. Returns the page's starting
// text, the retired names it found, every link it saw, resolved as on
// policyengine.org, the links into the study resolved as there, the addresses
// it asked the network for, and any field it couldn't fill. It hands the event
// loop a turn before each render, so a long sweep never holds up Vitest's
// messages to its workers past their 60-second timeout.
async function sweep(entry, View) {
  const body = document.body;
  const [page, slashed] = pageUrls(entry);
  requested.length = 0;
  opened.length = 0;
  handedUrls.clear();
  const found = {
    text: "",
    shown: new Set(),
    links: new Set(),
    studyLinks: new Set(),
    requests: [],
    fields: new Set(),
  };
  // Renders the page in a fresh container. Unmounting also removes the
  // container, so the body holds one render at a time and every scan reads
  // only the page in front of it.
  const mount = () => {
    const { unmount, container } = render(
      <MemoryRouter
        basename={STUDY_PATH}
        initialEntries={[`${STUDY_PATH}${entry}`]}
      >
        <View />
      </MemoryRouter>,
    );
    return {
      unmount: () => {
        unmount();
        container.remove();
      },
    };
  };
  const notCountry = (element) => !element.closest(COUNTRY_SWITCH);
  const controls = () =>
    [...body.querySelectorAll("*")].filter(
      (element) =>
        (element.matches(CONTROLS) || handlers(element).size > 0) &&
        !element.matches(NAVIGATES) &&
        notCountry(element),
    );
  const name = (element) =>
    (element.getAttribute("aria-label") ?? element.textContent)
      .trim()
      .slice(0, 40);
  const selects = () => [...body.querySelectorAll("select")].filter(notCountry);
  // Every group that holds one value, in page order: radio groups, tab lists,
  // list boxes and selects, then native radios outside those that share a
  // name. Each knows its options and which controls belong to it.
  const groups = () => {
    const list = [...body.querySelectorAll(SETTERS)]
      .filter(notCountry)
      .map((setter) =>
        setter.matches("select")
          ? {
              key: setter,
              label: name(setter),
              select: setter,
              options: [...setter.options],
              holds: () => false,
            }
          : {
              key: setter,
              label: name(setter),
              options: [...setter.querySelectorAll(SETTER_OPTIONS)],
              holds: (element) =>
                element.matches(SETTER_OPTIONS) &&
                element.closest(SETTERS) === setter,
            },
      );
    const radios = new Map();
    for (const radio of body.querySelectorAll("input[type=radio]")) {
      if (radio.closest(SETTERS) || !notCountry(radio)) continue;
      const key = radio.name || radio;
      radios.set(key, [...(radios.get(key) ?? []), radio]);
    }
    for (const [key, options] of radios) {
      list.push({
        key,
        label: options[0].name,
        options,
        holds: (element) =>
          typeof key === "string"
            ? element.matches("input[type=radio]") &&
              element.name === key &&
              !element.closest(SETTERS)
            : element === key,
      });
    }
    return list;
  };
  const chosen = (group) =>
    group.select
      ? group.select.options[group.select.selectedIndex]
      : group.options.find(
          (option) =>
            option.checked === true ||
            option.getAttribute("aria-checked") === "true" ||
            option.getAttribute("aria-selected") === "true",
        );
  const choose = (group, option) =>
    group.select
      ? fireEvent.change(group.select, { target: { value: option.value } })
      : activate(option, null);
  // Where an element sits under the body, so the same group shown by two
  // routes counts once.
  const domPath = (element) => {
    const parts = [];
    for (let node = element; node && node !== body; node = node.parentElement) {
      parts.push([...node.parentElement.children].indexOf(node));
    }
    return parts.reverse().join(".");
  };
  const groupKey = (group) =>
    [
      typeof group.key === "string" ? `name=${group.key}` : "",
      domPath(group.select ?? group.options[0] ?? body),
      group.label,
      ...group.options.map(name),
    ].join("|");
  // The step that chooses an option of a group: a select's position and the
  // value, or the option's position among the controls shown.
  const stepFor = (group, option) =>
    group.select
      ? { select: selects().indexOf(group.select), value: option.value }
      : controls().indexOf(option);
  // A route's steps for labels: a control's position, or a select's position
  // and the value chosen.
  const trail = (route) =>
    route
      .map((step) =>
        typeof step === "number" ? step : `${step.select}=${step.value}`,
      )
      .join(".");
  const record = (label) => {
    // A data: or blob: address shows its file when a visitor opens it, so
    // the test reads each one, wherever it sits.
    const attributes = [];
    for (const element of body.querySelectorAll("*")) {
      for (const { value } of element.attributes) {
        attributes.push(value);
        for (const url of embeddedFiles(value)) {
          noteFile(element.getAttribute("download") ?? "", url);
        }
      }
    }
    for (const text of [body.textContent, document.title, ...attributes]) {
      if (showsRetiredName(text)) found.shown.add(`${label}: ${excerpt(text)}`);
    }
    for (const element of body.querySelectorAll(LINKING)) {
      const attribute = element.matches("object")
        ? "data"
        : element.matches("form")
          ? "action"
          : element.hasAttribute("href")
            ? "href"
            : "src";
      const target = element.getAttribute(attribute);
      found.links.add(resolve(target, page));
      found.links.add(resolve(target, slashed));
      found.studyLinks.add(resolve(target, page));
    }
    for (const field of body.querySelectorAll(FIELDS)) {
      const label =
        field.getAttribute("aria-label") ??
        field.getAttribute("placeholder") ??
        field.getAttribute("name") ??
        "";
      found.fields.add(
        `${field.tagName.toLowerCase()}[type=${field.getAttribute("type") ?? ""}] ${label}`,
      );
    }
  };
  // Hovers an element that handles a hover and records what that shows, then
  // presses it as a mouse would and records again. Without a label it
  // records nothing, for steps whose states a pass has recorded already.
  const activate = (element, label) => {
    const handled = handlers(element);
    if (hovers(handled)) {
      fireEvent.mouseEnter(element);
      fireEvent.pointerEnter(element);
      fireEvent.mouseMove(element);
      fireEvent.pointerMove(element);
      fireEvent.focus(element);
      if (label) record(`${label}, hover`);
      if (!element.isConnected) return;
    }
    fireEvent.pointerDown(element);
    fireEvent.mouseDown(element);
    fireEvent.pointerUp(element);
    fireEvent.mouseUp(element);
    fireEvent.click(element);
    if (handled.has("onDoubleClick") && element.isConnected) {
      fireEvent.doubleClick(element);
    }
    if (label) record(label);
  };
  // Works every control the page shows, in page order and including any that
  // working another reveals, until none is left. A pass that starts partway
  // along a route counts the route's controls as worked. Returns a route to
  // each control the pass saw but a click hid before the pass reached it,
  // such as the other options of a list that closes once one is chosen: the
  // position of each control worked since the fresh render, among the
  // controls shown at the time, and then the hidden control's own. Given a
  // set of controls to follow, it returns only routes to those and to the
  // controls they reveal, and it adds those to the set. It never works a
  // control that `leave` holds, such as the options of a group whose choice
  // the pass keeps.
  // Given a list for reveals, the pass also adds a route to each group that a
  // step shows, with the group's place among the groups that route shows, for
  // the option passes below. A group counts as shown by a step unless it was
  // in `shownBefore`, which defaults to the groups shown when the pass began.
  const clickAll = (
    pass,
    {
      route = [],
      worked = [],
      follows = null,
      leave = () => false,
      reveals = null,
      shownBefore = groups().map((group) => group.key),
    } = {},
  ) => {
    const clicked = new Set(worked);
    const steps = [...route];
    const unreached = new Map();
    const known = new Set(shownBefore);
    let last = null;
    for (let shown = controls(); ; shown = controls()) {
      shown.forEach((element, position) => {
        if (clicked.has(element) || unreached.has(element)) return;
        if (leave(element)) return;
        unreached.set(element, [...steps, position]);
        if (follows?.has(last)) follows.add(element);
      });
      if (reveals) {
        groups().forEach((group, index) => {
          if (known.has(group.key)) return;
          known.add(group.key);
          reveals.push({ route: [...steps], index, key: groupKey(group) });
        });
      }
      const control = shown.find((next) => !clicked.has(next) && !leave(next));
      if (!control) break;
      if (clicked.size - worked.length === MAX_CLICKS_PER_PASS) {
        throw new Error(
          `${entry}, ${pass}: over ${MAX_CLICKS_PER_PASS} clicks`,
        );
      }
      steps.push(shown.indexOf(control));
      clicked.add(control);
      unreached.delete(control);
      activate(control, `${pass}, control ${clicked.size - worked.length}`);
      last = control;
    }
    return [...unreached]
      .filter(([element]) => !follows || follows.has(element))
      .map(([, hidden]) => hidden);
  };
  // From a fresh render, takes each step along a route, working a control or
  // choosing a select's value, and records the state the last step leaves.
  // Returns the controls it worked and the ones the last step revealed.
  // It also returns the groups shown before the last step, so a pass from
  // there can tell which groups that step revealed.
  const follow = (route) => {
    const worked = [];
    let before = [];
    let shownBefore = groups().map((group) => group.key);
    route.forEach((step, index) => {
      before = controls();
      shownBefore = groups().map((group) => group.key);
      const label = index === route.length - 1 ? `route ${trail(route)}` : null;
      const missing = () =>
        new Error(`${entry}: route ${trail(route)} fails at step ${index + 1}`);
      if (typeof step === "number") {
        const control = before[step];
        if (!control) throw missing();
        worked.push(control);
        activate(control, label);
        return;
      }
      const select = selects()[step.select];
      if (!select) throw missing();
      fireEvent.change(select, { target: { value: step.value } });
      if (label) record(label);
    });
    const revealed = new Set(controls());
    for (const element of before) revealed.delete(element);
    return { worked, revealed, shownBefore };
  };

  let { unmount } = mount();
  found.text = body.textContent;
  record("initial");
  // Groups a step reveals get option passes of their own below, once each.
  const optioned = new Set(groups().map(groupKey));
  const reveals = [];
  const routes = clickAll("first pass", { reveals });
  for (const group of groups().filter((group) => group.select)) {
    for (const option of group.options) {
      if (!group.select.isConnected) break;
      choose(group, option);
      record(`${group.label} = ${option.value}`);
    }
  }
  clickAll("second pass");
  unmount();

  // From a fresh render, follows a route to where a group shows, chooses one
  // of its options and runs a pass that leaves the group alone, so every
  // other control gets worked with that option chosen, as with tabs that
  // share one details button.
  const optionPass = (route, index, position) => {
    ({ unmount } = mount());
    const { worked } = follow(route);
    const group = groups()[index];
    const option = group?.options[position];
    if (!option) {
      throw new Error(`${entry}: route ${trail(route)} lost group ${index}`);
    }
    const step = stepFor(group, option);
    const label = `${route.length ? `route ${trail(route)}, ` : ""}${group.label} = ${name(option)}`;
    const before = controls();
    const shownBefore = groups().map((shown) => shown.key);
    if (typeof step === "number") {
      worked.push(option);
      activate(option, label);
    } else {
      choose(group, option);
      record(label);
    }
    const revealed = new Set(controls());
    for (const element of before) revealed.delete(element);
    routes.push(
      ...clickAll(label, {
        route: [...route, step],
        worked,
        follows: revealed,
        leave: group.holds,
        reveals,
        shownBefore,
      }),
    );
    unmount();
  };

  // Each option of every group the page starts with.
  ({ unmount } = mount());
  const sizes = groups().map((group) => group.options.length);
  unmount();
  for (let index = 0; index < sizes.length; index += 1) {
    for (let position = 0; position < sizes[index]; position += 1) {
      await breathe();
      optionPass([], index, position);
    }
  }

  // A pass saw each control in `routes` but hid it before reaching it. Each
  // gets a fresh render that works its way back to the control, works it,
  // and then runs a pass of its own. That pass adds a route to any control
  // the hidden one revealed and the pass hid in turn. Once no route is left,
  // each group a step revealed gets the option passes the starting groups
  // got, which can add routes and reveals of their own.
  let renders = 0;
  const counted = () => {
    renders += 1;
    if (renders > MAX_ROUTES) {
      throw new Error(`${entry}: over ${MAX_ROUTES} routes`);
    }
  };
  for (let nextRoute = 0, nextReveal = 0; ; ) {
    await breathe();
    if (nextRoute < routes.length) {
      counted();
      const route = routes[nextRoute];
      nextRoute += 1;
      ({ unmount } = mount());
      const { worked, revealed, shownBefore } = follow(route);
      routes.push(
        ...clickAll(`after route ${trail(route)}`, {
          route,
          worked,
          follows: revealed,
          reveals,
          shownBefore,
        }),
      );
      unmount();
      continue;
    }
    if (nextReveal === reveals.length) break;
    const { route, index, key } = reveals[nextReveal];
    nextReveal += 1;
    if (optioned.has(key)) continue;
    optioned.add(key);
    ({ unmount } = mount());
    follow(route);
    const size = groups()[index].options.length;
    unmount();
    for (let position = 0; position < size; position += 1) {
      counted();
      await breathe();
      optionPass(route, index, position);
    }
  }

  // Pairs each option of every group the page starts with with each option of
  // every other group shown alongside it. Each first group gets a fresh
  // render, and each second group returns to its starting option before the
  // next one, so no choice hides the groups after it.
  for (let first = 0; first < sizes.length; first += 1) {
    await breathe();
    ({ unmount } = mount());
    const group = groups()[first];
    for (const option of group.options) {
      choose(group, option);
      const firstChoice = `${group.label} = ${name(option)}`;
      record(firstChoice);
      const shown = groups().length;
      for (let index = 0; index < shown; index += 1) {
        const other = groups()[index];
        if (!other || other.key === group.key) continue;
        const start = chosen(other);
        for (const second of other.options) {
          if (!second.isConnected) break;
          choose(other, second);
          record(`${firstChoice}, ${other.label} = ${name(second)}`);
        }
        if (start?.isConnected) choose(other, start);
      }
    }
    unmount();
  }

  // Pages code opened and addresses it asked for, resolved as on
  // policyengine.org.
  for (const url of opened.splice(0)) {
    found.links.add(resolve(url, page));
    found.links.add(resolve(url, slashed));
    found.studyLinks.add(resolve(url, page));
  }
  found.requests = requested.splice(0).map((url) => resolve(url, page));
  return found;
}

// The text of a file a page handed over as a download.
const blobText = (blob) =>
  new Promise((done, fail) => {
    const reader = new FileReader();
    reader.onload = () => done(reader.result);
    reader.onerror = () => fail(reader.error);
    reader.readAsText(blob);
  });

describe("retired dataset names", () => {
  // Every request a page makes, every page it opens without a link and every
  // file it hands over reaches the test instead of the browser. Requests never
  // settle, so the uprating explorer stays loading; the tests below read the
  // table it would fetch directly.
  const { createObjectURL, revokeObjectURL } = URL;
  const { dispatchEvent } = EventTarget.prototype;
  const { open, send } = XMLHttpRequest.prototype;
  const urlOf = (input) => String(input?.url ?? input);
  class Connection {
    constructor(url) {
      requested.push(urlOf(url));
    }
    addEventListener() {}
    removeEventListener() {}
    send() {}
    close() {}
  }
  beforeAll(() => {
    vi.stubGlobal("fetch", (input) => {
      requested.push(urlOf(input));
      return new Promise(() => {});
    });
    vi.stubGlobal("WebSocket", Connection);
    vi.stubGlobal("EventSource", Connection);
    XMLHttpRequest.prototype.open = function record(method, url) {
      requested.push(urlOf(url));
    };
    XMLHttpRequest.prototype.send = () => {};
    Object.defineProperty(navigator, "sendBeacon", {
      configurable: true,
      value: (url) => {
        requested.push(urlOf(url));
        return true;
      },
    });
    vi.spyOn(window, "open").mockImplementation((url) => {
      opened.push(urlOf(url ?? ""));
      return null;
    });
    URL.createObjectURL = (blob) => {
      const url = `blob:${STUDY_URL}/download-${blobs.size + 1}`;
      blobs.set(url, blob);
      return url;
    };
    URL.revokeObjectURL = () => {};
    for (const Anchor of [HTMLAnchorElement, HTMLAreaElement]) {
      vi.spyOn(Anchor.prototype, "click").mockImplementation(function save() {
        noteAnchor(this);
      });
    }
    // A click event dispatched on an anchor, or on anything inside one, does
    // what the anchor's click() would, even when the anchor isn't on the page.
    EventTarget.prototype.dispatchEvent = function noted(event) {
      if (event.type === "click" && this instanceof Element) {
        noteAnchor(this.closest("a[href],area[href]"));
      }
      return dispatchEvent.call(this, event);
    };
  });
  afterAll(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    Object.assign(URL, { createObjectURL, revokeObjectURL });
    Object.assign(XMLHttpRequest.prototype, { open, send });
    EventTarget.prototype.dispatchEvent = dispatchEvent;
    delete navigator.sendBeacon;
  });

  // The files a sweep's pages handed over or showed through data: and blob:
  // addresses, each with its text, and any that shows a retired name or that
  // the test couldn't read.
  async function handedOver() {
    const files = await Promise.all(
      handed.splice(0).map(async ({ name, text, blob, url }) => ({
        name,
        url,
        text: text ?? (blob ? await blobText(blob) : null),
      })),
    );
    return {
      files,
      shown: files.flatMap(({ name, url, text }) => {
        if (text === null) return [`${name || url}: unreadable`];
        const shows = [name, text, markupText(text)].find(showsRetiredName);
        return shows === undefined ? [] : [`${name}: ${excerpt(shows)}`];
      }),
    };
  }

  it("renders every route App.jsx declares, and the app serves no other page", () => {
    expect(ROUTES.length).toBeGreaterThan(0);
    expect(ROUTES.length).toBe((read(APP).match(/<Route\b/g) ?? []).length);
    expect(ROUTES.filter(({ path, View }) => !path || !View)).toEqual([]);
    // A wildcard or a parameter would serve paths the test never renders,
    // and the behavior test fails on routing outside App.jsx.
    expect(ROUTES.filter(({ path }) => /[*:]/.test(path))).toEqual([]);
    // Next.js serves the router app from one catch-all page.
    expect(
      pathsUnder("app").filter((path) =>
        /(?:^|\/)(?:page|route)\.[cm]?[jt]sx?$/.test(path),
      ),
    ).toEqual(["app/[[...slug]]/page.jsx"]);
  });

  it("finds press and hover handlers on elements that declare no role", () => {
    render(
      <div>
        <div className="card" onClick={() => {}}>
          Card
        </div>
        <span onMouseEnter={() => {}}>Tip</span>
        <p>Text</p>
      </div>,
    );
    const handled = (selector) => [
      ...handlers(document.body.querySelector(selector)),
    ];
    expect([handled(".card"), handled("span"), handled("p")]).toEqual([
      ["onClick"],
      ["onMouseEnter"],
      [],
    ]);
  });

  it("reads a fetch's file from the call or from a string constant", () => {
    const constants = new Map([
      ["TABLE", new Set(["/data/table.csv"])],
      ["SPLIT", new Set(["/data/a.csv", "/data/b.csv"])],
    ]);
    const file = (call) =>
      fetchedFile([...call.matchAll(SERVED_FETCH)][0], constants);
    expect([
      file('fetch(withBasePath("/data/x.csv"))'),
      file("fetch(withBasePath(TABLE))"),
      file("fetch(withBasePath(SPLIT))"),
      file("fetch(withBasePath(MISSING))"),
    ]).toEqual(["/data/x.csv", "/data/table.csv", null, null]);
  });

  it("counts a request word in code, strings and copy but not in comments", () => {
    const requests = (source) =>
      (withoutComments(source).match(REQUESTS) ?? []).length;
    expect([
      requests("// the fetch.\nconst a = 1;"),
      requests("const a = 1; /* fetch it */"),
      requests("const Page = () => <p>{/* fetch */}Text</p>;"),
      requests('const url = "https://x.test/a"; fetch(url);'),
      requests('window["fetch"]("/data/x.csv");'),
      requests("const Page = () => <p>We fetch the table.</p>;"),
      requests("const a: number = 1; // the fetch."),
    ]).toEqual([0, 0, 0, 1, 1, 1, 1]);
  });

  it("gives each option of a group that a step reveals a pass of its own", async () => {
    // Shows a retired name only with the second tab chosen and the details
    // open, and choosing a tab closes the details. The tabs appear only after
    // a click, so the passes for starting groups never hold the second tab.
    const hidden = ["popu", "lace"].join("");
    function RevealedTabs() {
      const [open, setOpen] = useState(false);
      const [tab, setTab] = useState("one");
      const [details, setDetails] = useState(false);
      return (
        <div>
          <button
            type="button"
            aria-expanded={open}
            onClick={() => setOpen(!open)}
          >
            Tabs
          </button>
          {open && (
            <div>
              <div role="tablist" aria-label="Tabs">
                {["one", "two", "three"].map((key) => (
                  <button
                    key={key}
                    type="button"
                    role="tab"
                    aria-selected={tab === key}
                    onClick={() => {
                      setTab(key);
                      setDetails(false);
                    }}
                  >
                    {key}
                  </button>
                ))}
              </div>
              <button type="button" onClick={() => setDetails(true)}>
                Details
              </button>
              {details && tab === "two" && <p>{hidden}</p>}
            </div>
          )}
        </div>
      );
    }
    expect([...(await sweep("/", RevealedTabs)).shown].length).toBeGreaterThan(
      0,
    );
  });

  it("reads every file a page hands over or shows from a data: or blob: address", async () => {
    const json = (label) => JSON.stringify({ label });
    const save = (href, how) => {
      const link = document.createElement("a");
      link.href = href;
      link.download = `${how}.json`;
      if (how === "dispatched") link.dispatchEvent(new MouseEvent("click"));
      else link.click();
    };
    const asData = (text) =>
      `data:application/json;charset=utf-8,${encodeURIComponent(text)}`;
    const asBase64 = (text) =>
      `data:application/json;base64,${Buffer.from(text).toString("base64")}`;
    const asBlob = (text) => URL.createObjectURL(new Blob([text]));
    function Downloads() {
      const rendered = useMemo(() => asBlob(json("rendered blob")), []);
      return (
        <div>
          <button
            type="button"
            onClick={() => save(asBlob(json("clicked blob")), "clicked")}
          >
            Blob
          </button>
          <button
            type="button"
            onClick={() => save(asData(json("clicked data")), "data")}
          >
            Data
          </button>
          <button
            type="button"
            onClick={() => save(asBlob(json("dispatched blob")), "dispatched")}
          >
            Dispatched
          </button>
          <a href={rendered} download="rendered.json">
            Rendered blob
          </a>
          <a href={asBase64(json("rendered base64"))} download="base64.json">
            Rendered data
          </a>
          <span
            style={{ backgroundImage: `url(${asData(json("style data"))})` }}
          />
        </div>
      );
    }
    await sweep("/", Downloads);
    const { files } = await handedOver();
    const labels = files.map(({ text }) => JSON.parse(text).label);
    expect([...new Set(labels)].sort()).toEqual([
      "clicked blob",
      "clicked data",
      "dispatched blob",
      "rendered base64",
      "rendered blob",
      "style data",
    ]);
  });

  it("catches every request a page makes and every page it opens without a link", async () => {
    function Requests() {
      return (
        <button
          type="button"
          onClick={() => {
            fetch("https://example.test/fetch");
            const request = new XMLHttpRequest();
            request.open("GET", "https://example.test/xhr");
            request.send();
            new WebSocket("wss://example.test/socket");
            new EventSource("https://example.test/events");
            navigator.sendBeacon("https://example.test/beacon");
            window.open("https://github.com/PolicyEngine");
          }}
        >
          Load
        </button>
      );
    }
    const { requests, links } = await sweep("/", Requests);
    expect([...new Set(requests)]).toEqual([
      "https://example.test/fetch",
      "https://example.test/xhr",
      "wss://example.test/socket",
      "https://example.test/events",
      "https://example.test/beacon",
    ]);
    expect([...links].filter(linksRetiredPage)).toEqual([
      "https://github.com/PolicyEngine",
    ]);
    expect(
      [
        `${STUDY_URL}/data/uprating_analysis.csv`,
        `${STUDY_URL}/data/missing.csv`,
        "https://raw.githubusercontent.com/PolicyEngine/ai-inequality/main/public/data/uprating_analysis.csv",
      ].map(servesFile),
    ).toEqual([true, false, false]);
  });

  it("resolves the home page's relative links without a trailing slash, as policyengine.org serves it", async () => {
    function Home() {
      return <a href="research">Research</a>;
    }
    expect(
      [...(await sweep("/", Home)).links].filter(linksRetiredPage),
    ).toEqual(["https://policyengine.org/us/research"]);
  });

  it("tells a link into a page the test renders from one into a state the sweep never reached", () => {
    expect(
      [
        `${STUDY_URL}`,
        `${STUDY_URL}/`,
        `${STUDY_URL}/research`,
        `${STUDY_URL}/research/`,
        `${STUDY_URL}/income-shift?country=uk`,
        "https://www.policyengine.org/uk/ai-inequality/income-shift",
        `${STUDY_URL}/references#bibtex`,
        `${STUDY_URL}/data/uprating_analysis.csv`,
        `${STUDY_URL}/ai-inequality`,
        "https://policyengine.org/us/research",
        `${STUDY_URL}/?sources=all`,
        `${STUDY_URL}/income-shift?country=ca`,
        `${STUDY_URL}/income-shift?country=uk&tab=2`,
        `${STUDY_URL}/research/data-sources`,
        `${STUDY_URL}/data/uprating_analysis.csv?v=2`,
      ].map(opensUnrenderedPage),
    ).toEqual([
      false,
      false,
      false,
      false,
      false,
      false,
      false,
      false,
      false,
      false,
      true,
      true,
      true,
      true,
      false,
    ]);
  });

  it("flags code that could show a visitor what the sweep never reaches", () => {
    const flags = (source, path = "src/components/Example.jsx") =>
      unsweptBehavior(path, source).map((finding) =>
        finding.replace(/^[^:]+:\d+: /, ""),
      );
    expect([
      flags("setTimeout(() => show(true), 300);"),
      flags('const Section = React.lazy(() => import("./Section"));'),
      flags(
        "const Page = () => <Suspense fallback={null}><Section /></Suspense>;",
      ),
      flags("Promise.resolve().then(show);"),
      flags("async function load() { await wait(); }"),
      flags(
        'fetch(withBasePath("/data/x.csv")).then((r) => r.text()).catch(fail);',
      ),
      flags("const pick = (event) => show(event.target.dataset.detail);"),
      flags("const pick = (event) => show(event.target.value);"),
      flags(
        "const Tab = () => <button onKeyDown={nav.keyDownHandler(set)} onClick={pick} />;",
      ),
      flags("const Tab = () => <button onKeyUp={pick} />;"),
      flags('const Link = () => <a href="/x" onClick={show}>x</a>;'),
      flags(
        'const Link = () => <a href="/x" onClick={(e) => e.stopPropagation()}>x</a>;',
      ),
      flags(
        'const View = () => <Routes><Route path="x" element={<X />} /></Routes>;',
      ),
      flags(
        'const View = () => <Routes><Route path="x" element={<X />} /></Routes>;',
        APP,
      ),
      flags('window.location.href = "https://github.com/PolicyEngine";'),
      flags("const tab = useLocation().hash;"),
      flags('window.addEventListener("scroll", show);'),
      flags(
        'const App = dynamic(() => import("./App"), { ssr: false });',
        "src/ClientAppRouter.jsx",
      ),
      flags("const options = { lazy: true, hash: 1 };"),
      flags("const Page = () => <p>We await a lazy promise.</p>;"),
    ]).toEqual([
      ["defers rendering (setTimeout)"],
      ["defers rendering (lazy)", "defers rendering (import())"],
      ["defers rendering (Suspense)", "defers rendering (Suspense)"],
      ["defers rendering (a promise)", "defers rendering (Promise)"],
      ["defers rendering (async)", "defers rendering (async)"],
      [],
      ["reads more of an event's target than the sweep sets"],
      [],
      [],
      ["handles an event the sweep never fires (onKeyUp)"],
      ["a link handles an event, and the sweep never works links"],
      [],
      [
        "routes outside App.jsx (Routes)",
        "routes outside App.jsx (Routes)",
        "routes outside App.jsx (Route)",
      ],
      [],
      ["navigates without a link (location.href)"],
      ["reacts to input the sweep never gives (hash)"],
      ["reacts to input the sweep never gives (addEventListener)"],
      [],
      [],
      [],
    ]);
  });

  it.each(PAGES)(
    "%s shows none in any state and links no page that does",
    async (entry, View) => {
      const { text, shown, links, studyLinks, requests, fields } = await sweep(
        entry,
        View,
      );
      expect(text.length).toBeGreaterThan(200);
      expect([...shown]).toEqual([]);
      expect([...links].filter(linksRetiredPage)).toEqual([]);
      expect([...studyLinks].filter(opensUnrenderedPage)).toEqual([]);
      expect(requests.filter((url) => !servesFile(url))).toEqual([]);
      expect([...fields]).toEqual([]);
      expect((await handedOver()).shown).toEqual([]);
    },
    120_000,
  );

  it("reads the file a download hands over, such as the references' BibTeX", async () => {
    const references = ROUTES.find(({ path }) => path === "/references");
    await sweep("/references", references.View);
    const { files, shown } = await handedOver();
    expect(files.length).toBeGreaterThan(0);
    expect(files[0].text.length).toBeGreaterThan(1000);
    expect(shown).toEqual([]);
  }, 120_000);

  it("shows none in the shared header and footer in any state, which link only the known pages that do", async () => {
    // app/layout.jsx wraps every page in the US shell.
    expect(
      [
        ...read("app/layout.jsx").matchAll(
          /<PolicyEngineShell\b[^>]*?\bcountry="(\w+)"/g,
        ),
      ].map(([, country]) => country),
    ).toEqual(["us"]);
    const Shell = () => (
      <PolicyEngineShell country="us">
        <p>Page</p>
      </PolicyEngineShell>
    );
    const { shown, links, requests } = await sweep("/", Shell);
    expect([...shown]).toEqual([]);
    expect([...links].filter(linksRetiredPage).sort()).toEqual(
      SHELL_LINKS_TO_RETIRED_PAGES,
    );
    expect(requests.filter((url) => !servesFile(url))).toEqual([]);
    expect((await handedOver()).shown).toEqual([]);
  }, 120_000);

  it("stays out of the generated memo", () => {
    expect(memoMarkdown.length).toBeGreaterThan(1000);
    expect(normalize(memoMarkdown)).not.toMatch(RETIRED);
  });

  it("stays out of site code, copy and text assets", () => {
    expect(
      siteText.filter((path) => {
        const text = sourceText(path);
        return (
          showsRetiredName(text) ||
          (MARKUP.test(path) && showsRetiredName(markupText(text)))
        );
      }),
    ).toEqual([]);
  });

  it("stays out of everything the site serves", () => {
    expect(
      ["public", "src", "app"].flatMap((dir) => symlinksUnder(dir)),
    ).toEqual([]);
    expect(servedFiles.filter((path) => showsRetiredName(path))).toEqual([]);
    expect(
      [...publicFiles, ...siteFiles].filter(
        (path) => isUnreadable(path) && !CHECKED_DOCUMENTS.includes(path),
      ),
    ).toEqual([]);
    expect(
      publicText.filter((path) => {
        const text = read(path);
        return (
          showsRetiredName(text) ||
          (MARKUP.test(path) && showsRetiredName(markupText(text)))
        );
      }),
    ).toEqual([]);
  });

  it("links no page that shows one from code, data or public files", () => {
    const sources = new Set([
      ...siteText,
      ...pathsUnder("src/data"),
      ...publicText,
    ]);
    expect(
      [...new Set([...sources].flatMap(linksIn))].filter(linksRetiredPage),
    ).toEqual([]);
  });

  // A page shows only what the bundle holds or what it fetches, and the tests
  // above read both.
  it("fetches only files that public/ serves", () => {
    const codeByPath = siteCode.map((path) => [
      path,
      withoutComments(read(path)),
    ]);
    const constants = new Map();
    for (const [, code] of codeByPath) {
      for (const [, name, value] of code.matchAll(STRING_CONSTANT)) {
        constants.set(name, (constants.get(name) ?? new Set()).add(value));
      }
    }
    expect(
      codeByPath.flatMap(([path, code]) => {
        const requests = (code.match(REQUESTS) ?? []).length;
        const served = [...code.matchAll(SERVED_FETCH)].filter((match) => {
          const file = fetchedFile(match, constants);
          return file !== null && publicFiles.includes(`public${file}`);
        }).length;
        return requests === served
          ? []
          : [
              `${path}: ${requests} requests, ${served} for files public/ serves`,
            ];
      }),
    ).toEqual([]);
  });

  // The sweep renders each page, works it and records each state at once.
  // Code that changes a page later, or on input the sweep never gives, could
  // show a visitor a state the sweep never reached.
  it("shows nothing the sweep can't reach", () => {
    const running = runningModules();
    // The pages reach the router app and every view it routes to.
    expect(
      [
        APP,
        ...ROUTES.map(({ View }) =>
          Object.keys(VIEW_MODULES)
            .find((module) => VIEW_MODULES[module].default === View)
            .replace(/^\.\//, "src/"),
        ),
      ].filter((path) => !running.has(path)),
    ).toEqual([]);
    expect(
      [...running].flatMap((path) => unsweptBehavior(path, read(path))),
    ).toEqual([]);
  });

  it("reads frozen ids only where a page labels them", () => {
    const keys = new Set();
    const collect = (value, key) => {
      if (typeof value === "string") {
        if (showsRetiredName(value)) keys.add(key);
      } else if (Array.isArray(value)) {
        value.forEach((item) => collect(item, key));
      } else if (value && typeof value === "object") {
        Object.entries(value).forEach(([k, v]) => collect(v, k));
      }
    };
    pathsUnder("src/data")
      .filter((path) => path.endsWith(".json"))
      .forEach((path) => collect(JSON.parse(read(path))));

    const escape = (text) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const keyPattern = (key) => new RegExp(`\\b${escape(key)}\\b`);
    const allowed = (path, key) =>
      ALLOWED_READS.some((entry) => entry.path === path && entry.key === key);
    const reads = siteText
      .filter((path) => !path.startsWith("src/data/"))
      .flatMap((path) => {
        const code = read(path);
        return [...keys]
          .filter((key) => keyPattern(key).test(code) && !allowed(path, key))
          .map((key) => `${path}: ${key}`);
      });
    expect(reads).toEqual([]);

    // Each allowed key appears only inside its call, so the page prints the
    // label and never the id.
    for (const { path, key, call } of ALLOWED_READS) {
      const code = read(path);
      const mentions = code.split(keyPattern(key)).length - 1;
      const calls = code.split(call).length - 1;
      expect(`${path}: ${key} x${mentions}`).toBe(`${path}: ${key} x${calls}`);
    }
  });
});
