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
import "./PolicyAnalysis.css";

const COUNTRY_KEYS = Object.keys(COUNTRIES);

function formatTrillions(value, currencySymbol) {
  return value == null ? "-" : `${currencySymbol}${value.toFixed(1)}T`;
}

function formatShare(value) {
  return value == null ? "-" : `${Math.round(value * 100)}%`;
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

      <ShiftSweep sweepData={sweepData} />
    </>
  );
}

export default IncomeShift;
