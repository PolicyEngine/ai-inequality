import React from "react";
import defaultIncomeDistributionData from "../data/incomeDistributionData.json";
import defaultSweepData from "../data/shiftSweepData.json";
import "./BaselineDistributionSummary.css";

function formatPercent(value) {
  return value == null ? "-" : `${(value * 100).toFixed(1)}%`;
}

function positiveCapitalShares(sweepData, incomeDistributionData) {
  const baselineFacts = sweepData.metadata?.baseline_facts ?? {};
  if (baselineFacts.positive_capital_top_10_share != null) {
    return {
      top10: baselineFacts.positive_capital_top_10_share,
      top1: baselineFacts.positive_capital_top_1_share,
      top01: baselineFacts.positive_capital_top_0_1_share,
    };
  }

  const positiveCapitalBenchmark =
    incomeDistributionData?.capitalBenchmarks?.local?.find(
      (row) => row.label === "Positive capital income, ranked by market income",
    );

  return {
    top10: positiveCapitalBenchmark?.shares?.top10?.share,
    top1: positiveCapitalBenchmark?.shares?.top1?.share,
    top01: positiveCapitalBenchmark?.shares?.top01?.share,
  };
}

function groupsForSweep(sweepData, incomeDistributionData) {
  const baselineScenario =
    sweepData.scenarios.find((scenario) => scenario.shift_pct === 0) ??
    sweepData.scenarios[0];
  const capitalShares = positiveCapitalShares(
    sweepData,
    incomeDistributionData,
  );

  return [
    {
      label: "Top 10%",
      market: baselineScenario?.market_top_10_share,
      net: baselineScenario?.net_top_10_share,
      capital: capitalShares.top10,
    },
    {
      label: "Top 1%",
      market: baselineScenario?.market_top_1_share,
      net: baselineScenario?.net_top_1_share,
      capital: capitalShares.top1,
    },
    {
      label: "Top 0.1%",
      market: baselineScenario?.market_top_0_1_share,
      net: baselineScenario?.net_top_0_1_share,
      capital: capitalShares.top01,
    },
  ];
}

function BaselineDistributionSummary({
  sweepData = defaultSweepData,
  incomeDistributionData = defaultIncomeDistributionData,
}) {
  const topGroups = groupsForSweep(sweepData, incomeDistributionData);

  return (
    <div
      className="baseline-distribution-summary"
      aria-label="Baseline income concentration"
    >
      <div className="baseline-distribution-copy">
        <h2>Baseline distribution</h2>
        <p>
          Before the experiment, positive capital income is already much more
          concentrated than market or net income. These groups rank households
          by baseline market income; positive capital income sets losses to zero
          to match the dollars shifted in the experiment.
        </p>
      </div>

      <div className="baseline-distribution-table-wrap">
        <table className="baseline-distribution-table">
          <thead>
            <tr>
              <th>Group</th>
              <th>Market income share</th>
              <th>Net income share</th>
              <th>Positive capital income share</th>
            </tr>
          </thead>
          <tbody>
            {topGroups.map((group) => (
              <tr key={group.label}>
                <th scope="row">{group.label}</th>
                <td>{formatPercent(group.market)}</td>
                <td>{formatPercent(group.net)}</td>
                <td>{formatPercent(group.capital)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default BaselineDistributionSummary;
