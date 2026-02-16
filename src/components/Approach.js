import React from "react";
import "./Approach.css";

const Source = ({ href, children }) => (
  <a
    href={href}
    target="_blank"
    rel="noopener noreferrer"
    className="inline-source"
  >
    {children}
  </a>
);

function Approach() {
  const pipeline = [
    {
      step: 1,
      title: "AI economic scenarios",
      description: "Inputs from researchers, forecasters, economic models",
    },
    {
      step: 2,
      title: "PolicyEngine microsimulation",
      description: "Open-source tax-benefit models for US, UK, Canada",
    },
    {
      step: 3,
      title: "Distributional outcomes",
      description: "Inequality metrics, poverty rates, winners/losers analysis",
    },
    {
      step: 4,
      title: "Policy comparison",
      description:
        "Current law vs. UBI, expanded safety nets, capital taxation, hybrid approaches",
    },
  ];

  const capabilities = [
    {
      title: "Open source",
      description: (
        <>
          All models, data, and code are{" "}
          <Source href="https://github.com/PolicyEngine">
            open source (AGPL-3.0)
          </Source>
          . 10,000+ policy parameters encoded for the US tax-benefit system.
        </>
      ),
    },
    {
      title: "Proven infrastructure",
      description: (
        <>
          Used by the{" "}
          <Source href="https://policyengine.org/uk/research/autumn-budget-2024-policy-reform-impacts">
            UK government
          </Source>
          , US congressional offices, and leading think tanks. Cited by{" "}
          <Source href="https://www.cbo.gov/">CBO</Source>,{" "}
          <Source href="https://home.treasury.gov/">Treasury</Source>, and
          academic researchers.
        </>
      ),
    },
    {
      title: "AI-native",
      description: (
        <>
          PolicyEngine uses{" "}
          <Source href="https://github.com/PolicyEngine/policyengine-us">
            multi-agent AI
          </Source>{" "}
          to encode policy rules at scale, enabling rapid model expansion for
          new scenarios.
        </>
      ),
    },
  ];

  return (
    <div className="approach-section">
      <div className="section-header">
        <span className="eyebrow">PolicyEngine's role</span>
        <h2>Our approach</h2>
      </div>

      <div className="approach-pipeline">
        {pipeline.map((item, idx) => (
          <React.Fragment key={idx}>
            <div className="pipeline-step">
              <div className="pipeline-number">{item.step}</div>
              <h3>{item.title}</h3>
              <p>{item.description}</p>
            </div>
            {idx < pipeline.length - 1 && (
              <div className="pipeline-arrow">{"\u2192"}</div>
            )}
          </React.Fragment>
        ))}
      </div>

      <div className="approach-description">
        <p>
          We don't forecast AI's trajectory or prescribe optimal policies. We
          provide the infrastructure to translate any AI economic scenario into
          household-level distributional outcomes under different policy
          regimes {"\u2014"} enabling researchers, policymakers, and funders to
          evaluate policy responses rigorously.
        </p>
      </div>

      <div className="capability-grid">
        {capabilities.map((item, idx) => (
          <div key={idx} className="capability-card">
            <h3>{item.title}</h3>
            <p>{item.description}</p>
          </div>
        ))}
      </div>

      <div className="uncertainty-box">
        <h3>Quantifying uncertainty</h3>
        <p>
          Traditional policy analysis reports only point estimates (e.g., CBO
          baseline forecasts). AI-driven economic change involves profound
          uncertainty. We model ranges of scenarios to show how policy impacts
          vary across different AI trajectories.
        </p>
        <div className="uncertainty-stats">
          <div className="uncertainty-stat">
            <div className="uncertainty-value">Multiple</div>
            <div className="uncertainty-label">AI scenarios</div>
          </div>
          <div className="uncertainty-stat">
            <div className="uncertainty-value">Probabilistic</div>
            <div className="uncertainty-label">Forecasts</div>
          </div>
          <div className="uncertainty-stat">
            <div className="uncertainty-value">Robust</div>
            <div className="uncertainty-label">Policy analysis</div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Approach;
