import React, { useState, useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { IconTrendingDown, IconInfoCircle } from "@tabler/icons-react";
import cliffData from "../data/cliffData.json";
import "./CapitalIncomeCliff.css";

const TABS = [
  { key: "dividends", label: "Qualified dividends" },
  { key: "ltcg", label: "Long-term capital gains" },
];

const SERIES = [
  { key: "netIncome", label: "Net income", color: "#319795", width: 3 },
  { key: "eitc", label: "EITC", color: "#e53e3e", width: 2 },
  { key: "snap", label: "SNAP", color: "#38a169", width: 2 },
  {
    key: "incomeTax",
    label: "Federal income tax",
    color: "#2C6496",
    width: 2,
  },
];

function niceTicks(dataMax, targetCount = 5) {
  if (dataMax <= 0) return [0];
  const rawStep = dataMax / targetCount;
  const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)));
  const normalized = rawStep / magnitude;
  let niceStep;
  if (normalized <= 1) niceStep = 1 * magnitude;
  else if (normalized <= 2) niceStep = 2 * magnitude;
  else if (normalized <= 2.5) niceStep = 2.5 * magnitude;
  else if (normalized <= 5) niceStep = 5 * magnitude;
  else niceStep = 10 * magnitude;
  const niceMax = Math.ceil(dataMax / niceStep) * niceStep;
  const ticks = [];
  for (let v = 0; v <= niceMax; v += niceStep) {
    ticks.push(Math.round(v * 1e10) / 1e10);
  }
  return ticks;
}

const fmt = (v) =>
  v.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });

const TOOLTIP_STYLE = {
  background: "#fff",
  border: "1px solid #e2e8f0",
  borderRadius: 6,
  padding: "8px 12px",
  fontSize: 13,
};

function findCliff(data) {
  let worstIdx = 0;
  let worstDrop = 0;
  for (let i = 1; i < data.length; i++) {
    const drop = data[i].netIncome - data[i - 1].netIncome;
    if (drop < worstDrop) {
      worstDrop = drop;
      worstIdx = i;
    }
  }
  return {
    capitalIncome: data[worstIdx].capitalIncome,
    drop: worstDrop,
    beforeNet: data[worstIdx - 1]?.netIncome,
    afterNet: data[worstIdx].netIncome,
  };
}

function CapitalIncomeCliff() {
  const [activeTab, setActiveTab] = useState("dividends");
  const [showComponents, setShowComponents] = useState(false);

  const data = cliffData[activeTab];
  const cliff = useMemo(() => findCliff(data), [data]);

  const xMax = Math.max(...data.map((d) => d.capitalIncome));
  const xTicks = niceTicks(xMax);

  const yValues = showComponents
    ? data.flatMap((d) => [d.netIncome, d.eitc, d.snap, d.incomeTax])
    : data.map((d) => d.netIncome);
  const yMin = Math.min(...yValues);
  const yMax = Math.max(...yValues);
  const yRange = yMax - yMin;
  const yDomainMin = Math.floor((yMin - yRange * 0.05) / 1000) * 1000;
  const yDomainMax = Math.ceil((yMax + yRange * 0.05) / 1000) * 1000;

  const visibleSeries = showComponents
    ? SERIES
    : SERIES.filter((s) => s.key === "netIncome");

  const tabLabel =
    TABS.find((t) => t.key === activeTab)?.label || "capital income";

  return (
    <div id="capital-income-cliff" className="cliff-section">
      <div className="cliff-header">
        <div className="cliff-icon-wrapper">
          <IconTrendingDown size={28} stroke={1.5} />
        </div>
        <h2>Capital income cliffs</h2>
        <p className="cliff-subtitle">
          How benefit cliffs punish low-income families who receive investment
          income
        </p>
      </div>

      <div className="cliff-card">
        <div className="cliff-controls">
          <div className="cliff-tabs">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                className={`cliff-tab ${activeTab === tab.key ? "active" : ""}`}
                onClick={() => setActiveTab(tab.key)}
              >
                {tab.label}
              </button>
            ))}
          </div>
          <label className="cliff-toggle">
            <input
              type="checkbox"
              checked={showComponents}
              onChange={(e) => setShowComponents(e.target.checked)}
            />
            <span>Show components</span>
          </label>
        </div>

        <ResponsiveContainer width="100%" height={400}>
          <LineChart
            data={data}
            margin={{ left: 20, right: 30, top: 10, bottom: 20 }}
          >
            <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
            <XAxis
              dataKey="capitalIncome"
              type="number"
              domain={[0, xTicks[xTicks.length - 1]]}
              ticks={xTicks}
              tickFormatter={fmt}
              tick={{ fontSize: 12 }}
              label={{
                value: tabLabel + " ($)",
                position: "bottom",
                offset: 0,
                style: { fontSize: 13 },
              }}
            />
            <YAxis
              domain={[yDomainMin, yDomainMax]}
              tickFormatter={fmt}
              tick={{ fontSize: 12 }}
              label={{
                value: "Annual amount ($)",
                angle: -90,
                position: "insideLeft",
                offset: -5,
                style: { fontSize: 13 },
              }}
            />
            <Tooltip
              contentStyle={TOOLTIP_STYLE}
              separator=": "
              formatter={(value, name) => {
                const series = SERIES.find((s) => s.key === name);
                return [fmt(value), series?.label || name];
              }}
              labelFormatter={(v) => `${tabLabel}: ${fmt(v)}`}
            />
            <ReferenceLine
              x={cliff.capitalIncome}
              stroke="#e53e3e"
              strokeDasharray="4 4"
              strokeWidth={1.5}
            />
            {visibleSeries.map((s) => (
              <Line
                key={s.key}
                type="monotone"
                dataKey={s.key}
                stroke={s.color}
                strokeWidth={s.width}
                dot={false}
                name={s.key}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>

        <div className="cliff-callout">
          <IconInfoCircle size={20} stroke={1.5} />
          <div>
            <strong>EITC investment income cliff</strong>: At{" "}
            {fmt(cliff.capitalIncome)} in {tabLabel.toLowerCase()}, this
            household loses {fmt(Math.abs(cliff.drop))} in net income. The EITC
            has a hard eligibility cutoff based on investment income (~$12,000 in
            2026), causing a sudden loss of the entire credit.
          </div>
        </div>

        <p className="cliff-household-desc">
          {cliffData.household.description} ({cliffData.household.year})
        </p>
      </div>
    </div>
  );
}

export default CapitalIncomeCliff;
