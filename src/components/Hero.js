import React from "react";
import "./Hero.css";

function Hero() {
  const stats = [
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
  ];

  return (
    <div className="hero">
      <div className="hero-content">
        <h1>
          How will policy shape{" "}
          <span className="highlight">AI's impact on inequality?</span>
        </h1>
        <p className="hero-subtitle">
          PolicyEngine provides open-source microsimulation infrastructure to
          analyze how tax and benefit policies mediate AI-driven economic
          change — from wage shifts to capital concentration to labor
          displacement.
        </p>
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
