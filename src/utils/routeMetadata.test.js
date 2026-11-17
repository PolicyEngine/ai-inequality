import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import sweepData from "../data/shiftSweepData.json";
import { countsHealthTanf } from "./sweepRevenue";
import {
  POLICY_ANALYSIS_CARD,
  SITE_URL,
  policyAnalysisCardAlt,
  policyAnalysisDescription,
  routeMetadata,
  wholeBillions,
} from "./routeMetadata";

const revenueAt = (data, shift) =>
  data.scenarios.find((scenario) => scenario.shift_pct === shift)
    .revenue_change_b;

const billions = (value) =>
  `$${Math.round(Math.abs(value)).toLocaleString("en-US")} billion`;

// A copy of the site's sweep with the 10% revenue change replaced.
function withTenPercent(value) {
  return {
    ...sweepData,
    scenarios: sweepData.scenarios.map((scenario) =>
      scenario.shift_pct === 10
        ? { ...scenario, revenue_change_b: value }
        : scenario,
    ),
  };
}

// The PNG's text chunks, keyword to text.
function pngText(path) {
  const bytes = readFileSync(path);
  const chunks = {};
  let offset = 8;
  while (offset < bytes.length) {
    const length = bytes.readUInt32BE(offset);
    const type = bytes.toString("latin1", offset + 4, offset + 8);
    if (type === "tEXt") {
      const body = bytes.subarray(offset + 8, offset + 8 + length);
      const split = body.indexOf(0);
      chunks[body.toString("latin1", 0, split)] = body.toString(
        "latin1",
        split + 1,
      );
    }
    offset += 12 + length;
  }
  return { chunks, width: bytes.readUInt32BE(16), height: bytes.readUInt32BE(20) };
}

// Vitest runs from the repo root.
const CARD_FILE = join(process.cwd(), "public", POLICY_ANALYSIS_CARD.path);

describe("routeMetadata", () => {
  it("leaves routes without their own preview to the layout", () => {
    for (const route of ["", "research", "income-shift", "budget-lab"]) {
      expect(routeMetadata(route)).toEqual({});
    }
  });

  it("states the site's 10% amount for the US and the corporate-tax scope", () => {
    const description = policyAnalysisDescription();
    expect(description).toBe(
      `If AI shifted 10% of US labor income to capital income in ${sweepData.metadata.year}, with household market income unchanged, we estimate federal, state and local governments would come out ${billions(revenueAt(sweepData, 10))} behind, leaving aside corporate taxes.`,
    );
    expect(revenueAt(sweepData, 10)).toBeLessThan(0);
  });

  it("words a gain and a near-zero change from the amount", () => {
    expect(policyAnalysisDescription(withTenPercent(12.4))).toContain(
      "would come out $12 billion ahead",
    );
    expect(policyAnalysisDescription(withTenPercent(-0.3))).toContain(
      "governments would break even,",
    );
  });

  it("gives every tag an absolute image URL on policyengine.org", () => {
    const metadata = routeMetadata("policy-analysis");
    const url = `${SITE_URL}${POLICY_ANALYSIS_CARD.path}`;
    expect(url).toBe(
      "https://www.policyengine.org/us/ai-inequality/images/og/policy-analysis.png",
    );
    expect(metadata.openGraph.images[0]).toMatchObject({
      url,
      width: 1200,
      height: 630,
    });
    expect(metadata.twitter.card).toBe("summary_large_image");
    expect(metadata.twitter.images[0].url).toBe(url);
    // A page's openGraph replaces the layout's, so it carries every field.
    expect(metadata.openGraph).toMatchObject({
      type: "website",
      siteName: "PolicyEngine",
      title: expect.any(String),
      description: metadata.description,
    });
    // The UK rewrite serves this HTML too, so no tag claims the page's URL.
    expect(metadata.openGraph.url).toBeUndefined();
  });

  it("describes the card's amounts in its alt text", () => {
    const alt = policyAnalysisCardAlt();
    for (const shift of [10, 50, 100]) {
      expect(alt).toContain(billions(revenueAt(sweepData, shift)));
    }
    expect(alt).toContain("excluding corporate taxes");
  });

  it("ships a 1200 x 630 card drawn from the current sweep data", () => {
    const { chunks, width, height } = pngText(CARD_FILE);
    expect([width, height]).toEqual([1200, 630]);
    expect(readFileSync(CARD_FILE).length).toBeLessThan(1_000_000);
    const source = JSON.parse(chunks.Source);
    const drawn = Object.fromEntries(
      sweepData.scenarios.map((scenario) => [
        String(scenario.shift_pct),
        Number(scenario.revenue_change_b.toFixed(3)),
      ]),
    );
    // Rerun scripts/make_og_card.py after a data refresh.
    expect(source.revenue_change_b).toEqual(drawn);
    expect(source.year).toBe(sweepData.metadata.year);
    expect(source.counts_health).toBe(countsHealthTanf(sweepData));
    // The card's callout and the description print the same whole billions.
    expect(source.callout_billions_at_10).toBe(
      wholeBillions(revenueAt(sweepData, 10)),
    );
    expect(policyAnalysisDescription()).toContain(
      `$${source.callout_billions_at_10.toLocaleString("en-US")} billion`,
    );
  });

  it("words the alt text's scope and mixed or zero amounts from the data", () => {
    const withoutHealth = {
      ...sweepData,
      scenarios: sweepData.scenarios.map((scenario) => {
        const copy = { ...scenario };
        delete copy.federal_health_change_b;
        return copy;
      }),
    };
    expect(policyAnalysisCardAlt(withoutHealth)).toContain(
      "excluding health coverage and corporate taxes",
    );
    expect(policyAnalysisCardAlt(withTenPercent(0.3))).toContain(
      "We estimate it changes by less than $0.5 billion at 10%, falls ",
    );
    expect(policyAnalysisCardAlt(withTenPercent(12))).toMatch(
      /We estimate it rises \$12 billion at 10%, falls \$[\d,]+ billion at 50% and falls \$[\d,]+ billion at 100%\.$/,
    );
  });

  it("rounds halves away from zero, as the card script does", () => {
    expect([-194.5, 194.5, -0.4, 2010.79].map(wholeBillions)).toEqual([
      195, 195, 0, 2011,
    ]);
  });
});
