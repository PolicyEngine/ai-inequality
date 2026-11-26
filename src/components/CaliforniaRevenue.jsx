import React from "react";

import Figure, { LineLegend } from "../charts/Figure";
import LinePanel, { LINE_STYLES } from "../charts/LinePanel";
import { niceTicks } from "../utils/chartTicks";
import { healthCoverageCopy } from "./healthCoverageCopy";

// California's income and use tax after refundable credits, and what is left
// of it once the state pays for added health coverage and benefits, as
// analysis/revenue_lines.py stores them.
export const SERIES_KEYS = {
  incomeTax: "california_income_and_use_tax_change_b",
  net: "california_net_counting_health_change_b",
};

export function californiaTicks(lines) {
  const values = lines.flatMap((line) => [
    line[SERIES_KEYS.incomeTax],
    line[SERIES_KEYS.net],
  ]);
  return niceTicks(Math.min(0, ...values), Math.max(0, ...values));
}

export default function CaliforniaRevenue({ revenueLines, metadata, year }) {
  const copy = healthCoverageCopy(revenueLines).california;
  const legend = [
    { label: copy.series.incomeTax, ...LINE_STYLES.main },
    { label: copy.series.net, ...LINE_STYLES.comparison },
  ];

  return (
    <Figure
      id="california"
      title={copy.title}
      subtitle={copy.subtitle}
      legend={<LineLegend items={legend} />}
      footnote={copy.footnote}
      metadata={metadata}
      year={year}
    >
      <div className="study-figure-panel" data-panel="california">
        <LinePanel
          data={revenueLines.lines}
          ticks={californiaTicks(revenueLines.lines)}
          label={copy.title}
          series={[
            {
              key: SERIES_KEYS.incomeTax,
              name: copy.series.incomeTax,
              style: "main",
            },
            {
              key: SERIES_KEYS.net,
              name: copy.series.net,
              style: "comparison",
            },
          ]}
        />
      </div>
    </Figure>
  );
}
