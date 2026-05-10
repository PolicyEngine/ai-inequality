import React, { useState } from "react";
import UpratingViewer from "./UpratingViewer";

function StochasticForecasting() {
  const [expandedCard, setExpandedCard] = useState(null);
  const [showUpratingViewer, setShowUpratingViewer] = useState(false);

  const upratingCategories = [
    {
      category: "IRS Chained CPI-U",
      count: 214,
      percentage: 67,
      description:
        "Tax brackets, standard deductions, credits, and phase-outs indexed to chained CPI-U",
      examples: [
        "Federal income tax brackets",
        "Standard deduction amounts",
        "EITC phase-out thresholds",
        "Child Tax Credit parameters",
      ],
    },
    {
      category: "CPI-U Direct",
      count: 26,
      percentage: 8,
      description:
        "Direct CPI-U indexation for state tax parameters and federal benefit amounts",
      examples: [
        "State standard deductions (AR, LA)",
        "WIC benefit values",
        "School meal reimbursement rates",
      ],
    },
    {
      category: "Income growth by source",
      count: 12,
      percentage: 4,
      description:
        "CBO projections for different income types with potentially different growth rates",
      examples: [
        "Employment income",
        "Self-employment income",
        "Capital gains",
        "Qualified dividends",
        "Interest income",
        "Pension income",
        "Social Security income",
      ],
    },
    {
      category: "SSA Uprating (CPI-W)",
      count: 10,
      percentage: 3,
      description: "Social Security Administration parameters indexed to CPI-W",
      examples: ["Social Security benefit amounts", "Taxable wage base"],
    },
    {
      category: "Population growth",
      count: 10,
      percentage: 3,
      description: "Census Bureau population projections",
      examples: ["Total population by demographic group"],
    },
  ];

  const forecastingSources = [
    {
      title: "Survey of Professional Forecasters (SPF)",
      organization: "Federal Reserve Bank of Philadelphia",
      description:
        "Quarterly survey providing probability distributions for inflation, GDP growth, and unemployment. Longest-running US macroeconomic forecast survey (since 1968).",
      dataFormat: "Probability bins for key macro variables",
      url: "https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/survey-of-professional-forecasters",
    },
    {
      title: "CBO Economic Uncertainty Analysis",
      organization: "Congressional Budget Office",
      description:
        "Bayesian VAR and Markov-switching models to assess forecast uncertainty. Uses historical forecast errors to construct confidence intervals.",
      dataFormat: "Mean forecasts with uncertainty ranges",
      url: "https://www.cbo.gov/publication/58883",
    },
    {
      title: "Michigan Survey of Consumers",
      organization: "University of Michigan",
      description:
        "Consumer inflation expectations with distributional data showing heterogeneity across demographics and income levels.",
      dataFormat: "Point estimates with variance analysis",
      url: "https://data.sca.isr.umich.edu/",
    },
    {
      title: "New York Fed Outlook-at-Risk",
      organization: "Federal Reserve Bank of New York",
      description:
        "Constructs probability distributions for GDP growth, unemployment, and inflation using quantile vector autoregression.",
      dataFormat: "Time-varying probability distributions",
      url: "https://www.newyorkfed.org/research/policy/outlook-at-risk",
    },
  ];

  const modelingApproaches = [
    {
      method: "Vector Autoregression (VAR)",
      description:
        "Joint forecasting of multiple economic variables (inflation, wages, GDP) preserving correlations",
      advantages:
        "Captures dynamic interdependencies; standard tool at central banks",
      implementation:
        "One-step ahead forecasts with lagged values; iterate forward",
    },
    {
      method: "Copula-based models",
      description:
        "Separate modeling of marginal distributions and dependence structure",
      advantages:
        "Flexible specification of marginals; captures complex dependence patterns",
      implementation:
        "Model each variable separately, then link with copula function",
    },
    {
      method: "Bayesian VAR",
      description:
        "Incorporates prior information and provides full posterior distributions",
      advantages:
        "Natural uncertainty quantification; handles parameter uncertainty",
      implementation: "MCMC sampling from posterior; used by CBO",
    },
    {
      method: "Historical resampling",
      description:
        "Bootstrap from historical joint realizations of economic variables",
      advantages:
        "Simple; preserves actual historical correlations; no parametric assumptions",
      implementation: "Resample years from historical data with replacement",
    },
  ];

  return (
    <div id="stochastic-forecasting" className="section">
      <h2>Stochastic economic forecasting for microsimulation</h2>

      <div style={{ marginBottom: "2rem" }}>
        <p style={{ fontSize: "1.1rem", lineHeight: "1.6" }}>
          PolicyEngine-US uses <strong>318 uprating parameters</strong> to
          project tax and benefit rules forward in time. These parameters grow
          at different rates (CPI-U, CPI-W, wage growth, income by source) that
          are typically uncertain and correlated. Modeling their joint
          distribution is critical for understanding policy impacts under
          AI-driven economic scenarios.
        </p>
      </div>

      <h3>Uprating parameters in PolicyEngine-US</h3>
      <p style={{ textAlign: "center", marginBottom: "2rem" }}>
        Distribution of uprating categories across 318 parameters
      </p>

      <div className="grid">
        {upratingCategories.map((item, index) => (
          <div
            key={index}
            className={`card ${expandedCard === `uprating-${index}` ? "expanded" : ""}`}
            onClick={() =>
              setExpandedCard(
                expandedCard === `uprating-${index}`
                  ? null
                  : `uprating-${index}`,
              )
            }
            style={{ cursor: "pointer" }}
          >
            <h3
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              {item.category}
              <span
                style={{
                  fontSize: "0.9rem",
                  color: "#319795",
                  fontWeight: "normal",
                }}
              >
                {item.count} ({item.percentage}%)
              </span>
            </h3>
            <p>{item.description}</p>
            {expandedCard === `uprating-${index}` && (
              <div style={{ marginTop: "1rem" }}>
                <strong>Examples:</strong>
                <ul style={{ marginTop: "0.5rem" }}>
                  {item.examples.map((example, i) => (
                    <li key={i}>{example}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>

      <div style={{ marginTop: "2rem", marginBottom: "3rem" }}>
        <button
          onClick={() => setShowUpratingViewer(!showUpratingViewer)}
          style={{
            width: "100%",
            padding: "1rem 1.5rem",
            background: "#f0f9ff",
            border: "2px solid #319795",
            borderRadius: "8px",
            fontSize: "1.1rem",
            fontWeight: "600",
            cursor: "pointer",
            transition: "all 0.2s",
            textAlign: "left",
            color: "#319795",
          }}
        >
          {showUpratingViewer ? "▼" : "▶"} Interactive Uprating Explorer
        </button>
        {showUpratingViewer && (
          <div style={{ marginTop: "2rem" }}>
            <UpratingViewer />
          </div>
        )}
      </div>

      <h3 style={{ marginTop: "3rem" }}>Probabilistic Forecast Data Sources</h3>
      <p style={{ textAlign: "center", marginBottom: "2rem" }}>
        Existing sources for calibrating stochastic economic scenarios
      </p>

      <div className="grid">
        {forecastingSources.map((source, index) => (
          <div
            key={index}
            className={`card ${expandedCard === `source-${index}` ? "expanded" : ""}`}
            onClick={() =>
              setExpandedCard(
                expandedCard === `source-${index}` ? null : `source-${index}`,
              )
            }
            style={{ cursor: "pointer" }}
          >
            <h3
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              {source.title}
              <span style={{ fontSize: "1.2rem", color: "#319795" }}>
                {expandedCard === `source-${index}` ? "−" : "+"}
              </span>
            </h3>
            <p>
              <strong>{source.organization}</strong>
            </p>
            <p>{source.description}</p>
            {expandedCard === `source-${index}` && (
              <div style={{ marginTop: "1rem" }}>
                <p>
                  <strong>Data Format:</strong> {source.dataFormat}
                </p>
                <a
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  style={{
                    color: "#319795",
                    textDecoration: "underline",
                    display: "inline-block",
                    marginTop: "0.5rem",
                  }}
                >
                  View Source →
                </a>
              </div>
            )}
          </div>
        ))}
      </div>

      <h3 style={{ marginTop: "3rem" }}>Modeling Joint Distributions</h3>
      <p style={{ textAlign: "center", marginBottom: "2rem" }}>
        Methods for capturing correlations between economic variables
      </p>

      <div className="grid">
        {modelingApproaches.map((approach, index) => (
          <div
            key={index}
            className={`card ${expandedCard === `model-${index}` ? "expanded" : ""}`}
            onClick={() =>
              setExpandedCard(
                expandedCard === `model-${index}` ? null : `model-${index}`,
              )
            }
            style={{ cursor: "pointer" }}
          >
            <h3
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              {approach.method}
              <span style={{ fontSize: "1.2rem", color: "#319795" }}>
                {expandedCard === `model-${index}` ? "−" : "+"}
              </span>
            </h3>
            <p>{approach.description}</p>
            {expandedCard === `model-${index}` && (
              <div style={{ marginTop: "1rem" }}>
                <p>
                  <strong>Advantages:</strong> {approach.advantages}
                </p>
                <p>
                  <strong>Implementation:</strong> {approach.implementation}
                </p>
              </div>
            )}
          </div>
        ))}
      </div>

      <div
        className="card"
        style={{ marginTop: "2rem", backgroundColor: "#f0f9ff" }}
      >
        <h3>PolicyEngine's unique advantage</h3>
        <p>
          While we can provide default stochastic scenarios calibrated to
          professional forecasts and historical data,{" "}
          <strong>
            PolicyEngine's core advantage is enabling users to plug in their own
            distributional assumptions
          </strong>
          . This allows researchers, policymakers, and AI forecasters to test
          specific scenarios:
        </p>
        <ul style={{ marginTop: "1rem" }}>
          <li>
            AI companies can test policy resilience under explosive growth
            scenarios
          </li>
          <li>
            Think tanks can explore distributional effects under different
            inequality trajectories
          </li>
          <li>
            Researchers can validate findings across multiple forecast sources
          </li>
          <li>
            Policymakers can stress-test reforms under optimistic vs.
            pessimistic economic paths
          </li>
        </ul>
        <p style={{ marginTop: "1rem" }}>
          If no existing sources provide joint distributions of these variables,
          PolicyEngine is positioned to develop and maintain reference
          implementations that others can build upon.
        </p>
      </div>

      <div className="card" style={{ marginTop: "2rem" }}>
        <h3>Research roadmap</h3>
        <ol>
          <li>
            <strong>Phase 1: Marginal Distributions</strong> - Start with
            inflation uncertainty calibrated to SPF and CBO forecasts
          </li>
          <li>
            <strong>Phase 2: Simple Correlations</strong> - Model inflation-wage
            growth correlation using historical data
          </li>
          <li>
            <strong>Phase 3: Full VAR Model</strong> - Time-series approach with
            lagged values for all uprating factors
          </li>
          <li>
            <strong>Phase 4: AI Scenario Integration</strong> - Allow users to
            override specific growth paths while maintaining realistic
            correlations for other variables
          </li>
          <li>
            <strong>Phase 5: Validation</strong> - Compare PolicyEngine
            stochastic results against historical microsimulation accuracy
          </li>
        </ol>
      </div>
    </div>
  );
}

export default StochasticForecasting;
