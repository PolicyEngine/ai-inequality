import {
  countryFromPath,
  countryFromSearchParams,
  countrySearchParams,
} from "./countryConfig";

const UK = "/uk/ai-inequality/policy-analysis";
const US = "/us/ai-inequality/policy-analysis";
const query = (text) => new URLSearchParams(text);

afterEach(() => {
  window.history.replaceState(null, "", "/");
});

test("a path under /uk/ai-inequality implies the UK, and any other path the US", () => {
  expect(countryFromPath("/uk/ai-inequality")).toBe("uk");
  expect(countryFromPath("/uk/ai-inequality/")).toBe("uk");
  expect(countryFromPath(UK)).toBe("uk");
  expect(countryFromPath("/us/ai-inequality")).toBe("us");
  expect(countryFromPath(US)).toBe("us");
  // The GitHub Pages copy serves the study at /ai-inequality.
  expect(countryFromPath("/ai-inequality/income-shift")).toBe("us");
  expect(countryFromPath("/uk/ai-inequality-old")).toBe("us");
  expect(countryFromPath("/")).toBe("us");
  expect(countryFromPath("")).toBe("us");
});

test("?country= names the country when it names one, and the path decides otherwise", () => {
  expect(countryFromSearchParams(query("country=uk"), US)).toBe("uk");
  expect(countryFromSearchParams(query("country=us"), UK)).toBe("us");
  expect(countryFromSearchParams(query("country=uk"), UK)).toBe("uk");
  expect(countryFromSearchParams(query(""), UK)).toBe("uk");
  expect(countryFromSearchParams(query(""), US)).toBe("us");
  expect(countryFromSearchParams(query("country=ca"), UK)).toBe("uk");
  expect(countryFromSearchParams(query("country=ca"), US)).toBe("us");
});

// Names every plain object inherits name no country.
const INHERITED = ["constructor", "toString", "__proto__", "hasOwnProperty"];

test.each(INHERITED)("?country=%s names no country", (key) => {
  expect(countryFromSearchParams(query(`country=${key}`), UK)).toBe("uk");
  expect(countryFromSearchParams(query(`country=${key}`), US)).toBe("us");
});

test("the path defaults to the browser's", () => {
  window.history.replaceState(null, "", UK);
  expect(countryFromPath()).toBe("uk");
  expect(countryFromSearchParams(query(""))).toBe("uk");
  expect(countrySearchParams("uk")).toEqual({});
  window.history.replaceState(null, "", US);
  expect(countryFromPath()).toBe("us");
  expect(countryFromSearchParams(query(""))).toBe("us");
  expect(countrySearchParams("uk")).toEqual({ country: "uk" });
});

test("selecting a country adds ?country= only when the path implies another", () => {
  expect(countrySearchParams("uk", UK)).toEqual({});
  expect(countrySearchParams("us", UK)).toEqual({ country: "us" });
  expect(countrySearchParams("us", US)).toEqual({});
  expect(countrySearchParams("uk", US)).toEqual({ country: "uk" });
});
