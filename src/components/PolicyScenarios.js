import React from "react";
import "./PolicyScenarios.css";
import {
  IconClipboardList,
  IconCash,
  IconShield,
  IconBuildingBank,
  IconArrowsShuffle,
  IconChartBar,
} from "@tabler/icons-react";

function PolicyScenarios() {
  const scenarios = [
    {
      title: "Current policy baseline",
      icon: <IconClipboardList size={28} stroke={1.5} />,
      color: "#64748b",
      highlights: [
        "Existing tax systems",
        "Current safety nets",
        "State variations",
      ],
      areas: ["Progressive taxation", "EITC & CTC", "Automatic stabilizers"],
    },
    {
      title: "Universal basic income",
      icon: <IconCash size={28} stroke={1.5} />,
      color: "#319795",
      highlights: [
        "Unconditional transfers",
        "Multiple funding models",
        "Program interactions",
      ],
      areas: [
        "Benefit levels",
        "VAT/carbon/capital taxation",
        "Work incentive effects",
      ],
    },
    {
      title: "Expanded safety net",
      icon: <IconShield size={28} stroke={1.5} />,
      color: "#0ea5e9",
      highlights: ["Enhanced programs", "Job transitions", "Family support"],
      areas: ["UI & wage subsidies", "SNAP & housing", "Child allowances"],
    },
    {
      title: "Capital taxation",
      icon: <IconBuildingBank size={28} stroke={1.5} />,
      color: "#8b5cf6",
      highlights: [
        "Target capital income",
        "Wealth concentration",
        "Revenue recycling",
      ],
      areas: ["Capital gains rates", "Wealth taxes", "Automation taxes"],
    },
    {
      title: "Hybrid approaches",
      icon: <IconArrowsShuffle size={28} stroke={1.5} />,
      color: "#f59e0b",
      highlights: [
        "Combined policies",
        "Regional flexibility",
        "Adaptive scaling",
      ],
      areas: [
        "Partial UBI + programs",
        "Progressive wealth tax",
        "Federal minimums",
      ],
    },
  ];

  return (
    <div id="scenarios" className="policy-section">
      <div className="section-header">
        <h2>Alternative policy interventions</h2>
        <p className="section-subtitle">
          How would different policy responses mediate AI's distributional
          impacts?
        </p>
      </div>

      <div className="scenarios-grid">
        {scenarios.map((scenario, idx) => (
          <div
            key={idx}
            className="scenario-card"
            style={{ borderTopColor: scenario.color }}
          >
            <div className="scenario-header">
              <span className="scenario-icon">{scenario.icon}</span>
              <h3 style={{ color: scenario.color }}>{scenario.title}</h3>
            </div>

            <div className="scenario-highlights">
              {scenario.highlights.map((highlight, i) => (
                <span
                  key={i}
                  className="highlight-tag"
                  style={{ borderColor: scenario.color, color: scenario.color }}
                >
                  {highlight}
                </span>
              ))}
            </div>

            <div className="scenario-areas">
              {scenario.areas.map((area, i) => (
                <div key={i} className="area-item">
                  <span
                    className="area-bullet"
                    style={{ backgroundColor: scenario.color }}
                  >
                    •
                  </span>
                  {area}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="analysis-note">
        <div className="note-icon"><IconChartBar size={24} stroke={1.5} /></div>
        <div className="note-content">
          <h4>Comparative distributional analysis</h4>
          <p>
            For each policy intervention, we'll analyze how it mediates AI
            shocks—examining impacts on income, consumption, and wealth
            distribution, poverty, work incentives, and fiscal sustainability.
            This helps reveal how different policies shape distributional
            outcomes under economic uncertainty.
          </p>
        </div>
      </div>
    </div>
  );
}

export default PolicyScenarios;
