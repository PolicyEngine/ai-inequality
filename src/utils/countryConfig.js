import incomeDistributionData from "../data/incomeDistributionData.json";
import usShiftSweepData from "../data/shiftSweepData.json";
import ukShiftSweepData from "../data/ukShiftSweepData.json";

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

export function countryFromSearchParams(searchParams) {
  return COUNTRIES[searchParams.get("country")]
    ? searchParams.get("country")
    : "us";
}

export function aiInequalityUrl(countryKey) {
  return `https://www.policyengine.org/${countryKey}/ai-inequality`;
}

export function incomeShiftUrl(countryKey) {
  return `https://www.policyengine.org/${countryKey}/ai-inequality/income-shift`;
}
