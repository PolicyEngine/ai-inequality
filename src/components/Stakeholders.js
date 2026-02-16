import React, { useState } from "react";
import "./Stakeholders.css";
import {
  IconMicroscope,
  IconRobot,
  IconShield,
  IconCoin,
  IconTrendingUp,
  IconSchool,
  IconChartBar,
  IconWorld,
} from "@tabler/icons-react";

function Stakeholders() {
  const [selectedCategory, setSelectedCategory] = useState("all");

  const stakeholders = [
    { name: "Epoch AI", category: "AI Research", url: "https://epochai.org/" },
    {
      name: "Anthropic",
      category: "AI Companies",
      url: "https://www.anthropic.com/",
    },
    { name: "OpenAI", category: "AI Companies", url: "https://openai.com/" },
    {
      name: "Google DeepMind",
      category: "AI Companies",
      url: "https://deepmind.google/",
    },
    {
      name: "Future of Life Institute",
      category: "AI Safety & Policy",
      url: "https://futureoflife.org/",
    },
    {
      name: "Open Philanthropy",
      category: "Funders",
      url: "https://www.openphilanthropy.org/",
    },
    {
      name: "Metaculus",
      category: "Forecasting",
      url: "https://www.metaculus.com/",
    },
    {
      name: "Center for AI Safety",
      category: "AI Safety & Policy",
      url: "https://www.safe.ai/",
    },
    {
      name: "AI Now Institute",
      category: "AI Safety & Policy",
      url: "https://ainowinstitute.org/",
    },
    {
      name: "Centre for Long-Term Resilience",
      category: "AI Safety & Policy",
      url: "https://www.longtermresilience.org/",
    },
    {
      name: "Good Ventures",
      category: "Funders",
      url: "https://www.goodventures.org/",
    },
    {
      name: "Jaan Tallinn Philanthropies",
      category: "Funders",
      url: "https://survivalandflourishing.fund/",
    },
    {
      name: "AI Objectives Institute",
      category: "AI Safety & Policy",
      url: "https://ai-objectives.org/",
    },
    {
      name: "Future Search",
      category: "Forecasting",
      url: "https://futuresearch.ai/",
    },
    {
      name: "QURI",
      category: "Forecasting",
      url: "https://quantifieduncertainty.org/",
    },
    {
      name: "Penn Wharton Budget Model",
      category: "Academic Research",
      url: "https://budgetmodel.wharton.upenn.edu/",
    },
    {
      name: "Yale Budget Lab",
      category: "Academic Research",
      url: "https://budgetlab.yale.edu/",
    },
    {
      name: "MIT Sloan",
      category: "Academic Research",
      url: "https://mitsloan.mit.edu/",
    },
    {
      name: "Brookings Institution",
      category: "Academic Research",
      url: "https://www.brookings.edu/",
    },
    {
      name: "Center for Global Development",
      category: "Academic Research",
      url: "https://www.cgdev.org/",
    },
    {
      name: "McKinsey Global Institute",
      category: "Industry Research",
      url: "https://www.mckinsey.com/mgi",
    },
  ];

  const categoryIcons = {
    "AI Research": <IconMicroscope size={16} stroke={1.5} />,
    "AI Companies": <IconRobot size={16} stroke={1.5} />,
    "AI Safety & Policy": <IconShield size={16} stroke={1.5} />,
    Funders: <IconCoin size={16} stroke={1.5} />,
    Forecasting: <IconTrendingUp size={16} stroke={1.5} />,
    "Academic Research": <IconSchool size={16} stroke={1.5} />,
    "Industry Research": <IconChartBar size={16} stroke={1.5} />,
  };

  // WCAG AA compliant colors (4.5:1 contrast ratio on white)
  const categoryColors = {
    "AI Research": "#7c3aed", // violet-600
    "AI Companies": "#2c7a7b", // teal-700
    "AI Safety & Policy": "#0369a1", // sky-700
    Funders: "#b45309", // amber-700
    Forecasting: "#be185d", // pink-700
    "Academic Research": "#047857", // emerald-700
    "Industry Research": "#4338ca", // indigo-700
  };

  const filteredStakeholders =
    selectedCategory === "all"
      ? stakeholders
      : stakeholders.filter((s) => s.category === selectedCategory);

  return (
    <div id="stakeholders" className="stakeholders-section">
      <div className="section-header">
        <h2>Potential stakeholders</h2>
        <p className="section-subtitle">
          Organizations that might be interested in supporting or collaborating
          on this research
        </p>
      </div>

      <div className="category-filter">
        <button
          className={`filter-btn ${selectedCategory === "all" ? "active" : ""}`}
          onClick={() => setSelectedCategory("all")}
        >
          All Organizations
        </button>
        {Object.keys(categoryIcons).map((category) => (
          <button
            key={category}
            className={`filter-btn ${selectedCategory === category ? "active" : ""}`}
            onClick={() => setSelectedCategory(category)}
            style={{
              borderColor:
                selectedCategory === category
                  ? categoryColors[category]
                  : "#e2e8f0",
              color:
                selectedCategory === category
                  ? categoryColors[category]
                  : "#64748b",
            }}
          >
            <span className="filter-icon">{categoryIcons[category]}</span>
            {category}
          </button>
        ))}
      </div>

      <div className="stakeholders-grid">
        {filteredStakeholders.map((stakeholder, idx) => (
          <a
            key={idx}
            href={stakeholder.url}
            target="_blank"
            rel="noopener noreferrer"
            className="stakeholder-badge"
            style={{ borderLeftColor: categoryColors[stakeholder.category] }}
          >
            <div className="badge-content">
              <div className="badge-name">{stakeholder.name}</div>
              <div
                className="badge-category"
                style={{ color: categoryColors[stakeholder.category] }}
              >
                {stakeholder.category}
              </div>
            </div>
            <span className="badge-arrow">→</span>
          </a>
        ))}
      </div>

      <div className="international-box">
        <div className="box-header">
          <span className="box-icon"><IconWorld size={24} stroke={1.5} /></span>
          <h3>International expansion</h3>
        </div>
        <p>
          While initial work would focus on the United States using
          PolicyEngine-US, this framework could be expanded to other countries:
        </p>
        <div className="country-grid">
          <a
            href="https://policyengine.org/us"
            target="_blank"
            rel="noopener noreferrer"
            className="country-card"
          >
            <span className="country-flag">US</span>
            <div>
              <strong>United States</strong>
              <span className="status-tag operational">Operational</span>
            </div>
          </a>
          <a
            href="https://policyengine.org/uk"
            target="_blank"
            rel="noopener noreferrer"
            className="country-card"
          >
            <span className="country-flag">UK</span>
            <div>
              <strong>United Kingdom</strong>
              <span className="status-tag operational">Operational</span>
            </div>
          </a>
          <a
            href="https://policyengine.org/ca"
            target="_blank"
            rel="noopener noreferrer"
            className="country-card"
          >
            <span className="country-flag">CA</span>
            <div>
              <strong>Canada</strong>
              <span className="status-tag development">In Development</span>
            </div>
          </a>
        </div>
      </div>
    </div>
  );
}

export default Stakeholders;
