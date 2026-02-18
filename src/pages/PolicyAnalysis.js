import React from "react";
import PolicyScenarios from "../components/PolicyScenarios";
import PolicyEngineCapabilities from "../components/PolicyEngineCapabilities";
import CapitalIncomeCliff from "../components/CapitalIncomeCliff";
import CapitalSweep from "../components/CapitalSweep";
import LaborShift from "../components/LaborShift";
import MarginalTaxRates from "../components/MarginalTaxRates";
import ShiftSweep from "../components/ShiftSweep";

function PolicyAnalysis() {
  return (
    <>
      <div className="section section-alt" style={{ paddingTop: "6rem" }}>
        <h1
          style={{
            textAlign: "center",
            marginBottom: "1rem",
            fontSize: "3rem",
          }}
        >
          Policy Analysis Framework
        </h1>
        <p
          style={{
            textAlign: "center",
            fontSize: "1.2rem",
            maxWidth: "800px",
            margin: "0 auto 3rem",
          }}
        >
          How PolicyEngine analyzes distributional impacts of tax-benefit
          policies under AI-driven economic scenarios
        </p>
      </div>
      <PolicyScenarios />
      <CapitalSweep />
      <LaborShift />
      <ShiftSweep />
      <MarginalTaxRates />
      <CapitalIncomeCliff />
      <PolicyEngineCapabilities />
      <div
        className="section"
        style={{ textAlign: "center", padding: "3rem 2rem" }}
      >
        <a
          href="/"
          style={{
            color: "#319795",
            fontSize: "1.1rem",
            textDecoration: "none",
          }}
        >
          ← Back to Home
        </a>
      </div>
    </>
  );
}

export default PolicyAnalysis;
