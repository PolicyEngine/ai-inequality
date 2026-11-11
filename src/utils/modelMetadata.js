export function policyEngineVersion(metadata) {
  return metadata.policyengine_version ?? "version unavailable";
}

export function policyEngineLabel(metadata) {
  return `PolicyEngine ${policyEngineVersion(metadata)}`;
}

const MICROCOSM_US_BUILD_ID =
  /^(?:microcosm|populace)-us-(\d{4})-build([a-z0-9]+)-.+-(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z$/;

const MONTH_NAMES = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

// Published release ids keep Microcosm's pre-August spelling, so pages show
// this label and never the id. Returns null for anything other than a
// Microcosm US build stamped with a real UTC date and time.
export function microcosmBuildLabel(buildId) {
  const match = MICROCOSM_US_BUILD_ID.exec(buildId ?? "");
  if (!match) return null;
  const [, dataYear, build] = match;
  const [year, month, day, hours, minutes, seconds] = match
    .slice(3)
    .map(Number);
  // setUTCFullYear keeps years 0 to 99 as written, where Date.UTC would read
  // them as 1900 to 1999.
  const date = new Date(0);
  date.setUTCFullYear(year, month - 1, day);
  if (
    date.getUTCFullYear() !== year ||
    date.getUTCMonth() !== month - 1 ||
    date.getUTCDate() !== day ||
    hours > 23 ||
    minutes > 59 ||
    seconds > 59
  ) {
    return null;
  }
  return `Microcosm US ${dataYear} (build ${build}, ${day} ${MONTH_NAMES[month - 1]} ${year})`;
}

function hasNetIncomeExclusionRecord(record) {
  return (
    record != null &&
    typeof record === "object" &&
    Object.prototype.hasOwnProperty.call(record, "net_income_excluded_benefits")
  );
}

// True for a US run made before the September 2026 Head Start correction.
// Since RUNTIME_REVISION 3, every run built through
// analysis/policyengine_runtime.managed_us_microsimulation records the benefit
// programs it kept out of household net income as
// `net_income_excluded_benefits` in its bundle metadata (an empty list when the
// engine already leaves Head Start out). Runs without that record predate the
// correction; the ones committed here ran on policyengine-us 1.764.6, which
// counts Head Start and Early Head Start in household benefits and net income.
export function predatesHeadStartCorrection(metadata) {
  if (metadata == null || typeof metadata !== "object") return false;
  const bundle = metadata.policyengine_bundle;
  const modelPackage =
    metadata.country_model_package ?? bundle?.model_package ?? null;
  if (modelPackage !== "policyengine-us") return false;
  return !(
    hasNetIncomeExclusionRecord(metadata) || hasNetIncomeExclusionRecord(bundle)
  );
}
