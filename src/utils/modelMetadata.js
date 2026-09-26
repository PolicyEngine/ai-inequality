export function policyEngineVersion(metadata) {
  return metadata.policyengine_version ?? "version unavailable";
}

export function policyEngineLabel(metadata) {
  return `PolicyEngine ${policyEngineVersion(metadata)}`;
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
