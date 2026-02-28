import React, { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { IconArrowsExchange, IconInfoCircle } from "@tabler/icons-react";
import shiftData from "../data/laborShiftData.json";
import "./LaborShift.css";

const TABS = [
  { key: "overview", label: "Overview" },
  { key: "deciles", label: "Decile shares" },
];

const TOOLTIP_STYLE = {
  background: "#fff",
  border: "1px solid #e2e8f0",
  borderRadius: 6,
  padding: "8px 12px",
  fontSize: 13,
};

const pct = (v) => `${(v * 100).toFixed(1)}%`;

const COLORS = {
  baseline: "#319795",
  shift10: "#805AD5",
  shift25: "#D69E2E",
  shift50: "#e53e3e",
  ubi: "#38a169",
};

function LaborShift() {
  const [activeTab, setActiveTab] = useState("overview");

  const giniData = shiftData.scenarios.map((s) => ({
    scenario: s.label,
    "Market Gini": s.marketGini,
    "Net Gini": s.netGini,
  }));

  const povertyData = shiftData.scenarios.map((s) => ({
    scenario: s.label,
    "SPM poverty rate": s.povertyRate,
  }));

  const decileData = shiftData.deciles.labels.map((label, i) => ({
    decile: label,
    Baseline: shiftData.deciles.baseline[i],
    "50% shift": shiftData.deciles["50pctShift"][i],
    "50% + UBI": shiftData.deciles["50pctUBI"][i],
  }));

  return (
    <div id="labor-shift" className="shift-section">
      <div className="shift-header">
        <div className="shift-icon-wrapper">
          <IconArrowsExchange size={28} stroke={1.5} />
        </div>
        <h2>Labor-to-capital shift</h2>
        <p className="shift-subtitle">
          What happens when AI automation shifts wages to capital income at
          constant GDP
        </p>
      </div>

      <div className="shift-card">
        <div className="shift-controls">
          <div className="shift-tabs">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                className={`shift-tab ${activeTab === tab.key ? "active" : ""}`}
                onClick={() => setActiveTab(tab.key)}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {activeTab === "overview" && (
          <div className="shift-charts-grid">
            <div>
              <h3 className="shift-chart-title">Gini coefficients</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart
                  data={giniData}
                  margin={{ left: 10, right: 10, top: 5, bottom: 5 }}
                >
                  <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
                  <XAxis
                    dataKey="scenario"
                    tick={{ fontSize: 11 }}
                    interval={0}
                    angle={-20}
                    textAnchor="end"
                    height={50}
                  />
                  <YAxis
                    domain={[0.45, 0.8]}
                    tick={{ fontSize: 12 }}
                    tickFormatter={(v) => v.toFixed(2)}
                  />
                  <Tooltip
                    contentStyle={TOOLTIP_STYLE}
                    formatter={(v, name) => [v.toFixed(4), name]}
                  />
                  <Legend />
                  <Bar dataKey="Market Gini" fill="#e53e3e" />
                  <Bar dataKey="Net Gini" fill="#319795" />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div>
              <h3 className="shift-chart-title">SPM poverty rate</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart
                  data={povertyData}
                  margin={{ left: 10, right: 10, top: 5, bottom: 5 }}
                >
                  <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
                  <XAxis
                    dataKey="scenario"
                    tick={{ fontSize: 11 }}
                    interval={0}
                    angle={-20}
                    textAnchor="end"
                    height={50}
                  />
                  <YAxis
                    domain={[0, 0.4]}
                    tick={{ fontSize: 12 }}
                    tickFormatter={pct}
                  />
                  <Tooltip
                    contentStyle={TOOLTIP_STYLE}
                    formatter={(v) => [pct(v), "Poverty rate"]}
                  />
                  <Bar dataKey="SPM poverty rate" fill="#e53e3e" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {activeTab === "deciles" && (
          <ResponsiveContainer width="100%" height={400}>
            <BarChart
              data={decileData}
              margin={{ left: 20, right: 30, top: 10, bottom: 35 }}
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
              <Bar dataKey="Baseline" fill={COLORS.baseline} />
              <Bar dataKey="50% shift" fill={COLORS.shift50} />
              <Bar dataKey="50% + UBI" fill={COLORS.ubi} />
            </BarChart>
          </ResponsiveContainer>
        )}

        <div className="shift-callout">
          <IconInfoCircle size={20} stroke={1.5} />
          <div>
            <strong>Key finding</strong>: A 50% labor-to-capital shift raises
            poverty from 20.5% to 36.0%. The additional tax revenue funds
            ~$1,423/person/year in UBI, which reduces poverty to 29.6% —
            a partial offset of 6 percentage points out of the 15pp increase.
          </div>
        </div>

        <p className="shift-metadata">
          {shiftData.metadata.description} ({shiftData.metadata.year})
        </p>
      </div>
    </div>
  );
}

export default LaborShift;
