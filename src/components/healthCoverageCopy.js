// Every sentence of the policy-analysis page's health-coverage section, with
// each number read from src/data/revenueLines.json (analysis/revenue_lines.py
// writes it) and printed by one formatter.
import { billions } from "../charts/billions";

// The shift the titles, captions and footnote quote.
export const QUOTED_SHIFT = 10;

// One shift's stored lines; throws if the file lacks it.
export function linesAt(revenueLines, shift) {
  const line = revenueLines.lines.find((row) => row.shift_pct === shift);
  if (!line) throw new Error(`revenueLines has no ${shift}% shift`);
  return line;
}

// The states' line leaves out workers' state payroll taxes, such as
// California's State Disability Insurance. Where the line not counting health
// coverage is smaller than those taxes' change, its sign is not settled, so
// the caption says "about even" rather than print it.
export function statesAboutEven(line) {
  return (
    Math.abs(line.states_not_counting_health_change_b) <
    Math.abs(line.employee_state_payroll_tax_change_b)
  );
}

const word = (value) => billions(value, { unit: "billion" });
const signed = (value) => billions(value, { sign: true });

// The states' line not counting health coverage at one shift, as the caption
// and the tooltip print it: "about even" where statesAboutEven holds, else
// the signed amount.
export function statesNotCounting(line) {
  return statesAboutEven(line)
    ? "about even"
    : signed(line.states_not_counting_health_change_b);
}

export function healthCoverageCopy(revenueLines) {
  const at = linesAt(revenueLines, QUOTED_SHIFT);
  const year = revenueLines.provenance.year;
  const shift = `At a ${QUOTED_SHIFT}% shift`;
  const series = {
    counting: "Counting health coverage",
    notCounting: "Not counting health coverage",
  };
  const californiaTax = at.california_income_and_use_tax_change_b;
  const californiaSpending =
    californiaTax - at.california_net_counting_health_change_b;

  return {
    section: {
      heading: "What counting health coverage changes",
      intro:
        "The sweep counts Medicaid, CHIP and ACA premium tax credits, which grow as wages fall, and charges each government its share of the added spending.",
    },
    revenueByGovernment: {
      title: `${shift}, health coverage costs the federal government ${word(at.federal_health_change_b)} and the states ${word(at.state_health_change_b)}`,
      subtitle: `Net revenue change in ${year}, taxes less benefits and excluding corporate taxes, by share of labor income shifted to capital income`,
      panels: {
        federal: "Federal government",
        states: "States combined",
      },
      series,
      captions: {
        federal: `${shift}: ${signed(at.federal_counting_health_change_b)} counting health coverage, ${signed(at.federal_not_counting_health_change_b)} not counting it`,
        states: `${shift}: ${signed(at.states_counting_health_change_b)} counting health coverage, ${statesNotCounting(at)} not counting it`,
      },
      footnote: `The federal line includes employers' state and local payroll taxes. Neither line counts the Additional Medicare Tax, which falls ${word(at.additional_medicare_tax_change_b)} at a ${QUOTED_SHIFT}% shift, or workers' state payroll taxes, such as California's State Disability Insurance, and local taxes on occupations, which fall ${word(at.employee_state_payroll_tax_change_b + at.local_occupational_tax_change_b)}. Counting those, all governments' net revenue falls ${word(at.total_rev_change_b)}.`,
    },
    california: {
      title: `${shift}, California's income and use tax rises ${word(californiaTax)}, and added health and benefit spending takes ${word(californiaSpending)} of it`,
      subtitle: `Change in California's revenue in ${year}, by share of labor income shifted to capital income`,
      series: {
        incomeTax: "Income and use tax, after refundable credits",
        net: "Less added health and benefit spending",
      },
      footnote:
        "Neither line counts workers' State Disability Insurance contributions, which fall with wages.",
    },
  };
}
