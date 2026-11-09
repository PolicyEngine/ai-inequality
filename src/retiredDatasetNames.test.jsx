import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

import { PolicyEngineShell } from "@policyengine/ui-kit/layout";
import { fireEvent, render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";

import { memoMarkdown } from "./data/memoContent";
import BudgetLabMemo from "./views/BudgetLabMemo";
import Home from "./views/Home";
import IncomeShift from "./views/IncomeShift";
import PolicyAnalysis from "./views/PolicyAnalysis";
import References from "./views/References";
import ResearchPage from "./views/Research";

// Microcosm's pre-August name and the dataset it replaced as the default, in
// the spellings they take in prose, release ids and package names. Published
// ids keep the old spelling in data and code; pages never show them.
const RETIRED =
  /populace|enhanced[\s_-]*(?:cps|current[\s_-]*population[\s_-]*survey)|\be[\s_-]?cps\b|policyengine[\s_-]*us[\s_-]*data/i;

// Exact phrases that match RETIRED but name no dataset, such as a reference
// title that uses the English noun. Add one only after reading it in context.
const ALLOWED_PHRASES = [];

// Pages that show a retired name today. Remove an entry once its page stops.
const PAGES_SHOWING_RETIRED_NAMES = [
  // The org page renders PolicyEngine/.github's profile README, which lists
  // the earlier dataset's repository.
  /^https?:\/\/(?:www\.)?github\.com\/PolicyEngine\/?(?:[?#]|$)/i,
  // Their READMEs print Microcosm's release ids or link its pre-August pages.
  /^https?:\/\/(?:www\.)?github\.com\/PolicyEngine\/(?:microcosm|policyengine-us)\/?(?:[?#]|$)/i,
  // The landing site's home page names both.
  /^https?:\/\/(?:www\.)?microcosm\.institute(?:[/?#]|$)/i,
  // The Python page's example loads the earlier dataset, and the model docs'
  // pipeline diagram names it.
  /^https?:\/\/(?:www\.)?policyengine\.org\/us\/(?:python|model\/data\/pipeline)\/?(?:[?#]|$)/i,
  // The research listing shows a card for a post that names the earlier
  // dataset.
  /^https?:\/\/(?:www\.)?policyengine\.org\/us\/research\/?(?:[?#]|$)/i,
];

// Links in @policyengine/ui-kit's shared header and footer, which wrap every
// page here as on policyengine.org, that open a page listed above. Remove one
// once its page stops showing a retired name.
const SHELL_LINKS_TO_RETIRED_PAGES = [
  "https://policyengine.org/us/research",
  "https://policyengine.org/us/python",
];

const ROOT = process.cwd();

function pathsUnder(dir) {
  return readdirSync(join(ROOT, dir), { recursive: true, withFileTypes: true })
    .filter((entry) => entry.isFile())
    .map((entry) => join(entry.parentPath, entry.name).slice(ROOT.length + 1));
}

const read = (path) => readFileSync(join(ROOT, path), "utf8");

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

// The one module that recognizes the frozen release-id prefix, and the one
// token in it that may spell the old name.
const RELEASE_ID_PARSER = "src/utils/modelMetadata.js";
const RELEASE_ID_PREFIX = "(?:microcosm|populace)-us-";

const siteCode = [...pathsUnder("src"), ...pathsUnder("app")].filter(
  (path) =>
    /\.(?:jsx?|mjs|tsx?|css)$/.test(path) && !/\.test\.jsx?$/.test(path),
);

const sourceText = (path) =>
  path === RELEASE_ID_PARSER
    ? read(path).replace(RELEASE_ID_PREFIX, "")
    : read(path);

// Media can show text too, but this test can't read pixels, so check new images
// by eye. Documents and archives hold text it can't parse, so each needs a
// reviewed entry.
const MEDIA =
  /\.(?:png|jpe?g|gif|webp|avif|bmp|ico|woff2?|ttf|otf|eot|mp3|mp4|webm|mov|wav)$/i;
const DOCUMENTS =
  /\.(?:pdf|docx?|pptx?|xlsx?|odt|odp|ods|epub|zip|gz|tgz|tar|7z|rar|bz2|xz)$/i;
// Documents in public/ that someone has read in full and found clean.
const CHECKED_DOCUMENTS = [];
const MARKUP = /\.(?:html?|svg|xml)$/i;

const publicFiles = pathsUnder("public");
const publicText = publicFiles.filter(
  (path) => !MEDIA.test(path) && !DOCUMENTS.test(path),
);

const URL_PATTERN = /https?:\/\/[^\s"'`<>()\\]+/g;

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

// Toggles and disclosure controls that change what a page shows, and anything
// styled with a pointer cursor, such as the research page's expandable cards.
const CONTROLS = [
  "button[aria-pressed]",
  "button[aria-expanded]",
  "[role=radio]",
  "[role=tab]",
  "[role=switch]",
  "[role=checkbox]",
  "input[type=radio]",
  "input[type=checkbox]",
  '[style*="cursor: pointer"]',
].join(",");

// Radio groups, tab lists and selects each hold one value, and choosing one of
// their options sets that value whatever the page showed before.
const SETTERS = "[role=radiogroup],[role=tablist],select";

// The country switch swaps the whole page. PAGES renders each country on its
// own, so the sweep leaves the switch alone.
const COUNTRY_SWITCH = '[role=radiogroup][aria-label="Country"]';

// A pass that needs more clicks than this has met a control that remounts the
// others on every click, so it fails instead of looping.
const MAX_CLICKS_PER_PASS = 500;

// Renders a page, works each control and option, and checks the text, title
// and attribute values of every state it reaches. Returns the page's starting
// text, the retired names it found, and every link it saw.
function sweep(entry, View) {
  const body = document.body;
  const found = { text: "", shown: new Set(), links: new Set() };
  const mount = () =>
    render(
      <MemoryRouter initialEntries={[entry]}>
        <View />
      </MemoryRouter>,
    );
  const notCountry = (element) => !element.closest(COUNTRY_SWITCH);
  const controls = () =>
    [...body.querySelectorAll(CONTROLS)].filter(notCountry);
  const setters = () => [...body.querySelectorAll(SETTERS)].filter(notCountry);
  const isSelect = (setter) => setter.matches("select");
  const options = (setter) =>
    isSelect(setter)
      ? [...setter.options]
      : [...setter.querySelectorAll("[role=radio],[role=tab]")];
  const chosen = (setter) =>
    isSelect(setter)
      ? setter.options[setter.selectedIndex]
      : options(setter).find(
          (option) =>
            option.getAttribute("aria-checked") === "true" ||
            option.getAttribute("aria-selected") === "true",
        );
  const choose = (setter, option) =>
    isSelect(setter)
      ? fireEvent.change(setter, { target: { value: option.value } })
      : fireEvent.click(option);
  const name = (element) =>
    (element.getAttribute("aria-label") ?? element.textContent)
      .trim()
      .slice(0, 40);
  const record = (label) => {
    const attributes = [...body.querySelectorAll("*")].flatMap((element) =>
      [...element.attributes].map((attribute) => attribute.value),
    );
    for (const text of [body.textContent, document.title, ...attributes]) {
      if (showsRetiredName(text)) found.shown.add(`${label}: ${excerpt(text)}`);
    }
    for (const link of body.querySelectorAll("a[href]")) {
      found.links.add(link.getAttribute("href"));
    }
  };
  // Clicks every control the page shows, in page order and including any a
  // click reveals, until none is left unclicked. Returns the positions of the
  // starting controls that a click hid before the pass reached them.
  const clickAll = (pass) => {
    const start = controls();
    const clicked = new Set();
    let control = start[0];
    while (control) {
      if (clicked.size === MAX_CLICKS_PER_PASS) {
        throw new Error(
          `${entry}, ${pass}: over ${MAX_CLICKS_PER_PASS} clicks`,
        );
      }
      clicked.add(control);
      fireEvent.click(control);
      record(`${pass}, click ${clicked.size}`);
      control = controls().find((next) => !clicked.has(next));
    }
    return start.flatMap((first, index) => (clicked.has(first) ? [] : [index]));
  };

  let { unmount } = mount();
  found.text = body.textContent;
  record("initial");
  const hidden = clickAll("first pass");
  for (const select of setters().filter(isSelect)) {
    for (const option of options(select)) {
      if (!select.isConnected) break;
      choose(select, option);
      record(`${name(select)} = ${option.value}`);
    }
  }
  clickAll("second pass");
  unmount();

  // The first pass missed these, so each gets a fresh render, where it sits in
  // the same position, and a pass of its own after it.
  for (const index of hidden) {
    ({ unmount } = mount());
    fireEvent.click(controls()[index]);
    record(`fresh render, control ${index}`);
    clickAll(`after control ${index}`);
    unmount();
  }

  // Pairs each option of every group the page starts with with each option of
  // every other group shown alongside it. Each first group gets a fresh
  // render, and each second group returns to its starting option before the
  // next one, so no choice hides the groups after it.
  ({ unmount } = mount());
  const groups = setters().length;
  unmount();
  for (let first = 0; first < groups; first += 1) {
    ({ unmount } = mount());
    const group = setters()[first];
    for (const option of options(group)) {
      choose(group, option);
      const firstChoice = `${name(group)} = ${name(option)}`;
      record(firstChoice);
      const shown = setters().length;
      for (let index = 0; index < shown; index += 1) {
        const other = setters()[index];
        if (!other || other === group) continue;
        const start = chosen(other);
        for (const second of options(other)) {
          if (!second.isConnected) break;
          choose(other, second);
          record(`${firstChoice}, ${name(other)} = ${name(second)}`);
        }
        if (start?.isConnected) choose(other, start);
      }
    }
    unmount();
  }
  return found;
}

const PAGES = [
  ["/", Home],
  ["/?country=uk", Home],
  ["/research", ResearchPage],
  ["/research?country=uk", ResearchPage],
  ["/policy-analysis", PolicyAnalysis],
  ["/policy-analysis?country=uk", PolicyAnalysis],
  ["/income-shift", IncomeShift],
  ["/income-shift?country=uk", IncomeShift],
  ["/references", References],
  ["/budget-lab", BudgetLabMemo],
];

describe("retired dataset names", () => {
  // The uprating explorer fetches its table from public/, which the tests
  // below read directly, so the sweep leaves the explorer loading.
  beforeAll(() => {
    vi.stubGlobal("fetch", () => new Promise(() => {}));
  });
  afterAll(() => {
    vi.unstubAllGlobals();
  });

  it.each(PAGES)(
    "%s shows none in any state and links no page that does",
    (entry, View) => {
      const { text, shown, links } = sweep(entry, View);
      expect(text.length).toBeGreaterThan(200);
      expect([...shown]).toEqual([]);
      expect([...links].filter(linksRetiredPage)).toEqual([]);
    },
    60_000,
  );

  it("shows none in the shared header and footer, which link only the known pages that do", () => {
    render(
      <PolicyEngineShell country="us">
        <p>Page</p>
      </PolicyEngineShell>,
    );
    const body = document.body;
    const attributes = [...body.querySelectorAll("*")].flatMap((element) =>
      [...element.attributes].map((attribute) => attribute.value),
    );
    expect([body.textContent, ...attributes].filter(showsRetiredName)).toEqual(
      [],
    );
    const links = new Set(
      [...body.querySelectorAll("a[href]")].map((link) =>
        link.getAttribute("href"),
      ),
    );
    expect([...links].filter(linksRetiredPage)).toEqual(
      SHELL_LINKS_TO_RETIRED_PAGES,
    );
  });

  it("stays out of the generated memo", () => {
    expect(memoMarkdown.length).toBeGreaterThan(1000);
    expect(normalize(memoMarkdown)).not.toMatch(RETIRED);
  });

  it("stays out of site code and copy", () => {
    expect(
      siteCode.filter((path) => showsRetiredName(sourceText(path))),
    ).toEqual([]);
  });

  it("stays out of everything public serves", () => {
    expect(publicFiles.filter((path) => showsRetiredName(path))).toEqual([]);
    expect(
      publicFiles.filter(
        (path) => DOCUMENTS.test(path) && !CHECKED_DOCUMENTS.includes(path),
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
      ...siteCode,
      ...pathsUnder("src/data"),
      ...publicText,
    ]);
    const urls = [...sources].flatMap((path) =>
      (read(path).match(URL_PATTERN) ?? []).map((url) =>
        url.replace(/[.,;:!?]+$/, ""),
      ),
    );
    expect([...new Set(urls.filter(linksRetiredPage))]).toEqual([]);
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
    const reads = siteCode
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
