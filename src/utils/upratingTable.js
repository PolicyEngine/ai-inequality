import Papa from "papaparse";

import { POLICYENGINE_US_SNAPSHOT } from "./policyengineUsSource";

// scripts/generate_uprating_table.py writes this table from the pinned
// PolicyEngine-US release: a row for each parameter file whose values grow
// over time and for each variable whose uprating is set.
export const UPRATING_TABLE_PATH = "/data/uprating_analysis.csv";

export function parseUpratingTable(text) {
  const { data, errors } = Papa.parse(text, {
    header: true,
    skipEmptyLines: true,
  });
  if (errors.length) {
    throw new Error(
      `Uprating table row ${errors[0].row}: ${errors[0].message}`,
    );
  }
  return data;
}

// The generator joins a file's uprating specs with SPEC_SEPARATOR and writes
// a value that a formula in PolicyEngine-US grows as "<index> via <function>",
// naming a function in FORMULA_MODULE. Its FORMULA_SEPARATOR and
// EXTENSIONS_MODULE must match these.
export const FORMULA_MODULE =
  "policyengine_us/parameters/uprating_extensions.py";
const SPEC_SEPARATOR = "; ";
const FORMULA_SPEC = /^(\S+) via ([A-Za-z_]\w*)$/;

// The formulas that grow a row's values, as [{ series, step }].
export function formulaSteps(row) {
  return (row?.uprating ?? "")
    .split(SPEC_SEPARATOR)
    .map((spec) => FORMULA_SPEC.exec(spec))
    .filter(Boolean)
    .map(([, series, step]) => ({ series, step }));
}

export function formulaSourceUrl() {
  const { repository, commit } = POLICYENGINE_US_SNAPSHOT;
  return `https://github.com/${repository}/blob/${commit}/${FORMULA_MODULE}`;
}

const among =
  (...categories) =>
  (category) =>
    categories.includes(category);

// The cards on /research group the generator's categories by the index
// family that drives them. A category no card claims falls to OTHER_CARD,
// which lists it by name, so a new release's categories still show.
export const UPRATING_CARDS = [
  {
    id: "chained-cpi-u",
    title: "Chained CPI-U",
    includes: among("IRS chained CPI-U", "Chained CPI-U"),
    description:
      "The IRS adjusts federal income tax brackets, deductions and credits for inflation each year with chained CPI-U. PolicyEngine-US grows them, and many state tax amounts, with the same index.",
    examples: [
      { label: "Federal income tax brackets", path: "gov.irs.income.bracket" },
      {
        label: "Standard deduction",
        path: "gov.irs.deductions.standard.amount",
      },
      { label: "Maximum EITC", path: "gov.irs.credits.eitc.max" },
      {
        label: "HSA contribution limit for family coverage",
        path: "gov.irs.gross_income.health_savings_account_contributions.limit.family",
      },
    ],
  },
  {
    id: "income-by-source",
    title: "Income by source",
    includes: (category) => category.startsWith("CBO "),
    description:
      "PolicyEngine-US grows wages, self-employment income, capital gains, dividends, interest, pensions, Social Security benefits and unemployment compensation in its microdata with the IRS's total for each, per person. It extends those totals with CBO's projections, and grows other dollar inputs with CBO's projection of adjusted gross income per person.",
    examples: [
      { label: "Employment income", path: "employment_income_before_lsr" },
      {
        label: "Long-term capital gains",
        path: "long_term_capital_gains_before_response",
      },
      { label: "Qualified dividends", path: "qualified_dividend_income" },
      {
        label: "Social Security retirement benefits",
        path: "social_security_retirement_reported",
      },
      { label: "Unemployment compensation", path: "unemployment_compensation" },
    ],
  },
  {
    id: "cpi-u",
    title: "CPI-U",
    includes: among(
      "CPI-U",
      "SNAP (CPI-U)",
      "Head Start spending (CPI-U)",
      "Federal poverty guidelines (CPI-U)",
    ),
    description:
      "PolicyEngine-US grows the federal poverty guidelines, SNAP, WIC and school meal amounts, Medicaid's long-term care limits and several state and city tax amounts with CPI-U. In its microdata, it grows household expenses, assets and debts with the same index.",
    examples: [
      { label: "Federal poverty guidelines", path: "gov.hhs.fpg" },
      {
        label: "Medicaid home equity limit",
        path: "gov.hhs.medicaid.eligibility.long_term_care.home_equity.limit",
      },
      {
        label: "SNAP standard deduction",
        path: "gov.usda.snap.income.deductions.standard",
      },
      { label: "WIC benefit values", path: "gov.usda.wic.value" },
      {
        label: "Arkansas standard deduction",
        path: "gov.states.ar.tax.income.deductions.standard",
      },
      { label: "Home mortgage interest", path: "home_mortgage_interest" },
    ],
  },
  {
    id: "california-cpi",
    title: "California CPI",
    includes: among("California CPI"),
    description:
      "PolicyEngine-US grows California's income tax brackets, standard deduction, exemptions and credits with the California CPI, which it projects with chained CPI-U.",
    examples: [
      {
        label: "California income tax brackets for single filers",
        path: "gov.states.ca.tax.income.rates.single",
      },
      {
        label: "California standard deduction",
        path: "gov.states.ca.tax.income.deductions.standard.amount",
      },
    ],
  },
  {
    id: "cpi-w-and-wages",
    title: "CPI-W and wages",
    includes: among(
      "Social Security (CPI-W)",
      "CPI-W",
      "National average wage index",
    ),
    description:
      "PolicyEngine-US grows SSI payments, state supplements and veterans benefits with the cost-of-living adjustment that the Social Security Administration sets each year from CPI-W. It grows the payroll tax cap, the bend points in Social Security's benefit formula and other wage-indexed amounts with the national average wage index.",
    examples: [
      {
        label: "Maximum federal SSI payment",
        path: "gov.ssa.ssi.amount.individual",
      },
      { label: "Veterans benefits", path: "veterans_benefits" },
      {
        label: "Social Security payroll tax cap",
        path: "gov.irs.payroll.social_security.cap",
      },
      {
        label: "Bend points in Social Security's benefit formula",
        path: "gov.ssa.social_security.pia.formula_factors",
      },
    ],
  },
  {
    id: "health-costs",
    title: "Health costs",
    includes: among(
      "CMS health spending",
      "ACA benchmark premium",
      "CPI-U medical care",
    ),
    description:
      "PolicyEngine-US grows medical expenses and insurance premiums with CMS's health spending projections, and ACA benchmark premiums with the national average benchmark premium. It grows long-term care insurance premiums, and the cap on deducting them, with CPI-U for medical care.",
    examples: [
      { label: "Health insurance premiums", path: "health_insurance_premiums" },
      { label: "Emergency room visit expenses", path: "er_visit_expense" },
      {
        label: "ACA benchmark premiums by rating area",
        path: "gov.aca.state_rating_area_cost",
      },
      {
        label: "Cap on deducting long-term care premiums",
        path: "gov.irs.deductions.itemized.medical.long_term_care_premium_limit",
      },
    ],
  },
  {
    id: "population",
    title: "Population",
    includes: among("Population"),
    description:
      "PolicyEngine-US grows household and family weights with CBO's population projections, along with its counts of tax returns and of Social Security, SSI and SNAP participants.",
    examples: [
      { label: "Household weights", path: "household_weight" },
      {
        label: "Tax returns by filing status",
        path: "calibration.gov.irs.soi.returns_by_filing_status",
      },
      {
        label: "SNAP participants",
        path: "calibration.gov.usda.snap.participation",
      },
    ],
  },
];

export const OTHER_CARD = {
  id: "other",
  title: "Other indexes",
  includes: () => true,
  description: "",
  examples: [],
};

// The card each row's category falls in.
export function cardForCategory(category) {
  return UPRATING_CARDS.find((card) => card.includes(category)) ?? OTHER_CARD;
}

// Totals for the table and for each card that holds a row, largest first,
// with OTHER_CARD last. A card's share counts its rows against all rows.
export function summarizeUprating(rows) {
  const tally = new Map(
    [...UPRATING_CARDS, OTHER_CARD].map((card) => [
      card.id,
      { card, parameters: 0, variables: 0, categories: new Map() },
    ]),
  );
  let parameters = 0;
  let variables = 0;
  for (const row of rows) {
    const entry = tally.get(cardForCategory(row.uprating_category).id);
    const isParameter = row.type === "parameter";
    entry[isParameter ? "parameters" : "variables"] += 1;
    if (isParameter) parameters += 1;
    else variables += 1;
    entry.categories.set(
      row.uprating_category,
      (entry.categories.get(row.uprating_category) ?? 0) + 1,
    );
  }
  const total = rows.length;
  const pathsInCard = (card) =>
    new Set(
      rows
        .filter((row) => cardForCategory(row.uprating_category) === card)
        .map((row) => row.path),
    );
  const cards = [...tally.values()]
    .map(({ card, categories, ...counts }) => {
      const count = counts.parameters + counts.variables;
      const present = pathsInCard(card);
      return {
        ...card,
        ...counts,
        count,
        share: total ? count / total : 0,
        categories: [...categories]
          .map(([name, rowsInCategory]) => ({ name, count: rowsInCategory }))
          .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name)),
        examples: card.examples.filter((example) => present.has(example.path)),
      };
    })
    .filter((card) => card.count > 0)
    .sort(
      (a, b) =>
        (a.id === OTHER_CARD.id) - (b.id === OTHER_CARD.id) ||
        b.count - a.count,
    );
  return { total, parameters, variables, cards };
}

// "52%", or "<1%" for a share that rounds to zero.
export function formatShare(share) {
  const percent = Math.round(share * 100);
  return percent === 0 && share > 0 ? "<1%" : `${percent}%`;
}

// "1 parameter", "0 parameters" or "2 parameters".
export function counted(count, noun) {
  return `${count} ${noun}${count === 1 ? "" : "s"}`;
}
