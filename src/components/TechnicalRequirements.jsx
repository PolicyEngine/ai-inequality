import React from "react";

function TechnicalRequirements() {
  const requirements = [
    {
      category: "AI Economic Scenario Modeling",
      items: [
        "Develop parameterized models of AI-driven GDP growth, productivity gains, and sectoral shifts",
        "Model labor displacement rates by occupation, industry, and skill level",
        "Project changes in capital vs. labor income shares over time",
        "Incorporate uncertainty bounds and sensitivity analysis",
      ],
    },
    {
      category: "Microdata Enhancement",
      items: [
        "Extend PolicyEngine-US microdata with AI exposure indicators by occupation",
        "Integrate wealth data for capital income modeling",
        "Incorporate demographic characteristics relevant to AI impacts (education, age, industry)",
        "Develop reweighting procedures for future population scenarios",
      ],
    },
    {
      category: "PolicyEngine Model Extensions",
      items: [
        "Build modules to apply AI scenario shocks to household incomes",
        "Apply existing policy modeling capabilities (UBI, safety net expansions, tax changes) to AI scenarios",
        "Calculate distributional impacts (Gini, poverty rates, decile shares)",
        "Model behavioral responses (labor supply, savings, program take-up)",
      ],
    },
    {
      category: "Computational Infrastructure",
      items: [
        "Scale PolicyEngine API to handle large scenario comparison matrices",
        "Optimize microsimulation performance for rapid iteration",
        "Develop data pipelines for scenario inputs and results storage",
        "Build visualization tools for multidimensional scenario comparisons",
      ],
    },
    {
      category: "Validation and Calibration",
      items: [
        "Validate model against historical automation events (e.g., manufacturing decline)",
        "Calibrate AI scenario parameters to expert forecasts and empirical trends",
        "Conduct sensitivity analysis across parameter uncertainty ranges",
        "Compare results with other economic models (CGE, agent-based)",
      ],
    },
    {
      category: "Research Partnerships",
      items: [
        "Collaborate with AI forecasting experts (Epoch AI, forecasters)",
        "Engage labor economists and inequality researchers",
        "Partner with policy organizations on reform design",
        "Coordinate with microsimulation modeling community",
      ],
    },
  ];

  return (
    <div id="technical" className="section section-alt">
      <h2>Technical requirements</h2>
      <p
        style={{
          textAlign: "center",
          maxWidth: "800px",
          margin: "0 auto 2rem",
        }}
      >
        Conducting rigorous AI economic growth modeling requires advances in
        scenario design, data infrastructure, modeling capabilities, and
        research collaboration.
      </p>
      {requirements.map((requirement, index) => (
        <div key={index} className="card">
          <h3>{requirement.category}</h3>
          <ul>
            {requirement.items.map((item, itemIndex) => (
              <li key={itemIndex}>{item}</li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

export default TechnicalRequirements;
