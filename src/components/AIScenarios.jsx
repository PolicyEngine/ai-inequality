import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { IconInfoCircle, IconTimeline } from "@tabler/icons-react";
import defaultScenariosData from "../data/aiScenariosData.json";
import { TOOLTIP_STYLE } from "../utils/chartStyles";
import { useRovingRadioGroup } from "../utils/useRovingRadioGroup";

const SCENARIO_NAMES = ["Slow", "Moderate", "Rapid"];

// Survey inputs behind each scenario: annualised real GDP growth under AI and
// the 2030 labor share of factor income. Karger et al. (2026) via The Budget
// Lab, Table 1. Descriptive context only; every computed number on this page
// comes from the payload.
const SCENARIO_INPUTS = {
  Slow: { annualGrowth: "2.0%", laborShare2030: "55.0%" },
  Moderate: { annualGrowth: "2.6%", laborShare2030: "53.8%" },
  Rapid: { annualGrowth: "3.3%", laborShare2030: "51.3%" },
};

const VARIANTS = [
  { key: "compressive", label: "Wages compress" },
  { key: "proportional", label: "Proportional" },
  { key: "expansive", label: "Wages spread" },
];
const VARIANT_KEYS = VARIANTS.map((v) => v.key);

// Palette reuses values already in the repo: pe-blue-dark for the
// shares-fixed counterfactual, pe-teal-600 for the forecast tilt, semantic
// success/error only where a sign is genuinely good or bad for households.
const COLOR_FIXED = "#17354F";
const COLOR_FORECAST = "#227773";
const COLOR_GRID = "#e2e8f0";
const COLOR_ZERO = "#718096";
const COLOR_GOOD = "#22c55e";
const COLOR_BAD = "#ef4444";

const fmtBillions = (value) =>
  `${value >= 0 ? "+" : "−"}$${Math.abs(value).toFixed(0)}B`;
const fmtPp = (value) =>
  `${value >= 0 ? "+" : "−"}${Math.abs(value).toFixed(2)}pp`;
const fmtPct1 = (value) => `${(value * 100).toFixed(1)}%`;

function findRow(scenarios, name, variant) {
  return scenarios.find(
    (row) =>
      row.name === name && row.inequality === variant && !row.holdSharesFixed,
  );
}

function findSharesFixed(scenarios, name) {
  return scenarios.find((row) => row.name === name && row.holdSharesFixed);
}

/** Linear interpolation of the realization rate at which revenue crosses 0. */
export function realizationBreakeven(rows) {
  const sorted = [...(rows ?? [])].sort(
    (a, b) => (a.realizationRate ?? 0) - (b.realizationRate ?? 0),
  );
  for (let i = 1; i < sorted.length; i += 1) {
    const prev = sorted[i - 1];
    const next = sorted[i];
    const a = prev.revenueChange;
    const b = next.revenueChange;
    if (a == null || b == null || a === b) continue;
    if (a <= 0 && b >= 0) {
      const t = -a / (b - a);
      return (
        prev.realizationRate + t * (next.realizationRate - prev.realizationRate)
      );
    }
  }
  return null;
}

function StatTile({ label, value, delta, valueColor }) {
  return (
    <div className="ai-scenarios-stat">
      <div className="ai-scenarios-stat-label">{label}</div>
      <div
        className="ai-scenarios-stat-value"
        style={valueColor ? { color: valueColor } : undefined}
      >
        {value}
      </div>
      {delta != null && <div className="ai-scenarios-stat-delta">{delta}</div>}
    </div>
  );
}

function TiltCostChart({ scenarios }) {
  const data = SCENARIO_NAMES.map((name) => ({
    name,
    fixed: findSharesFixed(scenarios, name)?.revenueChange ?? null,
    forecast: findRow(scenarios, name, "proportional")?.revenueChange ?? null,
  })).filter((row) => row.fixed != null && row.forecast != null);
  if (data.length === 0) return null;

  return (
    <>
      <h3 className="analysis-chart-title">
        Revenue gain, with and without the tilt toward capital
      </h3>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={data} margin={{ left: 20, right: 30, top: 10 }}>
          <CartesianGrid stroke={COLOR_GRID} strokeDasharray="3 3" />
          <XAxis dataKey="name" tick={{ fontSize: 12 }} />
          <YAxis
            tickFormatter={(v) => `$${v}B`}
            tick={{ fontSize: 12 }}
            label={{
              value: "Revenue change ($B)",
              angle: -90,
              position: "insideLeft",
              offset: -8,
              style: { fontSize: 13 },
            }}
          />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            formatter={(value, seriesName) => [fmtBillions(value), seriesName]}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar
            dataKey="fixed"
            name="Shares held at today's split"
            fill={COLOR_FIXED}
            isAnimationActive={false}
          />
          <Bar
            dataKey="forecast"
            name="Tilted to capital, as forecast"
            fill={COLOR_FORECAST}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </>
  );
}

function VariantPairCharts({ scenarios, scenarioName }) {
  const rows = VARIANTS.map((variant) => {
    const row = findRow(scenarios, scenarioName, variant.key);
    if (!row) return null;
    return {
      variant: variant.label,
      revenue: row.revenueChange,
      povertyPp: (row.povertyRateChange ?? 0) * 100,
    };
  }).filter(Boolean);
  if (rows.length === 0) return null;

  return (
    <div className="analysis-charts-grid ai-scenarios-pair">
      <div>
        <h3 className="analysis-chart-title">Revenue stays positive…</h3>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={rows} margin={{ left: 12, right: 12, top: 10 }}>
            <CartesianGrid stroke={COLOR_GRID} strokeDasharray="3 3" />
            <XAxis dataKey="variant" tick={{ fontSize: 11 }} />
            <YAxis tickFormatter={(v) => `$${v}B`} tick={{ fontSize: 12 }} />
            <Tooltip
              contentStyle={TOOLTIP_STYLE}
              formatter={(value) => [fmtBillions(value), "Revenue change"]}
            />
            <Bar
              dataKey="revenue"
              fill={COLOR_FORECAST}
              isAnimationActive={false}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div>
        <h3 className="analysis-chart-title">…while poverty flips sign</h3>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={rows} margin={{ left: 12, right: 12, top: 10 }}>
            <CartesianGrid stroke={COLOR_GRID} strokeDasharray="3 3" />
            <XAxis dataKey="variant" tick={{ fontSize: 11 }} />
            <YAxis
              tickFormatter={(v) => `${v >= 0 ? "+" : ""}${v.toFixed(1)}pp`}
              tick={{ fontSize: 12 }}
            />
            <ReferenceLine y={0} stroke={COLOR_ZERO} strokeDasharray="4 4" />
            <Tooltip
              contentStyle={TOOLTIP_STYLE}
              formatter={(value) => [fmtPp(value), "Poverty change"]}
            />
            <Bar dataKey="povertyPp" isAnimationActive={false}>
              {rows.map((row) => (
                <Cell
                  key={row.variant}
                  fill={row.povertyPp > 0 ? COLOR_BAD : COLOR_GOOD}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function RealizationChart({ rows, breakeven }) {
  const data = [...(rows ?? [])]
    .sort((a, b) => (a.realizationRate ?? 0) - (b.realizationRate ?? 0))
    .map((row) => ({
      rate: (row.realizationRate ?? 0) * 100,
      revenue: row.revenueChange,
    }));
  if (data.length === 0) return null;

  return (
    <>
      <h3 className="analysis-chart-title">
        Rapid-scenario revenue vs the share of new capital income that is
        realized
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart
          data={data}
          margin={{ left: 20, right: 30, top: 10, bottom: 30 }}
        >
          <CartesianGrid stroke={COLOR_GRID} strokeDasharray="3 3" />
          <XAxis
            type="number"
            dataKey="rate"
            domain={[0, 100]}
            ticks={[0, 25, 50, 75, 100]}
            tickFormatter={(v) => `${v}%`}
            tick={{ fontSize: 12 }}
            label={{
              value: "Share of the AI capital flow reaching tax returns",
              position: "bottom",
              offset: 10,
              style: { fontSize: 13 },
            }}
          />
          <YAxis
            tickFormatter={(v) => `$${v}B`}
            tick={{ fontSize: 12 }}
            label={{
              value: "Revenue change ($B)",
              angle: -90,
              position: "insideLeft",
              offset: -8,
              style: { fontSize: 13 },
            }}
          />
          <ReferenceLine y={0} stroke={COLOR_ZERO} strokeDasharray="4 4" />
          {breakeven != null && (
            <ReferenceLine
              x={breakeven * 100}
              stroke={COLOR_BAD}
              strokeDasharray="4 4"
              label={{
                value: `Breakeven ≈ ${(breakeven * 100).toFixed(0)}%`,
                position: "insideTopLeft",
                fontSize: 12,
                fill: COLOR_BAD,
              }}
            />
          )}
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            formatter={(value) => [fmtBillions(value), "Revenue change"]}
            labelFormatter={(value) => `${value}% realized`}
          />
          <Line
            type="monotone"
            dataKey="revenue"
            stroke={COLOR_FORECAST}
            strokeWidth={3}
            dot={{ r: 4 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </>
  );
}

function CapitalScopeTable({ scenarios, scopeRows }) {
  const rows = (scopeRows ?? [])
    .map((row) => {
      const full = findRow(scenarios, row.name, "proportional");
      if (!full) return null;
      return {
        name: row.name,
        full: full.revenueChange,
        excl: row.revenueChange,
      };
    })
    .filter(Boolean);
  if (rows.length === 0) return null;

  return (
    <div className="ai-scenarios-scope">
      <h3 className="analysis-chart-title">
        What counts as capital: revenue with and without retirement
        distributions
      </h3>
      <table className="ai-scenarios-scope-table">
        <thead>
          <tr>
            <th scope="col">Scenario</th>
            <th scope="col">Full capital set</th>
            <th scope="col">Excl. pensions and IRAs</th>
            <th scope="col">Difference</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.name}>
              <th scope="row">{row.name}</th>
              <td>{fmtBillions(row.full)}</td>
              <td>{fmtBillions(row.excl)}</td>
              <td>{fmtBillions(row.excl - row.full)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="shift-sweep-description">
        Taxable pension and IRA distributions are taxed at ordinary rates, so
        counting them as capital raises the measured revenue gain. Excluding
        them halves the Rapid estimate and turns Slow negative.
      </p>
    </div>
  );
}

function AIScenarios({ scenariosData = defaultScenariosData }) {
  const [scenarioName, setScenarioName] = useState("Rapid");
  const [variantKey, setVariantKey] = useState("proportional");
  const scenarioNav = useRovingRadioGroup(SCENARIO_NAMES, scenarioName);
  const variantNav = useRovingRadioGroup(VARIANT_KEYS, variantKey);

  const scenarios = scenariosData?.scenarios ?? [];
  const baseline = scenariosData?.baseline ?? {};
  const metadata = scenariosData?.metadata ?? {};
  const realizationRows = scenariosData?.sensitivities?.realization ?? [];
  const scopeRows =
    scenariosData?.sensitivities?.capital_scope_excluding_retirement ?? [];

  const selected = findRow(scenarios, scenarioName, variantKey);
  const breakeven = useMemo(
    () => realizationBreakeven(realizationRows),
    [realizationRows],
  );

  if (scenarios.length === 0 || !selected) return null;

  const inputs = SCENARIO_INPUTS[scenarioName] ?? {};
  const povertyPp = (selected.povertyRateChange ?? 0) * 100;
  const crossover = selected.laborCrossoverIncome;

  // Share of the shares-fixed revenue gain the forecast tilt keeps, on the
  // all-government basis these cards use. The matched-federal figure the
  // reconciliation reports is different, so the copy names both bases.
  const rapidFixed = findSharesFixed(scenarios, "Rapid")?.revenueChange;
  const rapidForecast = findRow(scenarios, "Rapid", "proportional")?.revenueChange;
  const tiltKeptPct =
    rapidFixed && rapidForecast
      ? Math.round((100 * rapidForecast) / rapidFixed)
      : null;

  return (
    <div id="ai-scenarios" className="analysis-section">
      <div className="analysis-header">
        <div className="analysis-icon-wrapper">
          <IconTimeline size={28} stroke={1.5} />
        </div>
        <h2>What forecasters expect, under current law</h2>
        <p className="analysis-subtitle">
          Three AI futures from the Karger et al. (2026) forecaster survey, as
          calibrated by Yale&apos;s Budget Lab, run through PolicyEngine&apos;s
          full tax and benefit model for {scenariosData.year}.
        </p>
      </div>

      <div className="analysis-card">
        <div className="analysis-controls">
          <div className="shift-sweep-controls">
            <div className="shift-sweep-control-group">
              <div className="shift-sweep-label">AI adoption</div>
              <div
                className="analysis-tabs shift-sweep-tabs"
                role="radiogroup"
                aria-label="AI adoption scenario"
              >
                {SCENARIO_NAMES.map((name) => (
                  <button
                    key={name}
                    ref={scenarioNav.getRef(name)}
                    type="button"
                    role="radio"
                    aria-checked={scenarioName === name}
                    tabIndex={scenarioName === name ? 0 : -1}
                    className={`analysis-tab ${scenarioName === name ? "active" : ""}`}
                    onClick={() => setScenarioName(name)}
                    onKeyDown={scenarioNav.keyDownHandler(setScenarioName)}
                  >
                    {name}
                  </button>
                ))}
              </div>
            </div>
            <div className="shift-sweep-control-group">
              <div className="shift-sweep-label">Wage inequality</div>
              <div
                className="analysis-tabs shift-sweep-tabs"
                role="radiogroup"
                aria-label="Wage inequality variant"
              >
                {VARIANTS.map((variant) => (
                  <button
                    key={variant.key}
                    ref={variantNav.getRef(variant.key)}
                    type="button"
                    role="radio"
                    aria-checked={variantKey === variant.key}
                    tabIndex={variantKey === variant.key ? 0 : -1}
                    className={`analysis-tab ${variantKey === variant.key ? "active" : ""}`}
                    onClick={() => setVariantKey(variant.key)}
                    onKeyDown={variantNav.keyDownHandler(setVariantKey)}
                  >
                    {variant.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <p className="shift-sweep-description">
            {scenarioName} adoption assumes {inputs.annualGrowth} annual real
            GDP growth with the labor share falling to {inputs.laborShare2030}{" "}
            by 2030 (survey inputs). Against the CBO baseline, that means
            capital income {fmtPct1(selected.capitalGrowth)} higher and labor
            income {fmtPct1(Math.abs(selected.laborGrowth))}{" "}
            {selected.laborGrowth >= 0 ? "higher" : "lower"}.
          </p>
        </div>

        <div className="ai-scenarios-stats">
          <StatTile
            label="Net government revenue"
            value={fmtBillions(selected.revenueChange)}
            delta="federal + state, net of transfers"
          />
          <StatTile
            label="SPM poverty"
            value={fmtPp(povertyPp)}
            delta={`${fmtPct1(baseline.povertyRate)} at baseline`}
            valueColor={povertyPp > 0 ? COLOR_BAD : COLOR_GOOD}
          />
          <StatTile
            label="Payroll receipts"
            value={fmtBillions(selected.payrollChange)}
            delta="Social Security cap effect"
          />
          <StatTile
            label="Net income Gini"
            value={`${selected.netGiniChange >= 0 ? "+" : "−"}${Math.abs(
              selected.netGiniChange ?? 0,
            ).toFixed(4)}`}
            delta={`${(baseline.netGini ?? 0).toFixed(4)} at baseline`}
          />
        </div>

        <p className="ai-scenarios-stat-note">
          Net government revenue is federal <em>and</em> state taxes minus
          transfers: refundable credits (EITC, refundable CTC) and benefit
          outlays (SNAP, SSI, TANF, WIC, state-funded benefits) are netted out,
          so a scenario that raises taxes and benefit spending together shows
          the difference. Under {scenarioName} / proportional, state income tax
          is {fmtBillions(selected.stateTaxChange)} of it.
        </p>

        {crossover != null && (
          <p className="ai-scenarios-crossover">
            Under this variant, workers earning below{" "}
            <strong>${Math.round(crossover).toLocaleString("en-US")}</strong>{" "}
            {variantKey === "expansive" ? "lose" : "gain"} wage income relative
            to the proportional case.
          </p>
        )}

        <TiltCostChart scenarios={scenarios} />
        <p className="shift-sweep-description">
          The blue bars grow both factors at the scenario&apos;s GDP rate; the
          teal bars tilt the same growth toward capital as forecasters expect.
          {tiltKeptPct != null && (
            <>
              {" "}
              Under Rapid the tilt keeps {tiltKeptPct}% of the revenue gain on
              this all-government basis, and 50% on the narrower federal basis
              comparable to the Budget Lab&apos;s, which adds their
              corporate-tax estimate. Most of the difference is that
              corporate term: it grows with capital income, so it cushions the
              as-forecast case. State taxes and transfers add to the
              tilt&apos;s dollar cost but barely move the share kept.
            </>
          )}
        </p>

        <VariantPairCharts scenarios={scenarios} scenarioName={scenarioName} />
        <p className="shift-sweep-description">
          Whether AI compresses or spreads the wage distribution is the
          assumption forecasters flag as least evidenced. Revenue stays
          positive across the whole range; the poverty outcome flips sign.
        </p>

        <RealizationChart rows={realizationRows} breakeven={breakeven} />
        <p className="shift-sweep-description">
          The Budget Lab assumes the realized share of capital income is
          unchanged by AI (the 100% point). If less of the new capital income
          reaches tax returns — accruing instead as unrealized gains or inside
          retirement accounts — the revenue gain shrinks linearly and turns
          negative below the breakeven.
        </p>

        <CapitalScopeTable scenarios={scenarios} scopeRows={scopeRows} />

        <div className="analysis-callout">
          <IconInfoCircle size={20} stroke={1.75} />
          <span>
            {metadata.corporateTaxScopeNote ??
              "PolicyEngine-US models the household sector; totals exclude corporate income tax."}
          </span>
        </div>

        <p className="analysis-metadata">
          {metadata.countryModelPackage} {metadata.countryModelVersion} ·{" "}
          {metadata.dataPackage} {metadata.dataVersion} · {metadata.datasetName}{" "}
          · <Link to="/budget-lab">read the full write-up</Link>
        </p>
      </div>
    </div>
  );
}

export default AIScenarios;
