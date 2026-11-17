// Link-preview tags for the pages a post may link. The site is a static
// export of a client-rendered app, so a crawler reads these tags and little
// else. policyengine.org rewrites /uk/ai-inequality to the same HTML with
// ?country=uk, so every tag names the US instead of assuming the reader's
// country.
import sweepData from "../data/shiftSweepData.json";
import { countsHealthTanf } from "./sweepRevenue";

export const SITE_URL = "https://www.policyengine.org/us/ai-inequality";

// scripts/make_og_card.py draws this card from src/data/shiftSweepData.json
// and stamps the year and amounts it drew into the PNG, which
// routeMetadata.test.js checks against the data and the description.
export const POLICY_ANALYSIS_CARD = {
  path: "/images/og/policy-analysis.png",
  width: 1200,
  height: 630,
};

function revenueAt(data, shift) {
  const row = data.scenarios.find((scenario) => scenario.shift_pct === shift);
  if (!row || !Number.isFinite(row.revenue_change_b)) {
    throw new Error(`The sweep has no revenue change at a ${shift}% shift.`);
  }
  return row.revenue_change_b;
}

// Whole billions, halves away from zero, as scripts/make_og_card.py rounds the
// card's callout.
export function wholeBillions(value) {
  return Math.round(Math.abs(value));
}

// "$195 billion", "$2,011 billion": whole billions, the sign left to the words.
function billions(value) {
  return `$${wholeBillions(value).toLocaleString("en-US")} billion`;
}

export function policyAnalysisDescription(data = sweepData) {
  const year = data.metadata?.year ?? data.year;
  const value = revenueAt(data, 10);
  const outcome =
    wholeBillions(value) === 0
      ? "would break even"
      : `would come out ${billions(value)} ${value < 0 ? "behind" : "ahead"}`;
  return `If AI shifted 10% of US labor income to capital income in ${year}, with household market income unchanged, we estimate federal, state and local governments ${outcome}, leaving aside corporate taxes.`;
}

// The card's scope, as scripts/make_og_card.py words it from the same test.
function cardScope(data) {
  return countsHealthTanf(data)
    ? "counting health coverage and excluding corporate taxes"
    : "excluding health coverage and corporate taxes";
}

export function policyAnalysisCardAlt(data = sweepData) {
  const year = data.metadata?.year ?? data.year;
  const amounts = [10, 50, 100].map((shift) => {
    const value = revenueAt(data, shift);
    const verb =
      wholeBillions(value) === 0 ? "stays" : value < 0 ? "falls" : "rises";
    return { shift, value, verb };
  });
  const [ten, fifty, hundred] = amounts;
  let list;
  if (ten.verb !== "stays" && amounts.every(({ verb }) => verb === ten.verb)) {
    list = `${ten.verb} ${billions(ten.value)} at a 10% shift, ${billions(fifty.value)} at 50% and ${billions(hundred.value)} at 100%`;
  } else {
    const clauses = amounts.map(({ shift, value, verb }) =>
      verb === "stays"
        ? `changes by less than $0.5 billion at ${shift}%`
        : `${verb} ${billions(value)} at ${shift}%`,
    );
    list = `${clauses.slice(0, -1).join(", ")} and ${clauses.at(-1)}`;
  }
  return `Line chart of the change in US federal, state and local net revenue in ${year} by share of labor income shifted to capital income, ${cardScope(data)}. We estimate it ${list}.`;
}

const POLICY_ANALYSIS_TITLE = "What if AI shifts income from labor to capital?";

// Next's metadata for one route of the catch-all page. Routes without their
// own preview keep the layout's title and description.
export function routeMetadata(route, data = sweepData) {
  if (route !== "policy-analysis") return {};
  const description = policyAnalysisDescription(data);
  const image = {
    url: `${SITE_URL}${POLICY_ANALYSIS_CARD.path}`,
    width: POLICY_ANALYSIS_CARD.width,
    height: POLICY_ANALYSIS_CARD.height,
    alt: policyAnalysisCardAlt(data),
  };
  return {
    title: `${POLICY_ANALYSIS_TITLE} | PolicyEngine`,
    description,
    openGraph: {
      type: "website",
      siteName: "PolicyEngine",
      title: POLICY_ANALYSIS_TITLE,
      description,
      images: [image],
    },
    twitter: {
      card: "summary_large_image",
      title: POLICY_ANALYSIS_TITLE,
      description,
      images: [image],
    },
  };
}
