import React from "react";
import { cite } from "../data/references";

const HERO_CONTENT = {
  us: {
    subtitle:
      "PolicyEngine provides open-source microsimulation infrastructure to analyze how tax and benefit policies mediate AI-driven economic change — from wage shifts to capital concentration to labor displacement.",
    stats: [
      {
        value: "11.7%",
        label: "of US wage value is in skills AI can already perform",
        source: "Chopraetal2025",
      },
      {
        value: "19%",
        label: "employment gap for workers aged 22-25 in AI-exposed jobs",
        source: "BrynjolfssonChandarandChen2026",
      },
      {
        value: "49%",
        label:
          "of jobs have at least a quarter of their tasks done with Claude",
        source: "AnthropicEconomicIndex2026",
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
        source: "IPPR2024",
      },
      {
        value: "£144bn",
        label: "annual GDP gain in IPPR's central second-wave scenario",
        source: "IPPR2024",
      },
      {
        value: "3.9m",
        label: "UK jobs directly involving AI activities by 2035",
        source: "AISkillsProjections2026",
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
        {stats.map((stat) => {
          const { label, url } = cite(stat.source);
          return (
            <a
              key={`${stat.source}-${stat.value}`}
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="hero-stat"
            >
              <div className="hero-stat-value">{stat.value}</div>
              <div className="hero-stat-label">{stat.label}</div>
              <div className="hero-stat-source">{label} →</div>
            </a>
          );
        })}
      </div>
    </div>
  );
}

export default Hero;
