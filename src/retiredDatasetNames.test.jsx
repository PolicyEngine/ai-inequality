import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

import { PolicyEngineShell } from "@policyengine/ui-kit/layout";
import { fireEvent, render } from "@testing-library/react";
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
// the spellings they take in prose, release ids and package names. Published
// ids keep the old spelling in data and code; pages never show them.
const RETIRED =
  /populace|enhanced[\s_-]*(?:cps|current[\s_-]*population[\s_-]*survey)|\be[\s_-]?cps\b|policyengine[\s_-]*us[\s_-]*data/i;

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
// page here as on policyengine.org, that open a page listed above. Remove one
// once its page stops showing a retired name.
const SHELL_LINKS_TO_RETIRED_PAGES = [
  "https://policyengine.org/us/model",
  "https://policyengine.org/us/python",
  "https://policyengine.org/us/research",
];

// Where policyengine.org serves the study, so links resolve as they do there.
const STUDY_URL = "https://policyengine.org/us/ai-inequality";
const STUDY_PATH = new URL(STUDY_URL).pathname;

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

// Media can show text too, but this test can't read pixels, so check new images
// by eye. Documents and archives hold text it can't parse, so each needs a
// reviewed entry.
const MEDIA =
  /\.(?:png|jpe?g|gif|webp|avif|bmp|ico|woff2?|ttf|otf|eot|mp3|mp4|webm|mov|wav)$/i;
const DOCUMENTS =
  /\.(?:pdf|docx?|pptx?|xlsx?|odt|odp|ods|epub|zip|gz|tgz|tar|7z|rar|bz2|xz)$/i;
// Documents in public/, src/ or app/ that someone has read in full and found
// clean.
const CHECKED_DOCUMENTS = [];
const MARKUP = /\.(?:html?|svg|xml)$/i;

const isTest = (path) => /\.test\.[cm]?[jt]sx?$/.test(path);
const isCode = (path) => /\.[cm]?[jt]sx?$/.test(path);
const isData = (path) => path.startsWith("src/data/") && !isCode(path);

const publicFiles = pathsUnder("public");
const publicText = publicFiles.filter(
  (path) => !MEDIA.test(path) && !DOCUMENTS.test(path),
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
    (path) => !isData(path) && !MEDIA.test(path) && !DOCUMENTS.test(path),
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
const LINKING = "[href],iframe[src],frame[src],embed[src],object[data]";

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

// Renders a page, works each control and option, and checks the text, title
// and attribute values of every state it reaches. Returns the page's starting
// text, the retired names it found, every link it saw, resolved as on
// policyengine.org, and any field it couldn't fill.
function sweep(entry, View) {
  const body = document.body;
  const page = `${STUDY_URL}${entry}`;
  const found = {
    text: "",
    shown: new Set(),
    links: new Set(),
    fields: new Set(),
  };
  const mount = () =>
    render(
      <MemoryRouter
        basename={STUDY_PATH}
        initialEntries={[`${STUDY_PATH}${entry}`]}
      >
        <View />
      </MemoryRouter>,
    );
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
  // A route's steps for labels: a control's position, or a select's position
  // and the value chosen.
  const trail = (route) =>
    route
      .map((step) =>
        typeof step === "number" ? step : `${step.select}=${step.value}`,
      )
      .join(".");
  const record = (label) => {
    const attributes = [...body.querySelectorAll("*")].flatMap((element) =>
      [...element.attributes].map((attribute) => attribute.value),
    );
    for (const text of [body.textContent, document.title, ...attributes]) {
      if (showsRetiredName(text)) found.shown.add(`${label}: ${excerpt(text)}`);
    }
    for (const element of body.querySelectorAll(LINKING)) {
      const attribute = element.matches("object")
        ? "data"
        : element.hasAttribute("href")
          ? "href"
          : "src";
      found.links.add(resolve(element.getAttribute(attribute), page));
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
  const clickAll = (
    pass,
    { route = [], worked = [], follows = null, leave = () => false } = {},
  ) => {
    const clicked = new Set(worked);
    const steps = [...route];
    const unreached = new Map();
    let last = null;
    for (let shown = controls(); ; shown = controls()) {
      shown.forEach((element, position) => {
        if (clicked.has(element) || unreached.has(element)) return;
        if (leave(element)) return;
        unreached.set(element, [...steps, position]);
        if (follows?.has(last)) follows.add(element);
      });
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
  const follow = (route) => {
    const worked = [];
    let before = [];
    route.forEach((step, index) => {
      before = controls();
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
    return { worked, revealed };
  };

  let { unmount } = mount();
  found.text = body.textContent;
  record("initial");
  const routes = clickAll("first pass");
  for (const group of groups().filter((group) => group.select)) {
    for (const option of group.options) {
      if (!group.select.isConnected) break;
      choose(group, option);
      record(`${group.label} = ${option.value}`);
    }
  }
  clickAll("second pass");
  unmount();

  // Gives each option of every group the page starts with a fresh render and
  // then a pass that leaves the group alone, so every other control gets
  // worked with each option chosen, as with tabs that share one details
  // button.
  ({ unmount } = mount());
  const sizes = groups().map((group) => group.options.length);
  unmount();
  sizes.forEach((size, first) => {
    for (let index = 0; index < size; index += 1) {
      ({ unmount } = mount());
      const group = groups()[first];
      const option = group.options[index];
      const step = group.select
        ? { select: selects().indexOf(group.select), value: option.value }
        : controls().indexOf(option);
      const { worked, revealed } = follow([step]);
      routes.push(
        ...clickAll(`${group.label} = ${name(option)}`, {
          route: [step],
          worked,
          follows: revealed,
          leave: group.holds,
        }),
      );
      unmount();
    }
  });

  // A pass saw each of these controls but hid it before reaching it. Each
  // gets a fresh render that works its way back to the control, works it,
  // and then runs a pass of its own. That pass adds a route to any control
  // the hidden one revealed and the pass hid in turn.
  for (let next = 0; next < routes.length; next += 1) {
    if (next === MAX_ROUTES) {
      throw new Error(`${entry}: over ${MAX_ROUTES} routes`);
    }
    const route = routes[next];
    ({ unmount } = mount());
    const { worked, revealed } = follow(route);
    routes.push(
      ...clickAll(`after route ${trail(route)}`, {
        route,
        worked,
        follows: revealed,
      }),
    );
    unmount();
  }

  // Pairs each option of every group the page starts with with each option of
  // every other group shown alongside it. Each first group gets a fresh
  // render, and each second group returns to its starting option before the
  // next one, so no choice hides the groups after it.
  for (let first = 0; first < sizes.length; first += 1) {
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
  // The uprating explorer fetches its table from public/, which the tests
  // below read directly, so the sweep leaves the explorer loading. A download
  // hands its file to the test instead of the browser.
  const blobs = new Map();
  const downloads = [];
  const { createObjectURL, revokeObjectURL } = URL;
  beforeAll(() => {
    vi.stubGlobal("fetch", () => new Promise(() => {}));
    URL.createObjectURL = (blob) => {
      const url = `blob:${STUDY_URL}/download-${blobs.size + 1}`;
      blobs.set(url, blob);
      return url;
    };
    URL.revokeObjectURL = () => {};
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(
      function save() {
        downloads.push({ name: this.download, blob: blobs.get(this.href) });
      },
    );
  });
  afterAll(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    Object.assign(URL, { createObjectURL, revokeObjectURL });
  });

  // The downloads a sweep set off, each file's name and text, with any that
  // shows a retired name.
  async function handedOver() {
    const files = await Promise.all(
      downloads.splice(0).map(async ({ name, blob }) => ({
        name,
        text: blob ? await blobText(blob) : "",
      })),
    );
    return {
      files,
      shown: files.filter(
        ({ name, text }) => showsRetiredName(name) || showsRetiredName(text),
      ),
    };
  }

  it("renders every route App.jsx declares, and the app serves no other page", () => {
    expect(ROUTES.length).toBeGreaterThan(0);
    expect(ROUTES.length).toBe((read(APP).match(/<Route\b/g) ?? []).length);
    expect(ROUTES.filter(({ path, View }) => !path || !View)).toEqual([]);
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

  it.each(PAGES)(
    "%s shows none in any state and links no page that does",
    async (entry, View) => {
      const { text, shown, links, fields } = sweep(entry, View);
      expect(text.length).toBeGreaterThan(200);
      expect([...shown]).toEqual([]);
      expect([...links].filter(linksRetiredPage)).toEqual([]);
      expect([...fields]).toEqual([]);
      expect((await handedOver()).shown).toEqual([]);
    },
    120_000,
  );

  it("reads the file a download hands over, such as the references' BibTeX", async () => {
    const references = ROUTES.find(({ path }) => path === "/references");
    sweep("/references", references.View);
    const { files, shown } = await handedOver();
    expect(files.length).toBeGreaterThan(0);
    expect(files[0].text.length).toBeGreaterThan(1000);
    expect(shown).toEqual([]);
  }, 120_000);

  it("shows none in the shared header and footer in any state, which link only the known pages that do", () => {
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
    const { shown, links } = sweep("/", Shell);
    expect([...shown]).toEqual([]);
    expect([...links].filter(linksRetiredPage).sort()).toEqual(
      SHELL_LINKS_TO_RETIRED_PAGES,
    );
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
    expect(servedFiles.filter((path) => showsRetiredName(path))).toEqual([]);
    expect(
      [...publicFiles, ...siteFiles].filter(
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
    const constants = new Map();
    for (const path of siteCode) {
      for (const [, name, value] of read(path).matchAll(STRING_CONSTANT)) {
        constants.set(name, (constants.get(name) ?? new Set()).add(value));
      }
    }
    expect(
      siteCode.flatMap((path) => {
        const code = read(path);
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
