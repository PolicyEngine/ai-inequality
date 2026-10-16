import { describe, expect, it } from "vitest";
import aiScenariosData from "../data/aiScenariosData.json";
import {
  equivalentShift,
  forecastBand,
  forecastMarkers,
} from "./forecastEquivalence";

describe("equivalentShift", () => {
  it("matches the proportional labor-share fall from the calibration", () => {
    // Rapid: labor share 55.5% -> 52.0% implies (55.5 - 52.0) / 55.5 = 6.31%.
    // Growth rates are the Budget Lab's committed v1.0.1 cell parameters.
    const rapid = equivalentShift({
      gdpGrowth: 0.0716663637828425,
      laborGrowth: 0.00408380030104152,
    });
    expect(rapid).toBeCloseTo((55.5 - 52.0) / 55.5, 10);
  });

  it("is zero for the shares-fixed counterfactual", () => {
    expect(equivalentShift({ gdpGrowth: 0.0717, laborGrowth: 0.0717 })).toBe(0);
  });

  it("returns null when inputs are missing", () => {
    expect(equivalentShift({})).toBeNull();
    expect(equivalentShift(null)).toBeNull();
  });
});

describe("forecastMarkers on the committed payload", () => {
  it("yields one marker per scenario, in ascending order", () => {
    const markers = forecastMarkers(aiScenariosData);
    expect(markers.map((m) => m.name)).toEqual(["Slow", "Moderate", "Rapid"]);
  });

  it("reproduces the published labor-share targets", () => {
    // Slow 55.0, Moderate 54.0, Rapid 52.0, from a 55.5 pre-shock share
    // (Karger et al. 2026 via The Budget Lab, Table 1 as revised 9 October
    // 2026; the July table had 53.8 and 51.3).
    const markers = forecastMarkers(aiScenariosData);
    const byName = Object.fromEntries(markers.map((m) => [m.name, m.shiftPct]));
    expect(byName.Slow).toBeCloseTo(((55.5 - 55.0) / 55.5) * 100, 6);
    expect(byName.Moderate).toBeCloseTo(((55.5 - 54.0) / 55.5) * 100, 6);
    expect(byName.Rapid).toBeCloseTo(((55.5 - 52.0) / 55.5) * 100, 6);
  });

  it("keeps the whole band inside the first tenth of the sweep axis", () => {
    const band = forecastBand(aiScenariosData);
    expect(band.maxPct).toBeGreaterThan(6);
    expect(band.maxPct).toBeLessThan(10);
  });
});
