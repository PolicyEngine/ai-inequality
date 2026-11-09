import usShiftSweepData from "../data/shiftSweepData.json";
import ukShiftSweepData from "../data/ukShiftSweepData.json";
import {
  microcosmBuildLabel,
  predatesHeadStartCorrection,
} from "./modelMetadata";

describe("microcosmBuildLabel", () => {
  test("names the build and its date without the release id", () => {
    expect(
      microcosmBuildLabel(
        "populace-us-2024-buildp-sparse-rmloss100-cae8640-20260728T011454Z",
      ),
    ).toBe("Microcosm US 2024 (build p, 28 July 2026)");
  });

  test("accepts the migrated spelling and an unpadded day", () => {
    expect(
      microcosmBuildLabel("microcosm-us-2025-buildab-abc1234-20270103T000000Z"),
    ).toBe("Microcosm US 2025 (build ab, 3 January 2027)");
  });

  test.each([
    [undefined],
    [null],
    [""],
    ["policyengine-us-data-1.113.1"],
    // UK releases and SPM refreshes carry other id shapes.
    ["populace-uk-2023-buildp-abc1234-20260728T011454Z"],
    ["populace-us-2024-spm-20260915"],
    // Stamps that name no calendar date.
    ["populace-us-2024-buildp-abc1234-20261328T011454Z"],
    ["populace-us-2024-buildp-abc1234-20260732T011454Z"],
    ["populace-us-2024-buildp-abc1234-20260700T011454Z"],
    ["populace-us-2024-buildp-abc1234-20260231T011454Z"],
    ["populace-us-2024-buildp-abc1234-20270229T011454Z"],
  ])("returns null for %s", (buildId) => {
    expect(microcosmBuildLabel(buildId)).toBeNull();
  });

  test("accepts a leap day", () => {
    expect(
      microcosmBuildLabel("microcosm-us-2027-buildq-abc1234-20280229T120000Z"),
    ).toBe("Microcosm US 2027 (build q, 29 February 2028)");
  });
});

describe("predatesHeadStartCorrection", () => {
  test("flags the committed US sweep, which ran before the correction", () => {
    // If the sweep is rerun through managed_us_microsimulation its bundle
    // records net_income_excluded_benefits, this flips to false, and the
    // on-page note disappears with it.
    expect(usShiftSweepData.metadata.country_model_version).toBe("1.764.6");
    expect(predatesHeadStartCorrection(usShiftSweepData.metadata)).toBe(true);
  });

  test("does not flag the UK sweep", () => {
    expect(predatesHeadStartCorrection(ukShiftSweepData.metadata)).toBe(false);
  });

  test("does not flag a run that records its exclusions, even an empty list", () => {
    const base = {
      country_model_package: "policyengine-us",
      country_model_version: "1.764.6",
    };
    expect(
      predatesHeadStartCorrection({
        ...base,
        policyengine_bundle: {
          net_income_excluded_benefits: ["early_head_start", "head_start"],
        },
      }),
    ).toBe(false);
    expect(
      predatesHeadStartCorrection({
        ...base,
        country_model_version: "2.15.1",
        policyengine_bundle: { net_income_excluded_benefits: [] },
      }),
    ).toBe(false);
    expect(
      predatesHeadStartCorrection({
        ...base,
        net_income_excluded_benefits: ["early_head_start", "head_start"],
      }),
    ).toBe(false);
  });

  test("reads the package from the bundle when the top level lacks it", () => {
    expect(
      predatesHeadStartCorrection({
        policyengine_bundle: { model_package: "policyengine-us" },
      }),
    ).toBe(true);
  });

  test("returns false for missing or non-object metadata", () => {
    expect(predatesHeadStartCorrection(undefined)).toBe(false);
    expect(predatesHeadStartCorrection(null)).toBe(false);
    expect(predatesHeadStartCorrection("policyengine-us")).toBe(false);
  });
});
