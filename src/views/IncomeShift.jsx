import React from "react";
import { useSearchParams } from "react-router-dom";
import BaselineDistributionSummary from "../components/BaselineDistributionSummary";
import ShiftSweep from "../components/ShiftSweep";
import {
  aiInequalityUrl,
  COUNTRIES,
  countryFromSearchParams,
} from "../utils/countryConfig";
import { policyEngineLabel } from "../utils/modelMetadata";
import { useRovingRadioGroup } from "../utils/useRovingRadioGroup";

const COUNTRY_KEYS = Object.keys(COUNTRIES);

function formatTrillions(value, currencySymbol) {
  return value == null ? "-" : `${currencySymbol}${value.toFixed(1)}T`;
}

function formatShare(value) {
  return value == null ? "-" : `${Math.round(value * 100)}%`;
}

function formatBillionsChange(value, currencySymbol) {
  if (value == null) return "-";
  const sign = value >= 0 ? "+" : "-";
  return `${sign}${currencySymbol}${Math.abs(value).toFixed(0)}B`;
}

function formatPct1(value) {
  return value == null ? "-" : `${(value * 100).toFixed(1)}%`;
}

function headlineFindings(sweepData) {
  const scenarios = sweepData?.scenarios ?? [];
  const baseline = scenarios.find((s) => s.shift_pct === 0);
  const hundred = scenarios.find((s) => s.shift_pct === 100);
  if (!baseline || !hundred) return null;
  const trough = scenarios.reduce(
    (min, row) =>
      (row.total_rev_change_b ?? row.revenue_change_b ?? 0) <
      (min.total_rev_change_b ?? min.revenue_change_b ?? 0)
        ? row
        : min,
    baseline,
  );
  const deciles =
    sweepData?.metadata?.baseline_facts?.decile_impacts?.scenarios ?? [];
  const lastDecileScen = deciles.find((s) => s.shift_pct === 100);
  const topDecilePct =
    lastDecileScen?.deciles?.find((d) => d.decile === 10)?.pct_change ?? null;
  let worstDecile = null;
  let worstPct = null;
  for (const d of lastDecileScen?.deciles ?? []) {
    if (
      Number.isFinite(d.pct_change) &&
      d.decile !== 10 &&
      (worstPct == null || d.pct_change < worstPct)
    ) {
      worstPct = d.pct_change;
      worstDecile = d.decile;
    }
  }
  return {
    baselineGini: baseline.net_gini,
    hundredGini: hundred.net_gini,
    baselinePoverty: baseline.spm_poverty_rate,
    hundredPoverty: hundred.spm_poverty_rate,
    troughRevenueB:
      trough.total_rev_change_b ?? trough.revenue_change_b ?? null,
    troughShift: trough.shift_pct,
    topDecilePct,
    worstDecile,
    worstPct: worstPct != null ? worstPct / 100 : null,
  };
}

function IncomeShift() {
  const [searchParams, setSearchParams] = useSearchParams();
  const countryKey = countryFromSearchParams(searchParams);
  const country = COUNTRIES[countryKey];
  const sweepData = country.sweepData;
  const metadata = sweepData.metadata ?? {};
  const baselineFacts = metadata.baseline_facts ?? {};
  const docsUrl = metadata.model_url ?? "https://www.policyengine.org/us/model";
  const modelLabel = policyEngineLabel(metadata);
  const currencySymbol = metadata.currency_symbol ?? "$";
  const laborTerm = metadata.labor_label ?? "labor";
  const overviewUrl = aiInequalityUrl(countryKey);
  const countryNav = useRovingRadioGroup(COUNTRY_KEYS, countryKey);

  const selectCountry = (key) => {
    setSearchParams(key === "us" ? {} : { country: key });
  };

  return (
    <>
      <div className="section section-alt policy-analysis-hero">
        <div className="policy-analysis-hero-card">
          <a
            href={overviewUrl}
            target="_top"
            className="policy-analysis-back-link"
          >
            Back to AI inequality overview
          </a>
          <div className="policy-analysis-kicker">Income-shift experiment</div>
          <h1>What if income shifts from {laborTerm} to capital?</h1>
          <div
            className="policy-analysis-country-tabs"
            role="radiogroup"
            aria-label="Country"
          >
            {Object.entries(COUNTRIES).map(([key, option]) => (
              <button
                key={key}
                ref={countryNav.getRef(key)}
                type="button"
                role="radio"
                aria-checked={countryKey === key}
                tabIndex={countryKey === key ? 0 : -1}
                className={`analysis-tab ${countryKey === key ? "active" : ""}`}
                onClick={() => selectCountry(key)}
                onKeyDown={countryNav.keyDownHandler(selectCountry)}
              >
                {option.label}
              </button>
            ))}
          </div>
          <p className="policy-analysis-subtitle">
            A direct view of the prototype experiment: remove positive{" "}
            {laborTerm} income, route the same dollars through existing positive
            capital income, and measure distributional and fiscal effects under
            current law.
          </p>

          <div className="policy-analysis-brief">
            <div className="policy-analysis-brief-card">
              <h2>Baseline facts</h2>
              <p>
                The {metadata.year ?? sweepData.year} {country.label} baseline
                contains{" "}
                <strong>
                  {formatTrillions(
                    baselineFacts.labor_income_t,
                    currencySymbol,
                  )}
                </strong>{" "}
                in positive {laborTerm} income and{" "}
                <strong>
                  {formatTrillions(
                    baselineFacts.positive_capital_income_t,
                    currencySymbol,
                  )}
                </strong>{" "}
                in positive capital income. About{" "}
                <strong>
                  {formatShare(
                    baselineFacts.households_with_positive_capital_income_share,
                  )}
                </strong>{" "}
                of households receive any positive capital income.
              </p>
            </div>
            <div className="policy-analysis-brief-card">
              <h2>The experiment</h2>
              <p>
                We reduce positive employment and self-employment income by 0%
                to 100% in 10-point steps, then redistribute the same weighted
                total to positive capital income in proportion to existing
                holdings.
              </p>
            </div>
            <div className="policy-analysis-brief-card">
              <h2>Model</h2>
              <p>
                Results shown here come from <strong>{modelLabel}</strong> on a{" "}
                <strong>{metadata.year ?? sweepData.year}</strong> baseline. See
                the{" "}
                <a href={docsUrl} target="_blank" rel="noreferrer">
                  PolicyEngine model documentation
                </a>
                .
              </p>
            </div>
          </div>

          <BaselineDistributionSummary
            sweepData={sweepData}
            incomeDistributionData={country.incomeDistributionData}
          />
        </div>
      </div>

      {(() => {
        const findings = headlineFindings(sweepData);
        if (!findings) return null;
        return (
          <div className="section section-alt">
            <div className="policy-analysis-brief">
              <div className="policy-analysis-brief-card">
                <h2>Inequality</h2>
                <p>
                  Net-income Gini rises from{" "}
                  <strong>{findings.baselineGini?.toFixed(3)}</strong> at
                  baseline to{" "}
                  <strong>{findings.hundredGini?.toFixed(3)}</strong> at a 100%
                  shift.
                </p>
              </div>
              <div className="policy-analysis-brief-card">
                <h2>Poverty</h2>
                <p>
                  SPM poverty rises from{" "}
                  <strong>{formatPct1(findings.baselinePoverty)}</strong> to{" "}
                  <strong>{formatPct1(findings.hundredPoverty)}</strong>.
                </p>
              </div>
              <div className="policy-analysis-brief-card">
                <h2>Government revenue</h2>
                <p>
                  Net revenue bottoms at{" "}
                  <strong>
                    {formatBillionsChange(
                      findings.troughRevenueB,
                      currencySymbol,
                    )}
                  </strong>{" "}
                  at a {findings.troughShift}% shift under current law.
                </p>
              </div>
              <div className="policy-analysis-brief-card">
                <h2>Winners and losers</h2>
                <p>
                  At a 100% shift, the top decile's mean net income rises{" "}
                  <strong>
                    {findings.topDecilePct != null
                      ? `${findings.topDecilePct >= 0 ? "+" : ""}${findings.topDecilePct.toFixed(0)}%`
                      : "-"}
                  </strong>
                  {findings.worstPct != null && findings.worstDecile ? (
                    <>
                      {" "}
                      while decile {findings.worstDecile} loses{" "}
                      <strong>{formatPct1(findings.worstPct)}</strong>.
                    </>
                  ) : (
                    "."
                  )}
                </p>
              </div>
            </div>
          </div>
        );
      })()}

      <ShiftSweep sweepData={sweepData} />
    </>
  );
}

export default IncomeShift;
