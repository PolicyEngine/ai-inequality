import usShiftSweepData from "../data/shiftSweepData.json";
import ukShiftSweepData from "../data/ukShiftSweepData.json";
import { predatesHeadStartCorrection } from "./modelMetadata";

describe("predatesHeadStartCorrection", () => {
  test("does not flag the committed US sweep, which reran after the correction", () => {
    // The sweep reran through managed_us_microsimulation on the same model
    // version, so its bundle records the programs it keeps out of net income
    // and the on-page note stays off.
    expect(usShiftSweepData.metadata.country_model_version).toBe("1.764.6");
    expect(
      usShiftSweepData.metadata.policyengine_bundle
        .net_income_excluded_benefits,
    ).toEqual(["early_head_start", "head_start"]);
    expect(predatesHeadStartCorrection(usShiftSweepData.metadata)).toBe(false);
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
