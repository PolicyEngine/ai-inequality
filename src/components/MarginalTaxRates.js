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
import { IconPercentage, IconInfoCircle } from "@tabler/icons-react";
import mtrData from "../data/mtrData.json";
import "./MarginalTaxRates.css";

const TABS = [
  { key: "bySource", label: "By income source" },
  { key: "byScenario", label: "By scenario" },
];

const TOOLTIP_STYLE = {
  background: "#fff",
  border: "1px solid #e2e8f0",
  borderRadius: 6,
  padding: "8px 12px",
  fontSize: 13,
};

const pct = (v) => `${(v * 100).toFixed(1)}%`;

const SCENARIO_COLORS = {
  Baseline: "#319795",
  "2x capital": "#805AD5",
  "5x capital": "#e53e3e",
  "10% shift": "#D69E2E",
  "50% shift": "#2C6496",
};

const SOURCE_COLORS = {
  Employment: "#319795",
  "Self-emp": "#805AD5",
  LTCG: "#D69E2E",
  STCG: "#e53e3e",
  "Qual div": "#2C6496",
};

const SCENARIOS = ["Baseline", "2x capital", "5x capital", "10% shift", "50% shift"];
const SOURCES = ["Employment", "Self-emp", "LTCG", "STCG", "Qual div"];

function MarginalTaxRates() {
  const [activeTab, setActiveTab] = useState("bySource");

  // By-source view: income source on x-axis, bars for each scenario
  const bySourceData = mtrData.bySource;

  // By-scenario view: scenario on x-axis, bars for each income source
  const byScenarioData = mtrData.scenarios.map((s) => ({
    scenario: s.label,
    Employment: s.employment_income,
    "Self-emp": s.self_employment_income,
    LTCG: s.long_term_capital_gains,
    STCG: s.short_term_capital_gains,
    "Qual div": s.qualified_dividend_income,
  }));

  return (
    <div id="marginal-tax-rates" className="mtr-section">
      <div className="mtr-header">
        <div className="mtr-icon-wrapper">
          <IconPercentage size={28} stroke={1.5} />
        </div>
        <h2>Marginal tax rates</h2>
        <p className="mtr-subtitle">
          Average effective marginal tax rates by income source across
          AI-driven economic scenarios
        </p>
      </div>

      <div className="mtr-card">
        <div className="mtr-controls">
          <div className="mtr-tabs">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                className={`mtr-tab ${activeTab === tab.key ? "active" : ""}`}
                onClick={() => setActiveTab(tab.key)}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {activeTab === "bySource" && (
          <ResponsiveContainer width="100%" height={400}>
            <BarChart
              data={bySourceData}
              margin={{ left: 20, right: 10, top: 10, bottom: 35 }}
            >
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
              <XAxis dataKey="source" tick={{ fontSize: 12 }} />
              <YAxis
                tickFormatter={pct}
                tick={{ fontSize: 12 }}
                domain={[0, 0.3]}
                label={{
                  value: "Average effective MTR",
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
              {SCENARIOS.map((s) => (
                <Bar key={s} dataKey={s} fill={SCENARIO_COLORS[s]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        )}

        {activeTab === "byScenario" && (
          <ResponsiveContainer width="100%" height={400}>
            <BarChart
              data={byScenarioData}
              margin={{ left: 20, right: 10, top: 10, bottom: 35 }}
            >
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
              <XAxis
                dataKey="scenario"
                tick={{ fontSize: 11 }}
                interval={0}
                angle={-15}
                textAnchor="end"
                height={50}
              />
              <YAxis
                tickFormatter={pct}
                tick={{ fontSize: 12 }}
                domain={[0, 0.3]}
                label={{
                  value: "Average effective MTR",
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
              {SOURCES.map((s) => (
                <Bar key={s} dataKey={s} fill={SOURCE_COLORS[s]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        )}

        <div className="mtr-callout">
          <IconInfoCircle size={20} stroke={1.5} />
          <div>
            <strong>Key finding</strong>: Employment income faces the highest
            baseline MTR (17.2%) while long-term capital gains face the lowest
            (4.7%). Under a 50% labor-to-capital shift, the employment MTR
            rises to 25.7% and qualified dividend MTR rises to 23.3%.
          </div>
        </div>

        <p className="mtr-metadata">
          PolicyEngine US microsimulation, $100 income bump, {mtrData.year}
        </p>
      </div>
    </div>
  );
}

export default MarginalTaxRates;
