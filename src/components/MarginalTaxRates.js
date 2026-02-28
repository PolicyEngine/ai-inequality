import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { IconPercentage, IconInfoCircle } from "@tabler/icons-react";
import mtrData from "../data/mtrData.json";
import "./MarginalTaxRates.css";

const COLORS = {
  Employment: "#319795",
  "Self-emp": "#805AD5",
  LTCG: "#D69E2E",
  STCG: "#e07b39",
  "Qual div": "#2C6496",
};

const TOOLTIP_STYLE = {
  background: "#fff",
  border: "1px solid #e2e8f0",
  borderRadius: 6,
  padding: "8px 12px",
  fontSize: 13,
};

const pct = (v) => `${(v * 100).toFixed(1)}%`;

function MarginalTaxRates() {
  return (
    <div id="marginal-tax-rates" className="mtr-section">
      <div className="mtr-header">
        <div className="mtr-icon-wrapper">
          <IconPercentage size={28} stroke={1.5} />
        </div>
        <h2>Marginal tax rates by income source</h2>
        <p className="mtr-subtitle">
          Dollar-weighted average effective marginal tax rates — each person's
          rate weighted by their share of total income in that category
        </p>
      </div>

      <div className="mtr-card">
        <ResponsiveContainer width="100%" height={380}>
          <BarChart
            data={mtrData.baseline}
            margin={{ left: 20, right: 20, top: 10, bottom: 5 }}
          >
            <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
            <XAxis dataKey="source" tick={{ fontSize: 13 }} />
            <YAxis
              tickFormatter={pct}
              tick={{ fontSize: 12 }}
              domain={[0, 0.8]}
              label={{
                value: "Dollar-weighted MTR",
                angle: -90,
                position: "insideLeft",
                offset: -5,
                style: { fontSize: 13 },
              }}
            />
            <Tooltip
              contentStyle={TOOLTIP_STYLE}
              formatter={(value, _, props) => [
                pct(value),
                props.payload.source,
              ]}
              labelFormatter={() => "Baseline (2026)"}
            />
            <Bar dataKey="mtr" radius={[4, 4, 0, 0]}>
              {mtrData.baseline.map((entry) => (
                <Cell
                  key={entry.source}
                  fill={COLORS[entry.source] || "#319795"}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>

        <div className="mtr-callout">
          <IconInfoCircle size={20} stroke={1.5} />
          <div>
            <strong>Key finding</strong>: Employment income (32.8%) and
            self-employment (43.9%) face higher dollar-weighted MTRs than
            long-term capital gains (28.5%) and qualified dividends (24.8%).
            This indicates a labor-to-capital income shift would reduce tax
            revenues absent other effects. STCG (72.2%) reflects a small
            volume of gains concentrated among high-bracket taxpayers.
          </div>
        </div>

        <p className="mtr-metadata">
          PolicyEngine US microsimulation, 1% proportional bump, {mtrData.year}.
          Dollar-weighted: each person's marginal rate weighted by income share.
        </p>
      </div>
    </div>
  );
}

export default MarginalTaxRates;
