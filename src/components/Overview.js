import React from "react";
import "./Overview.css";
import {
  IconTrendingUp,
  IconBuildingFactory2,
  IconAlertTriangle,
  IconChartBar,
  IconMicroscope,
  IconDice,
  IconWorld,
} from "@tabler/icons-react";

function Overview() {
  const challenges = [
    {
      icon: <IconTrendingUp size={32} stroke={1.5} />,
      title: "Rising incomes",
      desc: "Productivity gains, unevenly distributed",
    },
    {
      icon: <IconBuildingFactory2 size={32} stroke={1.5} />,
      title: "Capital share growth",
      desc: "AI replacing or augmenting labor",
    },
    {
      icon: <IconAlertTriangle size={32} stroke={1.5} />,
      title: "Labor disruption",
      desc: "Potential technological unemployment",
    },
    {
      icon: <IconChartBar size={32} stroke={1.5} />,
      title: "Growing inequality",
      desc: "Gap between beneficiaries and displaced",
    },
  ];

  const approach = [
    {
      step: 1,
      title: "AI economic shocks",
      desc: "Income changes, unemployment, capital share shifts",
    },
    {
      step: 2,
      title: "Policy mediation",
      desc: "Taxes, transfers, UBI proposals, safety nets",
    },
    {
      step: 3,
      title: "Distributional outcomes",
      desc: "Income, consumption, wealth inequality effects",
    },
    {
      step: 4,
      title: "Cross-policy comparison",
      desc: "How different interventions shape outcomes",
    },
  ];

  return (
    <div id="overview" className="overview-section">
      <div className="section-header">
        <h2>Research overview</h2>
        <p className="section-subtitle">
          Examining the causal chain: AI economic shocks → policy interventions
          → distributional outcomes
        </p>
      </div>

      {/* Challenge Section - Icon Grid */}
      <div className="challenge-container">
        <h3 className="subsection-title">Potential AI economic shocks</h3>
        <p className="intro-text">
          AI could drive major changes in income distribution through various
          mechanisms:
        </p>
        <div className="icon-grid">
          {challenges.map((item, idx) => (
            <div key={idx} className="icon-card">
              <div className="icon-large">{item.icon}</div>
              <h4>{item.title}</h4>
              <p>{item.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Approach Section - Process Flow */}
      <div className="approach-container">
        <h3 className="subsection-title">Research framework</h3>
        <p className="intro-text">
          We examine how economic policies mediate the relationship between AI
          shocks and distributional outcomes. Researchers provide AI economic
          scenarios as inputs, we microsimulate policy responses using
          PolicyEngine models (US, UK, or other countries), and analyze
          resulting distributions of income, consumption, and wealth.
        </p>
        <div className="process-flow">
          {approach.map((item, idx) => (
            <div key={idx} className="process-step">
              <div className="step-number">{item.step}</div>
              <div className="step-content">
                <h4>{item.title}</h4>
                <p>{item.desc}</p>
              </div>
              {idx < approach.length - 1 && <div className="flow-arrow">→</div>}
            </div>
          ))}
        </div>
        <p className="integration-note">
          <strong>Integration possibility:</strong> Combine PolicyEngine
          microsimulation with general equilibrium models like{" "}
          <a
            href="https://pslmodels.github.io/OG-USA/"
            target="_blank"
            rel="noopener noreferrer"
          >
            OG-USA
          </a>{" "}
          for comprehensive economic-fiscal analysis.
        </p>
      </div>

      {/* Uncertainty Section - Highlight Box */}
      <div className="uncertainty-box">
        <div className="box-content">
          <h3>Quantifying uncertainty</h3>
          <p>
            Traditional policy analysis reports only point estimates (e.g., CBO
            baseline forecasts). AI-driven economic change involves profound
            uncertainty. We'll model ranges of scenarios to show how policy
            impacts vary across different AI trajectories.
          </p>
          <div className="stats-row">
            <div className="stat-item">
              <div className="stat-value">Multiple</div>
              <div className="stat-label">AI Scenarios</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">Probabilistic</div>
              <div className="stat-label">Forecasts</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">Robust</div>
              <div className="stat-label">Policy Analysis</div>
            </div>
          </div>
        </div>
      </div>

      {/* Why This Matters - Impact Grid */}
      <div className="impact-section">
        <h3 className="subsection-title">Why this matters</h3>
        <div className="impact-grid">
          <div className="impact-card">
            <span className="impact-icon"><IconMicroscope size={24} stroke={1.5} /></span>
            <h4>Understand mediation</h4>
            <p>
              How do policies shape AI's distributional impacts on income,
              consumption, wealth?
            </p>
          </div>
          <div className="impact-card">
            <span className="impact-icon"><IconChartBar size={24} stroke={1.5} /></span>
            <h4>Compare interventions</h4>
            <p>
              Contrast how current policies vs. alternatives mediate AI shocks
            </p>
          </div>
          <div className="impact-card">
            <span className="impact-icon"><IconDice size={24} stroke={1.5} /></span>
            <h4>Quantify uncertainty</h4>
            <p>
              Model ranges of AI scenarios and policy responses, not just point
              estimates
            </p>
          </div>
          <div className="impact-card">
            <span className="impact-icon"><IconWorld size={24} stroke={1.5} /></span>
            <h4>Open collaboration</h4>
            <p>
              Transparent microsimulation enables researchers to test their own
              assumptions
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Overview;
