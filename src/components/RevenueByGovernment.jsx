import React from "react";

import Figure, { LineLegend } from "../charts/Figure";
import LinePanel, { LINE_STYLES } from "../charts/LinePanel";
import { niceTicks } from "../utils/chartTicks";
import { healthCoverageCopy, statesNotCounting } from "./healthCoverageCopy";

// The federal government and the states combined, each counting and not
// counting health coverage, as analysis/revenue_lines.py stores them. The
// states' tooltip prints its line not counting health coverage as the
// caption does, so it says "about even" wherever the caption would.
export const PANELS = [
  {
    id: "federal",
    counting: "federal_counting_health_change_b",
    notCounting: "federal_not_counting_health_change_b",
  },
  {
    id: "states",
    counting: "states_counting_health_change_b",
    notCounting: "states_not_counting_health_change_b",
    formatNotCounting: statesNotCounting,
  },
];

// One y-axis for both panels, so the states' line reads at its size beside
// the federal one. Its ticks cover both panels' values at every shift, and 0.
export function sharedTicks(lines) {
  const values = lines.flatMap((line) =>
    PANELS.flatMap((panel) => [line[panel.counting], line[panel.notCounting]]),
  );
  return niceTicks(Math.min(0, ...values), Math.max(0, ...values));
}

export default function RevenueByGovernment({ revenueLines, metadata, year }) {
  const copy = healthCoverageCopy(revenueLines).revenueByGovernment;
  const ticks = sharedTicks(revenueLines.lines);
  const legend = [
    { label: copy.series.counting, ...LINE_STYLES.main },
    { label: copy.series.notCounting, ...LINE_STYLES.comparison },
  ];

  return (
    <Figure
      id="revenue-by-government"
      title={copy.title}
      subtitle={copy.subtitle}
      legend={<LineLegend items={legend} />}
      footnote={copy.footnote}
      metadata={metadata}
      year={year}
    >
      <div className="study-figure-panels">
        {PANELS.map((panel) => (
          <div
            key={panel.id}
            className="study-figure-panel"
            data-panel={panel.id}
          >
            <h4 className="study-figure-panel-title">
              {copy.panels[panel.id]}
            </h4>
            <LinePanel
              data={revenueLines.lines}
              ticks={ticks}
              series={[
                {
                  key: panel.counting,
                  name: copy.series.counting,
                  style: "main",
                },
                {
                  key: panel.notCounting,
                  name: copy.series.notCounting,
                  style: "comparison",
                  format: panel.formatNotCounting,
                },
              ]}
            />
            <p className="study-figure-caption">{copy.captions[panel.id]}</p>
          </div>
        ))}
      </div>
    </Figure>
  );
}
