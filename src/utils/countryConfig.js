import incomeDistributionData from "../data/incomeDistributionData.json";
import usShiftSweepData from "../data/shiftSweepData.json";
import ukShiftSweepData from "../data/ukShiftSweepData.json";
import { isUkStudyPath } from "./basePath";

export const COUNTRIES = {
  us: {
    label: "United States",
    sweepData: usShiftSweepData,
    incomeDistributionData,
  },
  uk: {
    label: "United Kingdom",
    sweepData: ukShiftSweepData,
    incomeDistributionData: null,
  },
};

function browserPathname() {
  return typeof window === "undefined" ? "" : window.location.pathname;
}

// The country a path implies. policyengine.org rewrites /uk/ai-inequality to
// these pages with ?country=uk, but the query reaches only that upstream
// request: the browser keeps /uk/ai-inequality and sees no query.
export function countryFromPath(pathname = browserPathname()) {
  return isUkStudyPath(pathname) ? "uk" : "us";
}

// The country a page shows: the one ?country= names, else the path's.
export function countryFromSearchParams(
  searchParams,
  pathname = browserPathname(),
) {
  const requested = searchParams.get("country");
  return COUNTRIES[requested] ? requested : countryFromPath(pathname);
}

// The query that selects a country on this path: none when the path already
// implies it, so each country's own URL stays clean.
export function countrySearchParams(countryKey, pathname = browserPathname()) {
  return countryKey === countryFromPath(pathname)
    ? {}
    : { country: countryKey };
}

// What each country's experiment card says the sweep leaves out. The UK
// sweep records no check that market income stays the same, so its card
// claims none.
export const EXPERIMENT_LIMITS = {
  us: "Households' total market income stays the same. We don't pass employers' savings on payroll tax to anyone, and we model no behavioral responses.",
  uk: "We model no behavioural responses.",
};

export function aiInequalityUrl(countryKey) {
  return `https://www.policyengine.org/${countryKey}/ai-inequality`;
}

export function incomeShiftUrl(countryKey) {
  return `https://www.policyengine.org/${countryKey}/ai-inequality/income-shift`;
}
