import React, { useMemo, useState } from "react";
import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { IconArrowsExchange, IconInfoCircle } from "@tabler/icons-react";
import defaultSweepData from "../data/shiftSweepData.json";
import { TOOLTIP_STYLE } from "../utils/chartStyles";
import { niceTicks } from "../utils/chartTicks";
import { policyEngineLabel } from "../utils/modelMetadata";
import { useRovingRadioGroup } from "../utils/useRovingRadioGroup";
import "./AnalysisSection.css";
import "./ShiftSweep.css";

const FEDERAL_BUCKETS = [
  {
    key: "rev_fed_income_tax_net",
    label: "Net federal income tax (after refundable credits)",
    color: "#17354F",
  },
  {
    key: "rev_payroll_all",
    label: "Payroll tax (employee + employer + self-employment)",
    color: "#DD6B20",
  },
  {
    key: "rev_fed_benefits",
    label: "Federal benefits (negated)",
    color: "#B45309",
  },
];

const STATE_BUCKETS = [
  {
    key: "rev_state_income_tax_net",
    label: "Net state income tax (after refundable credits)",
    color: "#17354F",
  },
  {
    key: "rev_state_benefits",
    label: "State benefits (negated)",
    color: "#B45309",
  },
];

const FED_INCOME_TAX_BUCKETS = [
  {
    key: "rev_fed_main",
    label: "Main ordinary-rate tax",
    color: "#17354F",
  },
  {
    key: "rev_fed_capgains",
    label: "Preferential capital gains / qualified div tax",
    color: "#2C6496",
  },
  {
    key: "rev_fed_amt",
    label: "Alternative minimum tax",
    color: "#39C6C0",
  },
  {
    key: "rev_fed_niit",
    label: "Net investment income tax (3.8%)",
    color: "#227773",
  },
  {
    key: "rev_fed_nonref",
    label: "Nonrefundable credits reduction (−Δ)",
    color: "#D7F6F4",
  },
  {
    key: "rev_fed_other",
    label: "Other (recapture, unreported payroll, retirement penalty)",
    color: "#85E0DC",
  },
];

const MTR_SOURCE_COLORS = {
  employment_income: "#DD6B20",
  self_employment_income: "#B45309",
  long_term_capital_gains: "#17354F",
  short_term_capital_gains: "#2C6496",
  qualified_dividend_income: "#39C6C0",
  non_qualified_dividend_income: "#227773",
  taxable_interest_income: "#5DD4CF",
  rental_income: "#8B5CF6",
};

const billionFmt = (value, { precision = 0, currencySymbol = "$" } = {}) => {
  const sign = value >= 0 ? "+" : "";
  return `${currencySymbol}${sign}${value.toFixed(precision)}B`;
};
const axisPctFmt = (value) => {
  const pct = value * 100;
  if (Math.abs(pct) >= 10 || pct === 0) {
    return `${Math.round(pct)}%`;
  }
  return `${pct.toFixed(1)}%`;
};
const shareTooltipFmt = (value) => `${(value * 100).toFixed(1)}%`;
const shareFmt = (value) => {
  const pct = value * 100;
  if (Math.abs(pct) >= 10) {
    return `${pct.toFixed(0)}%`;
  }
  if (Math.abs(pct) >= 1) {
    return `${pct.toFixed(1)}%`;
  }
  return `${pct.toFixed(2)}%`;
};

const PROPORTION_FALLBACK_TICKS = [0, 0.2, 0.4, 0.6, 0.8, 1];

const CONCEPTS = {
  market: {
    label: "Market income",
    color: "#DD6B20",
    description: "pre-tax, pre-transfer household market income",
  },
  net: {
    label: "Net income",
    color: "#319795",
    description: "household net income after taxes and transfers",
  },
};

function measuresForMetadata(metadata) {
  const currencySymbol = metadata.currency_symbol ?? "$";
  return {
    gini: {
      label: "Gini coefficient",
      field: "Gini",
      axisLabel: "Gini coefficient",
      valueFormatter: (value) => value.toFixed(4),
      tooltipFormatter: (value) => value.toFixed(4),
      description:
        "Inequality on a 0-1 scale, where higher values mean income is more concentrated.",
    },
    top10: {
      label: "Top 10% share",
      field: "Top10",
      axisLabel: "Share of income",
      valueFormatter: shareFmt,
      tooltipFormatter: shareTooltipFmt,
      description:
        "Share of household income received by the top 10% of households.",
    },
    top1: {
      label: "Top 1% share",
      field: "Top1",
      axisLabel: "Share of income",
      valueFormatter: shareFmt,
      tooltipFormatter: shareTooltipFmt,
      description:
        "Share of household income received by the top 1% of households.",
    },
    top0_1: {
      label: "Top 0.1% share",
      field: "Top0_1",
      axisLabel: "Share of income",
      valueFormatter: shareFmt,
      tooltipFormatter: shareTooltipFmt,
      description:
        "Share of household income received by the top 0.1% of households.",
    },
    revenue: {
      label: metadata.revenue_label ?? "Net federal revenue change",
      field: "Revenue",
      dataKey: "revenue",
      color: "#2C6496",
      axisLabel:
        metadata.revenue_axis_label ??
        `Change vs baseline (${currencySymbol}B)`,
      valueFormatter: (value) => billionFmt(value, { currencySymbol }),
      tooltipFormatter: (value) =>
        billionFmt(value, { precision: 1, currencySymbol }),
      description:
        metadata.revenue_description ??
        "Net government revenue change = taxes (household tax before refundable credits + employer payroll) minus transfers (refundable credits + benefits). Reconciles to the household net-income identity.",
    },
  };
}

const MEASURE_OPTIONS = ["gini", "top10", "top1", "top0_1", "revenue"];
const CONCEPT_OPTIONS = ["market", "net"];

function buildFederalRow(scenario) {
  const fedRefundable =
    (scenario.refundable_credits_change_b ?? 0) -
    (scenario.state_refundable_credits_change_b ?? 0);
  const rev_fed_income_tax_net =
    (scenario.fed_income_tax_before_refundable_credits_change_b ?? 0) -
    fedRefundable;
  const rev_payroll_all =
    (scenario.employer_payroll_change_b ?? 0) +
    (scenario.employee_ss_tax_change_b ?? 0) +
    (scenario.employee_medicare_tax_change_b ?? 0) +
    (scenario.self_employment_tax_change_b ?? 0);
  // Federal benefits = total household benefits − state-funded benefits.
  const fedBenefitsChange =
    (scenario.benefits_change_b ?? 0) -
    (scenario.state_benefits_change_b ?? 0);
  const rev_fed_benefits = -fedBenefitsChange;
  return {
    rev_fed_income_tax_net,
    rev_payroll_all,
    rev_fed_benefits,
    revenue:
      rev_fed_income_tax_net + rev_payroll_all + rev_fed_benefits,
  };
}

function buildStateRow(scenario, stateCode) {
  const state = scenario.state_deltas?.[stateCode] ?? {};
  const rev_state_income_tax_net =
    (state.state_tax_before_refundable_credits_change_b ?? 0) -
    (state.state_refundable_credits_change_b ?? 0);
  const rev_state_benefits = -(state.state_benefits_change_b ?? 0);
  return {
    rev_state_income_tax_net,
    rev_state_benefits,
    revenue: rev_state_income_tax_net + rev_state_benefits,
  };
}

function dataForChart(sweepData) {
  return sweepData.scenarios.map((scenario) => ({
    shift: scenario.shift_pct,
    label: scenario.label,
    marketGini: scenario.market_gini,
    netGini: scenario.net_gini,
    marketTop10: scenario.market_top_10_share,
    marketTop1: scenario.market_top_1_share,
    marketTop0_1: scenario.market_top_0_1_share,
    netTop10: scenario.net_top_10_share,
    netTop1: scenario.net_top_1_share,
    netTop0_1: scenario.net_top_0_1_share,
    // revenue here is fed+state overall — other charts use it; the
    // decomposition chart recomputes the total for the selected
    // jurisdiction.
    revenue: scenario.revenue_change_b,
    state_deltas: scenario.state_deltas ?? {},
    // Federal income-tax attribution (signed; nonref is flipped so positive
    // means more tax collected because fewer credits were applied).
    rev_fed_main: scenario.fed_main_rates_change_b ?? 0,
    rev_fed_capgains: scenario.fed_capital_gains_tax_change_b ?? 0,
    rev_fed_amt: scenario.fed_amt_change_b ?? 0,
    rev_fed_niit: scenario.fed_niit_change_b ?? 0,
    rev_fed_nonref: -(scenario.fed_nonrefundable_credits_change_b ?? 0),
    rev_fed_other: scenario.fed_other_income_tax_items_change_b ?? 0,
    _scenario: scenario,
  }));
}

function decompositionDataForJurisdiction(chartData, jurisdiction) {
  return chartData.map((row) => {
    const extras =
      jurisdiction === "federal"
        ? buildFederalRow(row._scenario)
        : buildStateRow(row._scenario, jurisdiction);
    return { ...row, ...extras };
  });
}

function metricConfig(measures, measureKey, conceptKey) {
  const measure = measures[measureKey];
  if (measureKey === "revenue") {
    return measure;
  }

  const concept = CONCEPTS[conceptKey];
  return {
    ...measure,
    label: `${concept.label} ${measure.label}`,
    dataKey: `${conceptKey}${measure.field}`,
    color: concept.color,
    description: `${measure.description} Uses ${concept.description}.`,
  };
}

function yTicksForConfig(config, chartData) {
  const values = chartData
    .map((point) => point[config.dataKey])
    .filter((value) => Number.isFinite(value));

  if (values.length === 0) {
    return config.dataKey === "revenue" ? [0] : PROPORTION_FALLBACK_TICKS;
  }

  const dataMin = Math.min(...values);
  const dataMax = Math.max(...values);

  if (config.dataKey === "revenue") {
    return niceTicks(Math.min(0, dataMin), Math.max(0, dataMax), 6);
  }

  // Proportion measure (Gini, income shares): tighten the Y-axis to the
  // observed range so small sweep-level differences are visible, rather
  // than always spanning the full [0, 1] domain. Pad ~15% on each side
  // and clamp within [0, 1].
  const range = Math.max(dataMax - dataMin, 1e-6);
  const pad = range * 0.15;
  const low = Math.max(0, dataMin - pad);
  const high = Math.min(1, dataMax + pad);
  return niceTicks(low, high, 6);
}

function summaryForMetric(measureKey, conceptKey, config, chartData, metadata) {
  const basePoint = chartData[0];
  const endPoint = chartData[chartData.length - 1];
  const shift50 = chartData.find((scenario) => scenario.shift === 50);
  const shift100 = chartData.find((scenario) => scenario.shift === 100);
  const startValue = basePoint?.[config.dataKey];
  const endValue = endPoint?.[config.dataKey];
  const laborTerm = metadata.labor_label ?? "labor";

  if (measureKey === "gini") {
    return (
      <>
        {config.label} rises from {startValue.toFixed(3)} at baseline to{" "}
        {endValue.toFixed(3)} at a 100% shift.{" "}
        {conceptKey === "net"
          ? "Current law dampens the shock, but it does not come close to offsetting it."
          : `This is the pre-tax, pre-transfer distributional effect of routing ${laborTerm} income through existing capital holdings.`}
      </>
    );
  }

  if (measureKey !== "revenue") {
    const direction = endValue >= startValue ? "rises" : "falls";
    return (
      <>
        {config.label} {direction} from {config.valueFormatter(startValue)} at
        baseline to {config.valueFormatter(endValue)} at a 100% shift. This
        traces how the income distribution changes when {laborTerm} income is
        rerouted through existing capital holdings.
      </>
    );
  }

  const trough = chartData.reduce(
    (min, row) => (row.revenue < min.revenue ? row : min),
    chartData[0],
  );
  return (
    <>
      {config.label} reaches {config.valueFormatter(shift50?.revenue ?? 0)} at a
      50% shift, bottoms out at {config.valueFormatter(trough?.revenue ?? 0)} at
      a {trough?.shift ?? 80}% shift, and rebounds to{" "}
      {config.valueFormatter(shift100?.revenue ?? 0)} at a 100% shift.{" "}
      {metadata.revenue_summary_note ??
        "Capital-gains tax and NIIT accelerate at the top of the sweep, while EITC and refundable CTC collapse once labor income approaches zero."}
    </>
  );
}

function RevenueDecompositionChart({
  chartData,
  currencySymbol,
  buckets,
  title,
  axisLabel,
  showTotalLine = true,
  unit = "dollars",
  denominatorB = null, // denominator in $B, used when unit === "share"
}) {
  // Share mode scales each bucket value by 100 / denominatorB.
  const scale = unit === "share" && denominatorB ? 100 / denominatorB : 1;
  const scaledData = chartData.map((row) => {
    const next = { ...row };
    for (const bucket of buckets) {
      if (row[bucket.key] != null) {
        next[bucket.key] = row[bucket.key] * scale;
      }
    }
    if (row.revenue != null) next.revenue = row.revenue * scale;
    return next;
  });

  const values = scaledData.flatMap((row) => {
    const pos = buckets
      .map((b) => Math.max(0, row[b.key] ?? 0))
      .reduce((a, b) => a + b, 0);
    const neg = buckets
      .map((b) => Math.min(0, row[b.key] ?? 0))
      .reduce((a, b) => a + b, 0);
    return [pos, neg, showTotalLine ? row.revenue : 0];
  });
  const absMax = Math.max(Math.abs(Math.min(0, ...values)), Math.abs(Math.max(0, ...values))) || 1;
  const ticks = niceTicks(-absMax, absMax, 7);

  const tickFormatter = (v) =>
    unit === "share"
      ? `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`
      : `${currencySymbol}${v >= 0 ? "+" : ""}${v.toFixed(0)}B`;
  const tooltipFormatter = (v) =>
    unit === "share"
      ? `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`
      : `${currencySymbol}${v >= 0 ? "+" : ""}${v.toFixed(1)}B`;
  const resolvedAxisLabel =
    unit === "share"
      ? "Change vs baseline (% of income + payroll tax revenue)"
      : axisLabel;

  return (
    <>
      <h3 className="analysis-chart-title">{title}</h3>
      <ResponsiveContainer width="100%" height={420}>
        <ComposedChart
          data={scaledData}
          margin={{ left: 20, right: 30, top: 10, bottom: 40 }}
          stackOffset="sign"
        >
          <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
          <XAxis
            dataKey="shift"
            tickFormatter={(value) => `${value}%`}
            tick={{ fontSize: 12 }}
            label={{
              value: "Share of labor income shifted to capital",
              position: "bottom",
              offset: 0,
              style: { fontSize: 13 },
            }}
          />
          <YAxis
            ticks={ticks}
            domain={[ticks[0], ticks[ticks.length - 1]]}
            tickFormatter={tickFormatter}
            tick={{ fontSize: 12 }}
            label={{
              value: resolvedAxisLabel,
              angle: -90,
              position: "insideLeft",
              offset: -10,
              style: { fontSize: 13 },
            }}
          />
          <ReferenceLine y={0} stroke="#718096" strokeDasharray="4 4" />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            formatter={(value, name) => [tooltipFormatter(value), name]}
            labelFormatter={(value) =>
              scaledData.find((row) => row.shift === value)?.label ??
              `${value}% shift`
            }
          />
          <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
          {buckets.map((bucket) => (
            <Area
              key={bucket.key}
              type="linear"
              dataKey={bucket.key}
              stackId="decomposition"
              stroke={bucket.color}
              fill={bucket.color}
              fillOpacity={0.75}
              name={bucket.label}
              isAnimationActive={false}
            />
          ))}
          {showTotalLine && (
            <Line
              type="monotone"
              dataKey="revenue"
              stroke="#1a202c"
              strokeWidth={3}
              strokeDasharray="4 2"
              dot={{ r: 3, fill: "#1a202c" }}
              activeDot={{ r: 5 }}
              name="Net (sum of components)"
              isAnimationActive={false}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </>
  );
}

function FederalMtrChart({ sweepData, metric }) {
  // metric: "fed_income_tax_mtr" (after refundable credits) or
  //         "fed_income_tax_before_refundable_credits_mtr"
  const scenarios = useMemo(
    () => sweepData.scenarios ?? [],
    [sweepData],
  );
  const perSource = useMemo(() => {
    const bySource = new Map();
    for (const scenario of scenarios) {
      const shift = scenario.shift_pct;
      const mtrs = scenario.federal_mtrs ?? [];
      for (const row of mtrs) {
        const key = row.source;
        if (!bySource.has(key)) {
          bySource.set(key, { source: key, label: row.label, points: [] });
        }
        const value = row[metric];
        if (Number.isFinite(value)) {
          bySource.get(key).points.push({ shift, value });
        }
      }
    }
    return Array.from(bySource.values());
  }, [scenarios, metric]);

  const chartData = scenarios
    .filter((s) => (s.federal_mtrs ?? []).length > 0)
    .map((s) => {
      const row = { shift: s.shift_pct, label: s.label };
      for (const mtrRow of s.federal_mtrs ?? []) {
        const value = mtrRow[metric];
        if (Number.isFinite(value)) {
          row[mtrRow.source] = value;
        }
      }
      return row;
    });

  if (perSource.length === 0 || chartData.length === 0) {
    return null;
  }

  const values = chartData.flatMap((r) =>
    perSource.map((s) => r[s.source]).filter((v) => Number.isFinite(v)),
  );
  const dataMin = Math.min(0, ...values);
  const dataMax = Math.max(...values);
  const ticks = niceTicks(dataMin, Math.max(dataMax, 0.05), 6);

  const titleByMetric = {
    fed_income_tax_mtr:
      "Dollar-weighted federal income tax MTR (after refundable credits)",
    fed_income_tax_before_refundable_credits_mtr:
      "Dollar-weighted federal income tax MTR (before refundable credits)",
    fed_income_plus_payroll_tax_mtr:
      "Dollar-weighted federal income + payroll tax MTR",
  };
  const title = titleByMetric[metric] ?? "Dollar-weighted federal MTR";
  const descriptionByMetric = {
    fed_income_plus_payroll_tax_mtr:
      "Each line shows the dollar-weighted marginal tax rate on a +1% bump in that income source against federal income tax (after refundable credits) + employer + employee payroll + self-employment tax. Labor sources now bear FICA on top of income tax; capital sources don't, so the gap reverses relative to income-tax-only.",
  };
  const description =
    descriptionByMetric[metric] ??
    "Each line shows the dollar-weighted marginal tax rate on a +1% bump in that income source. Labor sources typically pay lower rates than concentrated capital sources when measured on income tax alone because capital income is held predominantly by top-bracket households.";

  return (
    <div className="shift-sweep-mtr-chart">
      <h3 className="analysis-chart-title">{title}</h3>
      <p className="shift-sweep-description">{description}</p>
      <ResponsiveContainer width="100%" height={380}>
        <LineChart
          data={chartData}
          margin={{ left: 20, right: 30, top: 10, bottom: 40 }}
        >
          <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
          <XAxis
            dataKey="shift"
            tickFormatter={(value) => `${value}%`}
            tick={{ fontSize: 12 }}
            label={{
              value: "Share of labor income shifted to capital",
              position: "bottom",
              offset: 0,
              style: { fontSize: 13 },
            }}
          />
          <YAxis
            ticks={ticks}
            domain={[ticks[0], ticks[ticks.length - 1]]}
            tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
            tick={{ fontSize: 12 }}
            label={{
              value: "Dollar-weighted MTR",
              angle: -90,
              position: "insideLeft",
              offset: -10,
              style: { fontSize: 13 },
            }}
          />
          <ReferenceLine y={0} stroke="#718096" strokeDasharray="4 4" />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            formatter={(value, name) => [`${(value * 100).toFixed(1)}%`, name]}
            labelFormatter={(value) =>
              chartData.find((row) => row.shift === value)?.label ??
              `${value}% shift`
            }
          />
          <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
          {perSource.map((s) => (
            <Line
              key={s.source}
              type="monotone"
              dataKey={s.source}
              stroke={MTR_SOURCE_COLORS[s.source] ?? "#4a5568"}
              strokeWidth={2}
              dot={{ r: 2.5 }}
              activeDot={{ r: 4 }}
              name={s.label}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function DecileImpactChart({ sweepData, unit = "dollars" }) {
  const [selectedShift, setSelectedShift] = useState(50);
  const decileImpacts =
    sweepData?.metadata?.baseline_facts?.decile_impacts ?? null;
  const availableShifts = useMemo(
    () =>
      (decileImpacts?.scenarios ?? [])
        .map((s) => s.shift_pct)
        .filter((pct) => pct > 0),
    [decileImpacts],
  );
  const rows = useMemo(() => {
    if (!decileImpacts) return [];
    const scenario =
      decileImpacts.scenarios.find((s) => s.shift_pct === selectedShift) ??
      decileImpacts.scenarios[decileImpacts.scenarios.length - 1];
    if (!scenario) return [];
    return scenario.deciles
      .filter((d) => Number.isFinite(d.pct_change))
      .map((d) => ({
        decile: `D${d.decile}`,
        pct: d.pct_change,
        dollars_b: (d.delta_mean_net * d.weight) / 1e9,
        delta_mean: d.delta_mean_net,
        baseline_mean: d.baseline_mean_net,
      }));
  }, [decileImpacts, selectedShift]);

  if (!decileImpacts || rows.length === 0) {
    return null;
  }

  const field = unit === "share" ? "pct" : "dollars_b";
  const values = rows.map((r) => r[field]);
  const absMax =
    Math.max(Math.abs(Math.min(0, ...values)), Math.abs(Math.max(0, ...values))) || 1;
  const ticks = niceTicks(-absMax, absMax, 7);

  return (
    <div className="shift-sweep-state-exposure">
      <div className="shift-sweep-state-header">
        <h3 className="analysis-chart-title">
          Household net-income change by market-income decile, at{" "}
          {selectedShift}% shift
        </h3>
        <div
          className="analysis-tabs shift-sweep-tabs"
          role="radiogroup"
          aria-label="Shift percentage"
        >
          {availableShifts
            .filter((pct) => pct % 20 === 0 && pct > 0)
            .map((pct) => (
              <button
                key={pct}
                type="button"
                role="radio"
                aria-checked={selectedShift === pct}
                className={`analysis-tab ${selectedShift === pct ? "active" : ""}`}
                onClick={() => setSelectedShift(pct)}
              >
                {pct}%
              </button>
            ))}
        </div>
      </div>
      <p className="shift-sweep-description">
        Households are bucketed into deciles by weighted baseline market
        income; decile membership is held fixed across scenarios.
        {unit === "share"
          ? " Bars show the change in each decile's mean household net income as % of its baseline mean. D1 is omitted because its baseline mean is negative (losses dominate)."
          : " Bars show the aggregate dollar change in each decile's total net income ($B)."}
      </p>
      <ResponsiveContainer width="100%" height={360}>
        <BarChart
          data={rows}
          margin={{ left: 10, right: 30, top: 10, bottom: 40 }}
        >
          <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
          <XAxis
            dataKey="decile"
            tick={{ fontSize: 12, fontWeight: 600 }}
            label={{
              value: "Baseline market-income decile",
              position: "bottom",
              offset: 0,
              style: { fontSize: 13 },
            }}
          />
          <YAxis
            ticks={ticks}
            domain={[ticks[0], ticks[ticks.length - 1]]}
            tickFormatter={(v) =>
              unit === "share"
                ? `${v >= 0 ? "+" : ""}${v.toFixed(0)}%`
                : `$${v >= 0 ? "+" : ""}${v.toFixed(0)}B`
            }
            tick={{ fontSize: 12 }}
            label={{
              value:
                unit === "share"
                  ? "Change in mean household net income (%)"
                  : "Change in decile-total net income ($B)",
              angle: -90,
              position: "insideLeft",
              offset: -10,
              style: { fontSize: 13 },
            }}
          />
          <ReferenceLine y={0} stroke="#718096" />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            formatter={(value, name) => [
              unit === "share"
                ? `${value >= 0 ? "+" : ""}${value.toFixed(1)}%`
                : `$${value >= 0 ? "+" : ""}${value.toFixed(1)}B`,
              name,
            ]}
            labelFormatter={(label) => label}
          />
          <Bar
            dataKey={field}
            name="Net income change"
            isAnimationActive={false}
          >
            {rows.map((row, i) => (
              <Cell
                key={`cell-${i}`}
                fill={row[field] >= 0 ? "#227773" : "#DD6B20"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function StateExposureChart({ sweepData, currencySymbol, unit = "dollars" }) {
  const [selectedShift, setSelectedShift] = useState(50);
  const baselineTotals = sweepData?.metadata?.baseline_facts?.totals;

  const { ranked, availableShifts } = useMemo(() => {
    const withDeltas = sweepData.scenarios.filter(
      (s) => s.state_deltas && Object.keys(s.state_deltas).length > 0,
    );
    const shifts = withDeltas.map((s) => s.shift_pct);
    const scenario =
      withDeltas.find((s) => s.shift_pct === selectedShift) ?? withDeltas[0];
    if (!scenario) {
      return { ranked: [], availableShifts: shifts };
    }
    const rows = Object.entries(scenario.state_deltas).map(([code, d]) => {
      const stateTax = d.state_tax_before_refundable_credits_change_b ?? 0;
      const stateRef = d.state_refundable_credits_change_b ?? 0;
      const stateBen = d.state_benefits_change_b ?? 0;
      const netDollarsB = stateTax - stateRef - stateBen;
      // Denominator in $B for share mode: state's own baseline net state
      // revenue (tax − refundable credits − state benefits).
      const baseline = baselineTotals?.per_state?.[code];
      const denominatorB = baseline
        ? ((baseline.household_state_tax_before_refundable_credits ?? 0) -
            (baseline.household_refundable_state_tax_credits ?? 0) -
            (baseline.household_state_benefits ?? 0)) /
          1e9
        : null;
      const shareValue =
        unit === "share" && denominatorB && denominatorB !== 0
          ? (netDollarsB / denominatorB) * 100
          : null;
      return {
        state: code,
        stateTax,
        stateRef,
        stateBen,
        stateNet: unit === "share" && shareValue != null
          ? shareValue
          : netDollarsB,
        stateNetDollarsB: netDollarsB,
        stateNetShare: shareValue,
        denominatorB,
      };
    });
    // Drop states with no meaningful denominator in share mode.
    const valid = rows.filter(
      (r) => unit !== "share" || Number.isFinite(r.stateNetShare),
    );
    valid.sort((a, b) => b.stateNet - a.stateNet);
    return { ranked: valid, availableShifts: shifts };
  }, [sweepData, selectedShift, baselineTotals, unit]);

  if (ranked.length === 0) {
    return null;
  }

  const display = ranked;
  const values = display.map((r) => r.stateNet);
  const absMax = Math.max(Math.abs(Math.min(0, ...values)), Math.abs(Math.max(0, ...values))) || 1;
  const ticks = niceTicks(-absMax, absMax, 7);

  return (
    <div className="shift-sweep-state-exposure">
      <div className="shift-sweep-state-header">
        <h3 className="analysis-chart-title">
          State revenue exposure at {selectedShift}% shift
        </h3>
        <div
          className="analysis-tabs shift-sweep-tabs"
          role="radiogroup"
          aria-label="Shift percentage"
        >
          {availableShifts
            .filter((pct) => pct % 20 === 0 && pct > 0)
            .map((pct) => (
              <button
                key={pct}
                type="button"
                role="radio"
                aria-checked={selectedShift === pct}
                className={`analysis-tab ${selectedShift === pct ? "active" : ""}`}
                onClick={() => setSelectedShift(pct)}
              >
                {pct}%
              </button>
            ))}
        </div>
      </div>
      <p className="shift-sweep-description">
        All states with a state income tax, sorted descending by net change
        in state revenue at the selected shift level. Net = state income tax
        before refundable credits − refundable state credits − state-funded
        benefits. Teal gains, orange loses.
        {unit === "share"
          ? " In share mode, each state's change is expressed as % of its own baseline net state revenue — states without income tax (FL, TX, etc.) are dropped."
          : ""}
      </p>
      <ResponsiveContainer width="100%" height={Math.max(320, display.length * 22)}>
        <BarChart
          data={display}
          layout="vertical"
          margin={{ left: 10, right: 30, top: 10, bottom: 30 }}
        >
          <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
          <XAxis
            type="number"
            ticks={ticks}
            domain={[ticks[0], ticks[ticks.length - 1]]}
            tickFormatter={(v) =>
              unit === "share"
                ? `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`
                : `${currencySymbol}${v >= 0 ? "+" : ""}${v.toFixed(0)}B`
            }
            tick={{ fontSize: 12 }}
            label={{
              value:
                unit === "share"
                  ? "Change in state net revenue vs baseline (% of own baseline)"
                  : `Change in state net revenue vs baseline (${currencySymbol}B)`,
              position: "bottom",
              offset: 0,
              style: { fontSize: 13 },
            }}
          />
          <YAxis
            type="category"
            dataKey="state"
            width={40}
            interval={0}
            tick={{ fontSize: 11, fontWeight: 600 }}
          />
          <ReferenceLine x={0} stroke="#718096" />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            formatter={(value, name) => [
              unit === "share"
                ? `${value >= 0 ? "+" : ""}${value.toFixed(1)}%`
                : `${currencySymbol}${value >= 0 ? "+" : ""}${value.toFixed(2)}B`,
              name,
            ]}
            labelFormatter={(label) => `State: ${label}`}
          />
          <Bar
            dataKey="stateNet"
            name="Net state revenue change"
            isAnimationActive={false}
          >
            {display.map((row, i) => (
              <Cell
                key={`cell-${i}`}
                fill={row.stateNet >= 0 ? "#227773" : "#DD6B20"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

const UNIT_OPTIONS = [
  { key: "dollars", label: "$ billions" },
  { key: "share", label: "% of income + payroll tax revenue" },
];

function federalBaseDenominator(totals) {
  if (!totals?.national) return null;
  const n = totals.national;
  return (
    (n.fed_income_tax ?? 0) +
    (n.employer_payroll_tax ?? 0) +
    (n.employee_social_security_tax ?? 0) +
    (n.employee_medicare_tax ?? 0) +
    (n.self_employment_tax ?? 0)
  );
}

function stateBaseDenominator(totals, code) {
  const state = totals?.per_state?.[code];
  if (!state) return null;
  const own = (
    (state.household_state_tax_before_refundable_credits ?? 0) -
    (state.household_refundable_state_tax_credits ?? 0) -
    (state.household_state_benefits ?? 0)
  );
  // Fall back to federal base if the state has no income tax (e.g. TX, FL).
  return own > 0 ? own : null;
}

function ShiftSweep({ sweepData = defaultSweepData }) {
  const [selectedMeasure, setSelectedMeasure] = useState("gini");
  const [selectedConcept, setSelectedConcept] = useState("net");
  const [selectedJurisdiction, setSelectedJurisdiction] = useState("federal");
  const [selectedUnit, setSelectedUnit] = useState("dollars");
  const measureNav = useRovingRadioGroup(MEASURE_OPTIONS, selectedMeasure);
  const conceptNav = useRovingRadioGroup(CONCEPT_OPTIONS, selectedConcept);
  const metadata = sweepData.metadata ?? {};
  const docsUrl = metadata.model_url ?? "https://www.policyengine.org/us/model";
  const modelLabel = policyEngineLabel(metadata);
  const laborTerm = metadata.labor_label ?? "labor";
  const laborTitle = metadata.labor_title ?? "Labor";
  const measures = measuresForMetadata(metadata);
  const chartData = dataForChart(sweepData);
  const jurisdictionData = useMemo(
    () => decompositionDataForJurisdiction(chartData, selectedJurisdiction),
    [chartData, selectedJurisdiction],
  );
  const stateOptions = useMemo(() => {
    const last = sweepData.scenarios[sweepData.scenarios.length - 1];
    const deltas = last?.state_deltas ?? {};
    return Object.keys(deltas).sort();
  }, [sweepData]);
  const config = metricConfig(measures, selectedMeasure, selectedConcept);
  const yTicks = yTicksForConfig(config, chartData);
  const shiftTicks = niceTicks(
    chartData[0].shift,
    chartData[chartData.length - 1].shift,
    11,
  );
  const isRevenue = selectedMeasure === "revenue";
  const revenueFormatter = measures.revenue.valueFormatter;
  const currencySymbol = metadata.currency_symbol ?? "$";
  const hasStateDeltas = sweepData.scenarios.some(
    (s) => s.state_deltas && Object.keys(s.state_deltas).length > 0,
  );
  const baselineTotals = metadata?.baseline_facts?.totals;
  const hasBaselineTotals = Boolean(baselineTotals?.national);
  const decompositionDenominatorB =
    selectedJurisdiction === "federal"
      ? federalBaseDenominator(baselineTotals) / 1e9
      : stateBaseDenominator(baselineTotals, selectedJurisdiction) / 1e9;

  return (
    <div id="shift-sweep" className="analysis-section">
      <div className="analysis-header">
        <div className="analysis-icon-wrapper">
          <IconArrowsExchange size={28} stroke={1.5} />
        </div>
        <h2>{laborTitle}-to-capital shift experiment</h2>
        <p className="analysis-subtitle">
          Sweep the shock from 0% to 100% of positive {laborTerm} income shifted
          into positive capital income, and switch the chart between inequality,
          top shares, and fiscal outcomes.
        </p>
      </div>

      <div className="analysis-card">
        <div className="analysis-controls">
          <div className="shift-sweep-controls">
            <div className="shift-sweep-control-group">
              <div className="shift-sweep-label">Measure</div>
              <div
                className="analysis-tabs shift-sweep-tabs"
                role="radiogroup"
                aria-label="Measure"
              >
                {MEASURE_OPTIONS.map((key) => (
                  <button
                    key={key}
                    ref={measureNav.getRef(key)}
                    type="button"
                    role="radio"
                    aria-checked={selectedMeasure === key}
                    tabIndex={selectedMeasure === key ? 0 : -1}
                    className={`analysis-tab ${selectedMeasure === key ? "active" : ""}`}
                    onClick={() => setSelectedMeasure(key)}
                    onKeyDown={measureNav.keyDownHandler(setSelectedMeasure)}
                  >
                    {measures[key].label}
                  </button>
                ))}
              </div>
            </div>
            {!isRevenue && (
              <div className="shift-sweep-control-group">
                <div className="shift-sweep-label">Income concept</div>
                <div
                  className="analysis-tabs shift-sweep-tabs"
                  role="radiogroup"
                  aria-label="Income concept"
                >
                  {CONCEPT_OPTIONS.map((key) => (
                    <button
                      key={key}
                      ref={conceptNav.getRef(key)}
                      type="button"
                      role="radio"
                      aria-checked={selectedConcept === key}
                      tabIndex={selectedConcept === key ? 0 : -1}
                      className={`analysis-tab ${selectedConcept === key ? "active" : ""}`}
                      onClick={() => setSelectedConcept(key)}
                      onKeyDown={conceptNav.keyDownHandler(setSelectedConcept)}
                    >
                      {CONCEPTS[key].label}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {isRevenue && stateOptions.length > 0 && (
              <div className="shift-sweep-control-group">
                <label
                  htmlFor="jurisdiction-select"
                  className="shift-sweep-label"
                >
                  Jurisdiction
                </label>
                <select
                  id="jurisdiction-select"
                  className="shift-sweep-select"
                  value={selectedJurisdiction}
                  onChange={(event) =>
                    setSelectedJurisdiction(event.target.value)
                  }
                >
                  <option value="federal">Federal</option>
                  {stateOptions.map((code) => (
                    <option key={code} value={code}>
                      {code}
                    </option>
                  ))}
                </select>
              </div>
            )}
            {isRevenue && hasBaselineTotals && (
              <div className="shift-sweep-control-group">
                <div className="shift-sweep-label">Units</div>
                <div
                  className="analysis-tabs shift-sweep-tabs"
                  role="radiogroup"
                  aria-label="Units"
                >
                  {UNIT_OPTIONS.map((option) => (
                    <button
                      key={option.key}
                      type="button"
                      role="radio"
                      aria-checked={selectedUnit === option.key}
                      className={`analysis-tab ${selectedUnit === option.key ? "active" : ""}`}
                      onClick={() => setSelectedUnit(option.key)}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
          <p className="shift-sweep-description">{config.description}</p>
        </div>

        {isRevenue ? (
          <RevenueDecompositionChart
            chartData={jurisdictionData}
            currencySymbol={currencySymbol}
            buckets={
              selectedJurisdiction === "federal"
                ? FEDERAL_BUCKETS
                : STATE_BUCKETS
            }
            title={
              selectedJurisdiction === "federal"
                ? "Federal revenue decomposition"
                : `${selectedJurisdiction} state revenue decomposition`
            }
            axisLabel={config.axisLabel}
            unit={selectedUnit}
            denominatorB={decompositionDenominatorB}
          />
        ) : (
          <>
        <h3 className="analysis-chart-title">{config.label} by shift level</h3>
        <ResponsiveContainer width="100%" height={400}>
          <LineChart
            data={chartData}
            margin={{ left: 20, right: 30, top: 10, bottom: 35 }}
          >
            <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
            <XAxis
              type="number"
              dataKey="shift"
              domain={[shiftTicks[0], shiftTicks[shiftTicks.length - 1]]}
              ticks={shiftTicks}
              tickFormatter={(value) => `${value}%`}
              tick={{ fontSize: 12 }}
              label={{
                value: `Share of ${laborTerm} income shifted to capital`,
                position: "bottom",
                offset: 0,
                style: { fontSize: 13 },
              }}
            />
            <YAxis
              ticks={yTicks}
              domain={[yTicks[0], yTicks[yTicks.length - 1]]}
              tickFormatter={isRevenue ? revenueFormatter : axisPctFmt}
              tick={{ fontSize: 12 }}
              label={{
                value: config.axisLabel,
                angle: -90,
                position: "insideLeft",
                offset: -10,
                style: { fontSize: 13 },
              }}
            />
            {isRevenue && (
              <ReferenceLine y={0} stroke="#718096" strokeDasharray="4 4" />
            )}
            <Tooltip
              contentStyle={TOOLTIP_STYLE}
              formatter={(value) => [
                config.tooltipFormatter(value),
                config.label,
              ]}
              labelFormatter={(value) =>
                chartData.find((row) => row.shift === value)?.label ??
                `${value}% shift`
              }
            />
            <Line
              type="monotone"
              dataKey={config.dataKey}
              name={config.label}
              stroke={config.color}
              strokeWidth={3}
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
          </>
        )}

        {isRevenue && selectedJurisdiction === "federal" && (
          <RevenueDecompositionChart
            chartData={chartData}
            currencySymbol={currencySymbol}
            buckets={FED_INCOME_TAX_BUCKETS}
            title="Federal income tax decomposition"
            axisLabel={`Change vs baseline (${currencySymbol}B)`}
            showTotalLine={false}
            unit={selectedUnit}
            denominatorB={
              selectedUnit === "share"
                ? federalBaseDenominator(baselineTotals) / 1e9
                : null
            }
          />
        )}

        {isRevenue &&
          selectedJurisdiction === "federal" &&
          sweepData.scenarios.some(
            (s) => (s.federal_mtrs ?? []).length > 0,
          ) && (
            <FederalMtrChart
              sweepData={sweepData}
              metric="fed_income_plus_payroll_tax_mtr"
            />
          )}

        {isRevenue && (
          <DecileImpactChart sweepData={sweepData} unit={selectedUnit} />
        )}

        {isRevenue && hasStateDeltas && (
          <StateExposureChart
            sweepData={sweepData}
            currencySymbol={currencySymbol}
            unit={selectedUnit}
          />
        )}

        <div className="analysis-callout">
          <IconInfoCircle size={20} stroke={1.5} />
          <div>
            {summaryForMetric(
              selectedMeasure,
              selectedConcept,
              config,
              chartData,
              metadata,
            )}
          </div>
        </div>

        <p className="analysis-metadata">
          {modelLabel}, {metadata.year ?? sweepData.year} baseline.{" "}
          <a
            className="shift-sweep-link"
            href={docsUrl}
            target="_blank"
            rel="noreferrer"
          >
            Learn more about the model
          </a>
          .
        </p>
      </div>
    </div>
  );
}

export default ShiftSweep;
