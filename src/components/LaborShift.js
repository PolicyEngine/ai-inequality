import React, { useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { IconArrowsExchange, IconInfoCircle } from "@tabler/icons-react";
import shiftData from "../data/laborShiftData.json";
import sweepData from "../data/shiftSweepData.json";
import { TOOLTIP_STYLE, dollars, fmt, pct } from "../utils/chartStyles";
import { niceTicks } from "../utils/chartTicks";
import "./AnalysisSection.css";

const TABS = [
  { key: "overview", label: "Overview" },
  { key: "deciles", label: "Decile shares" },
];

const COLORS = {
  baseline: "#319795",
  shift10: "#805AD5",
  shift25: "#D69E2E",
  shift50: "#e53e3e",
  ubi: "#38a169",
};

function LaborShift() {
  const [activeTab, setActiveTab] = useState("overview");
  const baseline = shiftData.scenarios[0];
  const shift50 = shiftData.scenarios.find((s) => s.shiftPct === 50);
  const shift50Ubi = shiftData.scenarios.find((s) => s.label.includes("UBI"));
  const hasUbiScenario = Boolean(shift50Ubi && shiftData.deciles["50pctUBI"]);
  const healthDelta =
    baseline && shift50
      ? shift50.healthcareBenefitValue - baseline.healthcareBenefitValue
      : 0;
  const hasHealthSweepGini = sweepData.scenarios.every(
    (scenario) => scenario.net_gini_including_health_benefits != null,
  );
  const overviewNetLabel = hasHealthSweepGini
    ? "Resources incl. health"
    : "Net Gini";

  const giniData = sweepData.scenarios.map((s) => ({
    shiftPct: s.shift_pct,
    label: s.label,
    "Market Gini": s.market_gini,
    [overviewNetLabel]: s.net_gini_including_health_benefits ?? s.net_gini,
  }));
  const overviewShiftTicks = niceTicks(
    giniData[0].shiftPct,
    giniData[giniData.length - 1].shiftPct,
    11,
  );
  const overviewGiniTicks = niceTicks(
    Math.min(
      ...giniData.map((row) =>
        Math.min(row["Market Gini"], row[overviewNetLabel]),
      ),
    ),
    Math.max(
      ...giniData.map((row) =>
        Math.max(row["Market Gini"], row[overviewNetLabel]),
      ),
    ),
    6,
  );

  const decileData = shiftData.deciles.labels.map((label, i) => {
    const row = {
      decile: label,
      Baseline: shiftData.deciles.baseline[i],
      "50% shift": shiftData.deciles["50pctShift"][i],
    };
    if (hasUbiScenario) {
      row["50% shift + UBI"] = shiftData.deciles["50pctUBI"][i];
    }
    return row;
  });

  return (
    <div id="labor-shift" className="analysis-section">
      <div className="analysis-header">
        <div className="analysis-icon-wrapper">
          <IconArrowsExchange size={28} stroke={1.5} />
        </div>
        <h2>Labor-to-capital shift</h2>
        <p className="analysis-subtitle">
          What happens when AI automation shifts wages to capital income at
          constant modeled market income, counting Medicaid, CHIP, and ACA
          support in household resources
        </p>
      </div>

      <div className="analysis-card">
        <div className="analysis-controls">
          <div className="analysis-tabs">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                className={`analysis-tab ${activeTab === tab.key ? "active" : ""}`}
                onClick={() => setActiveTab(tab.key)}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {activeTab === "overview" && (
          <div className="analysis-charts-grid">
            <div style={{ gridColumn: "1 / -1" }}>
              <h3 className="analysis-chart-title">
                Gini coefficients by shift level
              </h3>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart
                  data={giniData}
                  margin={{ left: 10, right: 10, top: 5, bottom: 5 }}
                >
                  <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
                  <XAxis
                    type="number"
                    dataKey="shiftPct"
                    domain={[
                      overviewShiftTicks[0],
                      overviewShiftTicks[overviewShiftTicks.length - 1],
                    ]}
                    ticks={overviewShiftTicks}
                    tickFormatter={(v) => `${v}%`}
                    tick={{ fontSize: 11 }}
                    height={40}
                  />
                  <YAxis
                    ticks={overviewGiniTicks}
                    domain={[
                      overviewGiniTicks[0],
                      overviewGiniTicks[overviewGiniTicks.length - 1],
                    ]}
                    tick={{ fontSize: 12 }}
                    tickFormatter={(v) => v.toFixed(2)}
                  />
                  <Tooltip
                    contentStyle={TOOLTIP_STYLE}
                    formatter={(v, name) => [v.toFixed(4), name]}
                    labelFormatter={(value) =>
                      giniData.find((row) => row.shiftPct === value)?.label ??
                      `${value}% shift`
                    }
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="Market Gini"
                    stroke="#e53e3e"
                    strokeWidth={2}
                    dot={{ r: 4 }}
                  />
                  <Line
                    type="monotone"
                    dataKey={overviewNetLabel}
                    stroke="#319795"
                    strokeWidth={3}
                    dot={{ r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {activeTab === "deciles" && (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart
              data={decileData}
              margin={{ left: 20, right: 30, top: 10, bottom: 35 }}
            >
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
              <XAxis dataKey="decile" tick={{ fontSize: 12 }} />
              <YAxis
                tickFormatter={pct}
                tick={{ fontSize: 12 }}
                label={{
                  value: "Share of household resources",
                  angle: -90,
                  position: "insideLeft",
                  offset: -5,
                  style: { fontSize: 13 },
                }}
              />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                formatter={(value, name) => [pct(value), name]}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="Baseline"
                stroke={COLORS.baseline}
                strokeWidth={3}
                dot={{ r: 4 }}
              />
              <Line
                type="monotone"
                dataKey="50% shift"
                stroke={COLORS.shift50}
                strokeWidth={2.5}
                dot={{ r: 4 }}
              />
              {hasUbiScenario && (
                <Line
                  type="monotone"
                  dataKey="50% shift + UBI"
                  stroke={COLORS.ubi}
                  strokeWidth={2.5}
                  dot={{ r: 4 }}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        )}

        <div className="analysis-callout">
          <IconInfoCircle size={20} stroke={1.5} />
          <div>
            <strong>Key finding</strong>: A 50% labor-to-capital shift raises
            the top decile's share of household resources from{" "}
            {pct(baseline?.top10Share)} to {pct(shift50?.top10Share)}. Health
            coverage support changes from{" "}
            {dollars(baseline?.healthcareBenefitValue ?? 0)} to{" "}
            {dollars(shift50?.healthcareBenefitValue ?? 0)} (
            {healthDelta >= 0 ? "+" : ""}
            {dollars(healthDelta)}), with the 50% shift scenario carrying{" "}
            {dollars(shift50?.medicaidBenefits ?? 0)} in Medicaid,{" "}
            {dollars(shift50?.chipBenefits ?? 0)} in CHIP, and{" "}
            {dollars(shift50?.acaBenefits ?? 0)} in ACA premium support.
            {hasUbiScenario ? (
              <>
                {" "}
                The additional fiscal space funds{" "}
                {fmt(shift50Ubi?.ubiPerPerson)} per person per year in UBI.
              </>
            ) : (
              <>
                {" "}
                Once payroll tax losses and transfer changes are counted, this
                scenario does not generate enough fiscal space for a
                budget-neutral UBI.
              </>
            )}
          </div>
        </div>

        <p className="analysis-metadata">
          {shiftData.metadata.description} ({shiftData.metadata.year})
        </p>
      </div>
    </div>
  );
}

export default LaborShift;
