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
  ReferenceLine,
} from "recharts";
import { IconArrowsExchange, IconInfoCircle } from "@tabler/icons-react";
import sweepData from "../data/shiftSweepData.json";
import capitalData from "../data/capitalDoublingData.json";
import "./ShiftSweep.css";

const TABS = [
  { key: "inequality", label: "Inequality" },
  { key: "revenue", label: "Tax revenue" },
  { key: "compare", label: "Shift vs. doubling" },
];

const TOOLTIP_STYLE = {
  background: "#fff",
  border: "1px solid #e2e8f0",
  borderRadius: 6,
  padding: "8px 12px",
  fontSize: 13,
};

const pctFmt = (v) => `${(v * 100).toFixed(1)}%`;
const bFmt = (v) => `$${v >= 0 ? "+" : ""}${v.toFixed(0)}B`;

const chartData = sweepData.scenarios.map((s) => ({
  shift: s.shift_pct,
  marketGini: s.market_gini,
  netGini: s.net_gini,
  poverty: s.spm_poverty_rate,
  revenue: s.revenue_change_b,
  incomeTax: s.income_tax_change_b,
  employeePayroll: s.employee_payroll_change_b,
  employerPayroll: s.employer_payroll_change_b,
  totalPayroll: s.employee_payroll_change_b + s.employer_payroll_change_b,
  eitc: s.eitc_change_b,
  snap: s.snap_change_b,
}));


function ShiftSweep() {
  const [activeTab, setActiveTab] = useState("inequality");

  return (
    <div id="shift-sweep" className="shift-sweep-section">
      <div className="shift-sweep-header">
        <div className="shift-sweep-icon-wrapper">
          <IconArrowsExchange size={28} stroke={1.5} />
        </div>
        <h2>Labor-to-capital shift: sensitivity across shift magnitudes</h2>
        <p className="shift-sweep-subtitle">
          How inequality, poverty, and tax revenue change as a growing share of
          labor income is replaced by capital income — holding total GDP constant
        </p>
      </div>

      <div className="shift-sweep-card">
        <div className="shift-sweep-tabs">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              className={`shift-sweep-tab ${activeTab === tab.key ? "active" : ""}`}
              onClick={() => setActiveTab(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === "inequality" && (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart
              data={chartData}
              margin={{ left: 20, right: 30, top: 10, bottom: 35 }}
            >
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
              <XAxis
                dataKey="shift"
                tickFormatter={(v) => `${v}%`}
                tick={{ fontSize: 12 }}
                label={{
                  value: "Share of labor income shifted to capital",
                  position: "bottom",
                  offset: 0,
                  style: { fontSize: 13 },
                }}
              />
              <YAxis
                domain={[0, 1]}
                tickFormatter={(v) => v.toFixed(2)}
                tick={{ fontSize: 12 }}
                label={{
                  value: "Gini / poverty rate",
                  angle: -90,
                  position: "insideLeft",
                  offset: -5,
                  style: { fontSize: 13 },
                }}
              />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                formatter={(value, name) => [value.toFixed(4), name]}
                labelFormatter={(v) => `${v}% shift`}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="marketGini"
                name="Market Gini"
                stroke="#e07b39"
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
                dataKey="poverty"
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
              data={chartData}
              margin={{ left: 20, right: 30, top: 10, bottom: 35 }}
            >
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
              <XAxis
                dataKey="shift"
                tickFormatter={(v) => `${v}%`}
                tick={{ fontSize: 12 }}
                label={{
                  value: "Share of labor income shifted to capital",
                  position: "bottom",
                  offset: 0,
                  style: { fontSize: 13 },
                }}
              />
              <YAxis
                tickFormatter={(v) => `$${v >= 0 ? "+" : ""}${v.toFixed(0)}B`}
                tick={{ fontSize: 12 }}
                label={{
                  value: "Revenue change vs baseline ($B)",
                  angle: -90,
                  position: "insideLeft",
                  offset: -10,
                  style: { fontSize: 13 },
                }}
              />
              <ReferenceLine y={0} stroke="#718096" strokeDasharray="4 4" />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                formatter={(value, name) => [bFmt(value), name]}
                labelFormatter={(v) => `${v}% shift`}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="revenue"
                name="Net revenue change"
                stroke="#319795"
                strokeWidth={3}
                dot={{ r: 5 }}
              />
              <Line
                type="monotone"
                dataKey="incomeTax"
                name="Income tax change"
                stroke="#2C6496"
                strokeWidth={2}
                dot={{ r: 3 }}
              />
              <Line
                type="monotone"
                dataKey="totalPayroll"
                name="Payroll tax change (employee + employer)"
                stroke="#e07b39"
                strokeWidth={2}
                dot={{ r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}

        {activeTab === "compare" && (
          <div className="compare-grid">
            <table className="compare-table">
              <thead>
                <tr>
                  <th>Scenario</th>
                  <th>GDP effect</th>
                  <th>Net Gini</th>
                  <th>SPM poverty</th>
                  <th>Revenue change</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Baseline</td>
                  <td>—</td>
                  <td>{sweepData.scenarios[0]?.net_gini.toFixed(4)}</td>
                  <td>{pctFmt(sweepData.scenarios[0]?.spm_poverty_rate)}</td>
                  <td>—</td>
                </tr>
                <tr className="compare-row-shift">
                  <td>50% labor→capital shift</td>
                  <td>Neutral (GDP constant)</td>
                  <td>
                    {sweepData.scenarios
                      .find((s) => s.shift_pct === 50)
                      ?.net_gini.toFixed(4)}
                  </td>
                  <td>
                    {pctFmt(
                      sweepData.scenarios.find((s) => s.shift_pct === 50)
                        ?.spm_poverty_rate
                    )}
                  </td>
                  <td>
                    {bFmt(
                      sweepData.scenarios.find((s) => s.shift_pct === 50)
                        ?.revenue_change_b
                    )}
                  </td>
                </tr>
                <tr className="compare-row-shift">
                  <td>100% labor→capital shift</td>
                  <td>Neutral (GDP constant)</td>
                  <td>
                    {sweepData.scenarios
                      .find((s) => s.shift_pct === 100)
                      ?.net_gini.toFixed(4)}
                  </td>
                  <td>
                    {pctFmt(
                      sweepData.scenarios.find((s) => s.shift_pct === 100)
                        ?.spm_poverty_rate
                    )}
                  </td>
                  <td>
                    {bFmt(
                      sweepData.scenarios.find((s) => s.shift_pct === 100)
                        ?.revenue_change_b
                    )}
                  </td>
                </tr>
                <tr className="compare-row-double">
                  <td>Capital income doubled</td>
                  <td>+GDP (capital more productive)</td>
                  <td>{capitalData.doubled.net_gini.toFixed(4)}</td>
                  <td>{pctFmt(capitalData.doubled.spm_poverty_rate)}</td>
                  <td>{bFmt(capitalData.doubled.revenue_change_b)}</td>
                </tr>
              </tbody>
            </table>

            <div className="shift-sweep-callout">
              <IconInfoCircle size={20} stroke={1.5} />
              <div>
                The two AI scenarios have sharply different distributional
                consequences. When AI displaces workers (shift scenario), most
                households lose labor income they cannot replace with capital
                income they do not own — the bottom nine deciles hold only 14.5%
                of positive capital income. When AI boosts capital productivity
                (doubling scenario), total incomes rise and poverty barely
                changes, though the top decile captures most gains.
              </div>
            </div>
          </div>
        )}

        {activeTab !== "compare" && (
          <div className="shift-sweep-callout">
            <IconInfoCircle size={20} stroke={1.5} />
            {activeTab === "inequality" && (
              <div>
                Inequality and poverty rise monotonically with the shift magnitude.
                At 50%, SPM poverty reaches{" "}
                {pctFmt(sweepData.scenarios.find((s) => s.shift_pct === 50)?.spm_poverty_rate)}{" "}
                and the net Gini rises from{" "}
                {sweepData.scenarios[0]?.net_gini.toFixed(3)} to{" "}
                {sweepData.scenarios.find((s) => s.shift_pct === 50)?.net_gini.toFixed(3)}.
                At 100%, poverty reaches{" "}
                {pctFmt(sweepData.scenarios.find((s) => s.shift_pct === 100)?.spm_poverty_rate)}
                {" "}— reflecting that most households have negligible capital income
                to replace lost wages.
              </div>
            )}
            {activeTab === "revenue" && (
              <div>
                Including both employee and employer payroll taxes, the
                labor-to-capital shift is revenue-negative at every magnitude.
                Although income tax revenue rises (capital income faces higher
                income tax rates than wages alone), the combined payroll tax loss
                from both sides more than offsets it. Employer payroll tax losses
                roughly mirror employee losses at each shift level.
              </div>
            )}
          </div>
        )}

        <p className="shift-sweep-metadata">
          PolicyEngine US microsimulation, 2026. Labor→capital shift holds total
          GDP constant; capital doubling adds new income. Static analysis only.
        </p>
      </div>
    </div>
  );
}

export default ShiftSweep;
