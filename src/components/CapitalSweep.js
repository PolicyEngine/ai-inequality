import React, { useState } from "react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
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
import "./AnalysisSection.css";

const TABS = [
  { key: "gini", label: "Inequality" },
  { key: "revenue", label: "Tax revenue" },
  { key: "deciles", label: "Decile shares" },
];

function CapitalSweep() {
  const [activeTab, setActiveTab] = useState("gini");

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
          How rising capital income (1x to 5x) affects inequality, poverty, and
          tax revenue across the full US population
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
                domain={[1, 5]}
                ticks={[1, 1.5, 2, 2.5, 3, 4, 5]}
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
                domain={[0.48, 0.75]}
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
              <Line
                type="monotone"
                dataKey="povertyRate"
                name="SPM poverty rate"
                stroke="#805AD5"
                strokeWidth={2}
                strokeDasharray="5 5"
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
                domain={[1, 5]}
                ticks={[1, 1.5, 2, 2.5, 3, 4, 5]}
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
            <BarChart
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
              <Bar dataKey="Baseline" fill="#319795" />
              <Bar dataKey="2x" fill="#805AD5" />
              <Bar dataKey="5x" fill="#e53e3e" />
            </BarChart>
          </ResponsiveContainer>
        )}

        <div className="analysis-callout">
          <IconInfoCircle size={20} stroke={1.5} />
          <div>
            <strong>Key finding</strong>: At 5x capital income, the top decile
            captures 52% of net income (up from 38% at baseline) while poverty
            holds steady at ~20.5%. The existing tax-benefit system offsets
            bottom-decile losses but does not reduce top-end concentration.
            The scenario generates $2.9T in additional annual tax revenue.
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
