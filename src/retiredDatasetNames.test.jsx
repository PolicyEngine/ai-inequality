import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

import { fireEvent, render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

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
// by eye. Documents hold text it can't parse, so each needs a reviewed entry.
const MEDIA =
  /\.(?:png|jpe?g|gif|webp|avif|bmp|ico|woff2?|ttf|otf|eot|mp3|mp4|webm|mov|wav)$/i;
const DOCUMENTS = /\.(?:pdf|docx?|pptx?|xlsx?|odt|odp|ods|epub|zip)$/i;
// Documents in public/ that someone has read in full and found clean.
const CHECKED_DOCUMENTS = [];
const MARKUP = /\.(?:html?|svg|xml)$/i;

const publicFiles = pathsUnder("public");
const publicText = publicFiles.filter(
  (path) => !MEDIA.test(path) && !DOCUMENTS.test(path),
);

const URL_PATTERN = /https?:\/\/[^\s"'`<>()\\]+/g;

// A frozen id can reach a page only through code that reads the data key
// holding it. AIScenarios reads this one and prints microcosmBuildLabel's
// label instead; any new read fails until someone confirms it prints no id.
const ALLOWED_READS = ["src/components/AIScenarios.jsx: certifiedDataBuildId"];

// Toggles and disclosure controls that change what a page shows.
const CONTROLS = [
  "button[aria-pressed]",
  "button[aria-expanded]",
  "[role=radio]",
  "[role=tab]",
  "[role=switch]",
  "[role=checkbox]",
  "input[type=radio]",
  "input[type=checkbox]",
].join(",");

// The country switch swaps the whole page. PAGES renders each country on its
// own, so the sweep leaves the switch alone.
const COUNTRY_SWITCH = '[role=radiogroup][aria-label="Country"]';

// A pass that needs more clicks than this has met a control that remounts the
// others on every click, so it fails instead of looping.
const MAX_CLICKS_PER_PASS = 500;

// Renders a page, works each control and each select option, and records the
// text, title, attribute values and links of every state it reaches.
function sweep(entry, View) {
  const body = document.body;
  const states = [];
  const mount = () =>
    render(
      <MemoryRouter initialEntries={[entry]}>
        <View />
      </MemoryRouter>,
    );
  const controls = () =>
    [...body.querySelectorAll(CONTROLS)].filter(
      (control) => !control.closest(COUNTRY_SWITCH),
    );
  const record = (label) => {
    const attributes = [...body.querySelectorAll("*")].flatMap((element) =>
      [...element.attributes].map((attribute) => attribute.value),
    );
    states.push({
      label,
      texts: [body.textContent, document.title, ...attributes],
      links: [...body.querySelectorAll("a[href]")].map((link) =>
        link.getAttribute("href"),
      ),
    });
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
  record("initial");
  const hidden = clickAll("first pass");
  const selectCount = body.querySelectorAll("select").length;
  for (let index = 0; index < selectCount; index += 1) {
    const values = [
      ...(body.querySelectorAll("select")[index]?.options ?? []),
    ].map((option) => option.value);
    for (const value of values) {
      const select = body.querySelectorAll("select")[index];
      if (!select) break;
      fireEvent.change(select, { target: { value } });
      record(`select ${index} = ${value}`);
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
  return states;
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
  it.each(PAGES)(
    "%s shows none in any state and links no page that does",
    (entry, View) => {
      const states = sweep(entry, View);
      expect(states[0].texts[0].length).toBeGreaterThan(200);
      const shown = states.flatMap(({ label, texts }) =>
        texts
          .filter(showsRetiredName)
          .map((text) => `${label}: ${excerpt(text)}`),
      );
      expect([...new Set(shown)]).toEqual([]);
      const links = new Set(states.flatMap((state) => state.links));
      expect([...links].filter(linksRetiredPage)).toEqual([]);
    },
    60_000,
  );

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
    const reads = siteCode
      .filter((path) => !path.startsWith("src/data/"))
      .flatMap((path) => {
        const code = read(path);
        return [...keys]
          .filter((key) => new RegExp(`\\b${escape(key)}\\b`).test(code))
          .map((key) => `${path}: ${key}`);
      });
    expect(reads.filter((entry) => !ALLOWED_READS.includes(entry))).toEqual([]);
  });
});
