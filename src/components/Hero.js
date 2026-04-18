import React from "react";
import "./Hero.css";

const HERO_CONTENT = {
  us: {
    subtitle:
      "PolicyEngine provides open-source microsimulation infrastructure to analyze how tax and benefit policies mediate AI-driven economic change — from wage shifts to capital concentration to labor displacement.",
    stats: [
      {
        value: "11.7%",
        label: "of US labor market automatable today",
        source: "MIT Iceberg Index",
        url: "https://futuretech.mit.edu/research",
      },
      {
        value: "16%",
        label: "decline in early-career tech employment",
        source: "Stanford DEL 2025",
        url: "https://digitaleconomy.stanford.edu/publications/canaries-in-the-coal-mine/",
      },
      {
        value: "$1.2T",
        label: "in wage value at stake",
        source: "MIT Iceberg Index",
        url: "https://futuretech.mit.edu/research",
      },
    ],
  },
  uk: {
    subtitle:
      "PolicyEngine provides open-source microsimulation infrastructure to analyse how UK tax and benefit policy mediates AI-driven economic change — from wage shifts to capital concentration to labour displacement.",
    stats: [
      {
        value: "59%",
        label: "of UK work tasks exposed in deeper GenAI adoption",
        source: "IPPR",
        url: "https://www.ippr.org/media-office/up-to-8-million-uk-jobs-at-risk-from-ai-unless-government-acts-finds-ippr",
      },
      {
        value: "£144bn",
        label: "annual GDP gain in IPPR's central second-wave scenario",
        source: "IPPR",
        url: "https://www.ippr.org/media-office/up-to-8-million-uk-jobs-at-risk-from-ai-unless-government-acts-finds-ippr",
      },
      {
        value: "3.9m",
        label: "UK jobs directly involving AI activities by 2035",
        source: "GOV.UK AI skills projections",
        url: "https://www.gov.uk/government/publications/ai-skills-for-life-and-work-labour-market-and-skills-projections/ai-skills-for-life-and-work-labour-market-and-skills-projections",
      },
    ],
  },
};

function Hero({ countryKey = "us" }) {
  const content = HERO_CONTENT[countryKey] ?? HERO_CONTENT.us;
  const stats = content.stats;

  return (
    <div className="hero">
      <div className="hero-content">
        <h1>
          How will policy shape{" "}
          <span className="highlight">AI's impact on inequality?</span>
        </h1>
        <p className="hero-subtitle">{content.subtitle}</p>
        <div className="hero-cta">
          <a href="#evidence" className="cta-button primary">
            Explore the research
          </a>
          <a href="#get-involved" className="cta-button outline">
            Get involved
          </a>
        </div>
      </div>

      <div className="hero-stats">
        {stats.map((stat, idx) => (
          <a
            key={idx}
            href={stat.url}
            target="_blank"
            rel="noopener noreferrer"
            className="stat-box"
          >
            <div className="stat-value">{stat.value}</div>
            <div className="stat-label">{stat.label}</div>
            <div className="stat-source">{stat.source} →</div>
          </a>
        ))}
      </div>
    </div>
  );
}

export default Hero;
