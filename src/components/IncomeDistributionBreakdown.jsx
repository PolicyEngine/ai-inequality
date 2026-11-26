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
import {
  AXIS_STYLE,
  GAIN,
  GRID_STYLE,
  LEGEND_STYLE,
  LOSS,
  SERIES,
  TEXT,
  TOOLTIP_ITEM_STYLE,
  TOOLTIP_LABEL_STYLE,
  ZERO_LINE,
} from "../charts/kitTheme";
import { TOOLTIP_STYLE } from "../utils/chartStyles";
import { niceTicks } from "../utils/chartTicks";

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

// Each segment's colour, by key, from the UI kit. The data file's own colours
// are ignored. Market income's segments take the first three series colours
// in order. In net income, taxes take the kit's loss gray and benefits its
// gain teal; the other two take the series colours that stay distinct from
// their neighbours in the stack: refundable credits teal-700 beside benefits,
// and market income sky beside the zero line.
export const SEGMENT_COLOURS = {
  labor: SERIES[0],
  capital: SERIES[1],
  otherMarket: SERIES[2],
  market: SERIES[2],
  refundableCredits: SERIES[1],
  benefits: GAIN,
  taxes: LOSS,
};

// The order each concept stacks its segments, outward from zero. Benefits
// stack last so their teal touches only the refundable credits' teal-700.
const STACK_ORDER = {
  net: ["market", "refundableCredits", "benefits", "taxes"],
};

export function stackedComponents(conceptKey, components) {
  const order = STACK_ORDER[conceptKey];
  if (!order) return components;
  return [...components].sort(
    (a, b) => order.indexOf(a.key) - order.indexOf(b.key),
  );
}

// Legend names stay in ink; the swatch beside each carries the segment colour.
const legendText = (label) => (
  <span style={{ color: TEXT.muted }}>{label}</span>
);

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
                      style={{ background: SEGMENT_COLOURS[component.key] }}
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
              <CartesianGrid {...GRID_STYLE} />
              <XAxis
                type="number"
                ticks={ticks}
                domain={[ticks[0], ticks[ticks.length - 1]]}
                tickFormatter={view.formatter}
                tick={AXIS_STYLE}
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
                tick={AXIS_STYLE}
              />
              <ReferenceLine x={0} {...ZERO_LINE} />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                labelStyle={TOOLTIP_LABEL_STYLE}
                itemStyle={TOOLTIP_ITEM_STYLE}
                formatter={(value, name) => {
                  const component = concept.components.find(
                    (item) => item.key === name,
                  );
                  return [view.formatter(value), component?.label ?? name];
                }}
              />
              <Legend
                {...LEGEND_STYLE}
                formatter={(value) =>
                  legendText(
                    concept.components.find(
                      (component) => component.key === value,
                    )?.label ?? value,
                  )
                }
              />
              {stackedComponents(conceptKey, concept.components).map(
                (component) => (
                  <Bar
                    key={component.key}
                    dataKey={component.key}
                    stackId="income"
                    fill={SEGMENT_COLOURS[component.key]}
                    radius={[4, 4, 4, 4]}
                  />
                ),
              )}
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
