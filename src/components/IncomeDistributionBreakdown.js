import React, { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { IconChartBar, IconInfoCircle } from "@tabler/icons-react";
import incomeDistributionData from "../data/incomeDistributionData.json";
import { TOOLTIP_STYLE } from "../utils/chartStyles";
import { niceTicks } from "../utils/chartTicks";
import "./AnalysisSection.css";
import "./IncomeDistributionBreakdown.css";

const CONCEPTS = {
  market: {
    label: "Market income",
    summary:
      "Market income is pre-tax, pre-transfer household income from private sources. Here it is split into labor income, measured capital income, and the remaining market-income sources.",
  },
  net: {
    label: "Net income",
    summary:
      "Net income starts with market income, adds benefits and refundable credits, then subtracts taxes before refundable credits. This is the household income concept used for after-tax distributional comparisons.",
  },
};

const VIEWS = {
  composition: {
    label: "Composition",
    axisLabel: "Percent of group total",
    valueFor: (componentValue, group) =>
      group.total_b === 0 ? 0 : componentValue / group.total_b,
    formatter: (value) => `${(value * 100).toFixed(0)}%`,
    note: "Components are divided by that group's total income. Groups with losses can show negative or above-100% contributions.",
  },
  absolute: {
    label: "Absolute",
    axisLabel: "Aggregate dollars ($B)",
    valueFor: (componentValue) => componentValue,
    formatter: (value) => `$${value.toFixed(0)}B`,
    note: "Shows aggregate dollars in each percentile group.",
  },
  shareOfTotal: {
    label: "Share of total",
    axisLabel: "Percent of national total",
    valueFor: (componentValue, group, concept) =>
      concept.total_b === 0 ? 0 : componentValue / concept.total_b,
    formatter: (value) => `${(value * 100).toFixed(1)}%`,
    note: "Shows each component's contribution as a percent of national total income for the selected concept.",
  },
};

const TOP_SHARE_KEYS = ["top10", "top1", "top01"];

function formatBenchmarkPercent(value) {
  return `${(value * 100).toFixed(1)}%`;
}

function chartRows(conceptKey, viewKey) {
  const concept = incomeDistributionData[conceptKey];
  const view = VIEWS[viewKey];
  return concept.groups.map((group) => {
    const row = {
      group: group.label,
      total: view.valueFor(group.total_b, group, concept),
    };
    concept.components.forEach((component) => {
      row[component.key] = view.valueFor(
        group.components_b[component.key],
        group,
        concept,
      );
    });
    return row;
  });
}

function ticksForRows(rows, components) {
  const stackExtents = rows.flatMap((row) => {
    const positiveTotal = components.reduce(
      (total, component) => total + Math.max(0, row[component.key] ?? 0),
      0,
    );
    const negativeTotal = components.reduce(
      (total, component) => total + Math.min(0, row[component.key] ?? 0),
      0,
    );
    return [negativeTotal, positiveTotal];
  });
  const min = Math.min(0, ...stackExtents);
  const max = Math.max(0, ...stackExtents);
  return niceTicks(min, max, 6);
}

function CapitalBenchmarkDisclosure() {
  const benchmark = incomeDistributionData.capitalBenchmarks;

  if (!benchmark) {
    return null;
  }

  return (
    <details className="income-benchmark-disclosure">
      <summary>
        <span>Benchmark capital-income concentration</span>
        <small>IRS, CBO, and Federal Reserve comparisons</small>
      </summary>

      <div className="income-benchmark-content">
        <p>{benchmark.summary}</p>

        <div className="income-benchmark-table-wrap">
          <table className="income-benchmark-table">
            <thead>
              <tr>
                <th>PolicyEngine baseline</th>
                {TOP_SHARE_KEYS.map((key) => (
                  <th key={key}>{benchmark.local[0].shares[key].label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {benchmark.local.map((row) => (
                <tr key={row.label}>
                  <td>
                    <strong>{row.label}</strong>
                    <span>{row.description}</span>
                  </td>
                  {TOP_SHARE_KEYS.map((key) => (
                    <td key={key}>
                      {formatBenchmarkPercent(row.shares[key].share)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="income-benchmark-sources">
          {benchmark.external.map((item) => (
            <article key={item.source}>
              <h4>
                <a href={item.url} target="_blank" rel="noreferrer">
                  {item.source}
                </a>
              </h4>
              <p>{item.benchmark}</p>
              <span>{item.comparison}</span>
            </article>
          ))}
        </div>
      </div>
    </details>
  );
}

function IncomeDistributionBreakdown() {
  const [conceptKey, setConceptKey] = useState("market");
  const [viewKey, setViewKey] = useState("composition");
  const concept = incomeDistributionData[conceptKey];
  const view = VIEWS[viewKey];
  const rows = chartRows(conceptKey, viewKey);
  const ticks = ticksForRows(rows, concept.components);

  return (
    <section className="section income-background">
      <div className="analysis-section income-background-inner">
        <div className="analysis-header">
          <div className="analysis-icon-wrapper">
            <IconChartBar size={28} stroke={1.5} />
          </div>
          <h2>Current income distribution</h2>
          <p className="analysis-subtitle">
            The baseline distribution matters before any experiment: who has
            labor income, who has capital income, who receives transfers, and
            where taxes are paid. Households are shown for{" "}
            {incomeDistributionData.year}, with the top decile split into
            P90-99, P99-99.9, and the top 0.1%.
          </p>
        </div>

        <div className="analysis-card income-breakdown-card">
          <div className="income-breakdown-controls">
            <div>
              <div className="income-breakdown-label">Income concept</div>
              <div
                className="analysis-tabs"
                role="tablist"
                aria-label="Income concept"
              >
                {Object.entries(CONCEPTS).map(([key, option]) => (
                  <button
                    key={key}
                    type="button"
                    role="tab"
                    aria-selected={conceptKey === key}
                    className={`analysis-tab ${conceptKey === key ? "active" : ""}`}
                    onClick={() => setConceptKey(key)}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <div className="income-breakdown-label">View</div>
              <div className="analysis-tabs" role="tablist" aria-label="View">
                {Object.entries(VIEWS).map(([key, option]) => (
                  <button
                    key={key}
                    type="button"
                    role="tab"
                    aria-selected={viewKey === key}
                    className={`analysis-tab ${viewKey === key ? "active" : ""}`}
                    onClick={() => setViewKey(key)}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="income-definition-grid">
            <div>
              <h3>{concept.title}</h3>
              <p>{CONCEPTS[conceptKey].summary}</p>
            </div>
            <div>
              <h3>Components</h3>
              <div className="income-component-list">
                {concept.components.map((component) => (
                  <div key={component.key} className="income-component-item">
                    <span
                      className="income-component-swatch"
                      style={{ background: component.color }}
                    />
                    <div>
                      <strong>{component.label}</strong>
                      <span>{component.description}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <ResponsiveContainer width="100%" height={520}>
            <BarChart
              data={rows}
              layout="vertical"
              margin={{ left: 28, right: 30, top: 20, bottom: 15 }}
              stackOffset="sign"
            >
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
              <XAxis
                type="number"
                ticks={ticks}
                domain={[ticks[0], ticks[ticks.length - 1]]}
                tickFormatter={view.formatter}
                tick={{ fontSize: 12 }}
                label={{
                  value: view.axisLabel,
                  position: "insideBottom",
                  offset: -8,
                  style: { fontSize: 13 },
                }}
              />
              <YAxis
                type="category"
                dataKey="group"
                width={92}
                tick={{ fontSize: 12 }}
              />
              <ReferenceLine x={0} stroke="#4a5568" strokeWidth={1.3} />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                formatter={(value, name) => {
                  const component = concept.components.find(
                    (item) => item.key === name,
                  );
                  return [view.formatter(value), component?.label ?? name];
                }}
              />
              <Legend
                formatter={(value) =>
                  concept.components.find(
                    (component) => component.key === value,
                  )?.label ?? value
                }
              />
              {concept.components.map((component) => (
                <Bar
                  key={component.key}
                  dataKey={component.key}
                  stackId="income"
                  fill={component.color}
                  radius={[4, 4, 4, 4]}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>

          <div className="analysis-callout income-breakdown-note">
            <IconInfoCircle size={20} stroke={1.5} />
            <div>
              {view.note} {incomeDistributionData.grouping}
            </div>
          </div>

          <CapitalBenchmarkDisclosure />
        </div>
      </div>
    </section>
  );
}

export default IncomeDistributionBreakdown;
