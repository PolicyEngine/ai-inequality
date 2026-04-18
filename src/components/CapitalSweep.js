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
import { IconTrendingUp, IconInfoCircle } from "@tabler/icons-react";
import sweepData from "../data/capitalSweepData.json";
import { TOOLTIP_STYLE, pct, dollars } from "../utils/chartStyles";
import { niceTicks } from "../utils/chartTicks";
import "./AnalysisSection.css";

const TABS = [
  { key: "gini", label: "Inequality" },
  { key: "revenue", label: "Tax revenue" },
  { key: "deciles", label: "Decile shares" },
];

function CapitalSweep() {
  const [activeTab, setActiveTab] = useState("gini");
  const baseline = sweepData.sweep[0];
  const fiveX = sweepData.sweep.find((row) => row.multiplier === 5.0);
  const extraRevenue = fiveX ? fiveX.totalRevenue - baseline.totalRevenue : 0;
  const multiplierTicks = niceTicks(
    sweepData.sweep[0].multiplier,
    sweepData.sweep[sweepData.sweep.length - 1].multiplier,
    9,
  );
  const giniTicks = niceTicks(
    Math.min(
      ...sweepData.sweep.map((row) => Math.min(row.marketGini, row.netGini)),
    ),
    Math.max(
      ...sweepData.sweep.map((row) => Math.max(row.marketGini, row.netGini)),
    ),
    6,
  );
  const revenueTicks = niceTicks(
    Math.min(
      ...sweepData.sweep.map((row) =>
        Math.min(row.fedRevenue, row.stateRevenue, row.totalRevenue),
      ),
    ),
    Math.max(
      ...sweepData.sweep.map((row) =>
        Math.max(row.fedRevenue, row.stateRevenue, row.totalRevenue),
      ),
    ),
    6,
  );

  const decileData = sweepData.deciles.labels.map((label, i) => ({
    decile: label,
    Baseline: sweepData.deciles.baseline[i],
    "2x": sweepData.deciles["2x"][i],
    "5x": sweepData.deciles["5x"][i],
  }));

  return (
    <div id="capital-sweep" className="analysis-section">
      <div className="analysis-header">
        <div className="analysis-icon-wrapper">
          <IconTrendingUp size={28} stroke={1.5} />
        </div>
        <h2>Capital income sweep</h2>
        <p className="analysis-subtitle">
          How rising capital income (1x to 5x) affects inequality and tax
          revenue across the full US population
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

        {activeTab === "gini" && (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart
              data={sweepData.sweep}
              margin={{ left: 20, right: 30, top: 10, bottom: 35 }}
            >
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
              <XAxis
                dataKey="multiplier"
                type="number"
                domain={[
                  multiplierTicks[0],
                  multiplierTicks[multiplierTicks.length - 1],
                ]}
                ticks={multiplierTicks}
                tickFormatter={(v) => `${v}x`}
                tick={{ fontSize: 12 }}
                label={{
                  value: "Capital income multiplier",
                  position: "bottom",
                  offset: 0,
                  style: { fontSize: 13 },
                }}
              />
              <YAxis
                ticks={giniTicks}
                domain={[giniTicks[0], giniTicks[giniTicks.length - 1]]}
                tick={{ fontSize: 12 }}
                tickFormatter={(v) => v.toFixed(2)}
                label={{
                  value: "Gini coefficient",
                  angle: -90,
                  position: "insideLeft",
                  offset: -5,
                  style: { fontSize: 13 },
                }}
              />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                formatter={(value, name) => [value.toFixed(4), name]}
                labelFormatter={(v) => `${v}x capital income`}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="marketGini"
                name="Market Gini"
                stroke="#e53e3e"
                strokeWidth={2}
                dot={{ r: 4 }}
              />
              <Line
                type="monotone"
                dataKey="netGini"
                name="Net Gini"
                stroke="#319795"
                strokeWidth={3}
                dot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}

        {activeTab === "revenue" && (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart
              data={sweepData.sweep}
              margin={{ left: 20, right: 30, top: 10, bottom: 35 }}
            >
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
              <XAxis
                dataKey="multiplier"
                type="number"
                domain={[
                  multiplierTicks[0],
                  multiplierTicks[multiplierTicks.length - 1],
                ]}
                ticks={multiplierTicks}
                tickFormatter={(v) => `${v}x`}
                tick={{ fontSize: 12 }}
                label={{
                  value: "Capital income multiplier",
                  position: "bottom",
                  offset: 0,
                  style: { fontSize: 13 },
                }}
              />
              <YAxis
                ticks={revenueTicks}
                domain={[
                  revenueTicks[0],
                  revenueTicks[revenueTicks.length - 1],
                ]}
                tick={{ fontSize: 12 }}
                tickFormatter={(v) => `$${v.toLocaleString()}B`}
                label={{
                  value: "Annual revenue ($B)",
                  angle: -90,
                  position: "insideLeft",
                  offset: -10,
                  style: { fontSize: 13 },
                }}
              />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                formatter={(value, name) => [dollars(value), name]}
                labelFormatter={(v) => `${v}x capital income`}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="fedRevenue"
                name="Federal revenue"
                stroke="#2C6496"
                strokeWidth={2}
                dot={{ r: 4 }}
              />
              <Line
                type="monotone"
                dataKey="stateRevenue"
                name="State revenue"
                stroke="#38a169"
                strokeWidth={2}
                dot={{ r: 4 }}
              />
              <Line
                type="monotone"
                dataKey="totalRevenue"
                name="Total revenue"
                stroke="#319795"
                strokeWidth={3}
                dot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}

        {activeTab === "deciles" && (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart
              data={decileData}
              margin={{ left: 20, right: 30, top: 10, bottom: 5 }}
            >
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
              <XAxis dataKey="decile" tick={{ fontSize: 12 }} />
              <YAxis
                tickFormatter={pct}
                tick={{ fontSize: 12 }}
                label={{
                  value: "Share of net income",
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
                stroke="#319795"
                strokeWidth={3}
                dot={{ r: 4 }}
              />
              <Line
                type="monotone"
                dataKey="2x"
                stroke="#805AD5"
                strokeWidth={2.5}
                dot={{ r: 4 }}
              />
              <Line
                type="monotone"
                dataKey="5x"
                stroke="#e53e3e"
                strokeWidth={2.5}
                dot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}

        <div className="analysis-callout">
          <IconInfoCircle size={20} stroke={1.5} />
          <div>
            <strong>Key finding</strong>: At 5x capital income, the top decile
            captures {pct(fiveX?.top10Share)} of net income up from{" "}
            {pct(baseline?.top10Share)} at baseline. The existing tax-benefit
            system offsets some bottom-decile losses but does not prevent
            top-end concentration. The scenario generates{" "}
            {dollars(Math.round(extraRevenue))} in additional annual tax
            revenue.
          </div>
        </div>

        <p className="analysis-metadata">
          {sweepData.metadata.description} ({sweepData.metadata.year})
        </p>
      </div>
    </div>
  );
}

export default CapitalSweep;
