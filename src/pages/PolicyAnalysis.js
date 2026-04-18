import React from "react";
import { useSearchParams } from "react-router-dom";
import BaselineDistributionSummary from "../components/BaselineDistributionSummary";
import IncomeDistributionBreakdown from "../components/IncomeDistributionBreakdown";
import ShiftSweep from "../components/ShiftSweep";
import {
  COUNTRIES,
  countryFromSearchParams,
  incomeShiftUrl,
} from "../utils/countryConfig";
import { policyEngineLabel } from "../utils/modelMetadata";
import "./PolicyAnalysis.css";

function formatTrillions(value, currencySymbol) {
  return value == null ? "—" : `${currencySymbol}${value.toFixed(1)}T`;
}

function formatShare(value) {
  return value == null ? "—" : `${Math.round(value * 100)}%`;
}

function PolicyAnalysis() {
  const [searchParams] = useSearchParams();
  const countryKey = countryFromSearchParams(searchParams);
  const country = COUNTRIES[countryKey];
  const sweepData = country.sweepData;
  const metadata = sweepData.metadata ?? {};
  const baselineFacts = metadata.baseline_facts ?? {};
  const docsUrl = metadata.model_url ?? "https://www.policyengine.org/us/model";
  const modelLabel = policyEngineLabel(metadata);
  const currencySymbol = metadata.currency_symbol ?? "$";
  const laborTerm = metadata.labor_label ?? "labor";

  return (
    <>
      <div className="section section-alt policy-analysis-hero">
        <div className="policy-analysis-hero-card">
          <div className="policy-analysis-kicker">Prototype analysis</div>
          <h1>What if income shifts from {laborTerm} to capital?</h1>
          <p className="policy-analysis-subtitle">
            This page is a concrete example of the kind of work we want to do
            more of: define a plausible AI-driven economic shock, run it through
            PolicyEngine, and show who gains, who loses, and how the public
            budget responds under current law.
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
                holdings. The exercise is mechanically market-income-neutral and
                static.
              </p>
            </div>
            <div className="policy-analysis-brief-card">
              <h2>Model</h2>
              <p>
                Results shown here come from <strong>{modelLabel}</strong> on a{" "}
                <strong>{metadata.year ?? sweepData.year}</strong> baseline. For
                the model structure and variable definitions, see the{" "}
                <a href={docsUrl} target="_blank" rel="noreferrer">
                  PolicyEngine model documentation
                </a>
                .
              </p>
            </div>
          </div>

          <div className="policy-analysis-actions">
            <a
              href={incomeShiftUrl(countryKey)}
              target="_top"
              className="policy-analysis-primary-link"
            >
              Open the income-shift experiment
            </a>
          </div>

          <BaselineDistributionSummary
            sweepData={sweepData}
            incomeDistributionData={country.incomeDistributionData}
          />
        </div>
      </div>

      {country.incomeDistributionData && <IncomeDistributionBreakdown />}
      <ShiftSweep sweepData={sweepData} />
    </>
  );
}

export default PolicyAnalysis;
