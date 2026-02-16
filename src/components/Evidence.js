import React from "react";
import "./Evidence.css";

function Evidence() {
  const findings = [
    {
      source: "Stanford DEL (2025)",
      title: "Canaries in the Coal Mine",
      detail:
        "Early-career workers in AI-exposed occupations saw 16% relative employment decline since late 2022. Software developers ages 22-25 saw employment fall 20%.",
      url: "https://digitaleconomy.stanford.edu/publications/canaries-in-the-coal-mine/",
    },
    {
      source: "MIT Iceberg Index (2025)",
      title: "11.7% of the US labor market automatable by AI",
      detail:
        "AI currently capable of automating 11.7% of the US labor market (~$1.2T in wage value). Simulated 151 million workers across 32,000+ skills.",
      url: "https://mitfuturetech.mit.edu/iceberg-index",
    },
    {
      source: "IMF Working Paper (2025)",
      title: "AI may reduce wage inequality but always increases wealth inequality",
      detail:
        "Unlike previous automation, AI could reduce wage inequality (by hitting high-income tasks), but capital income and wealth inequality always increase with AI adoption.",
      url: "https://www.imf.org/en/Publications/WP/Issues/2025/04/04/AI-Adoption-and-Inequality-565729",
    },
    {
      source: "Anthropic Economic Index (2026)",
      title: "AI adoption accelerating across occupations",
      detail:
        "Share of jobs using AI for 25%+ of tasks rose from 36% (Jan 2025) to 49%. 52% augmentation vs. 45% automation. AI delivers largest productivity gains on college-level work.",
      url: "https://www.anthropic.com/economic-index",
    },
    {
      source: "Penn Wharton Budget Model (2025)",
      title: "Generative AI projected to boost GDP 1.5% by 2035",
      detail:
        "Generative AI will increase productivity/GDP by 1.5% by 2035, ~3% by 2055. 40% of current GDP could be substantially affected.",
      url: "https://budgetmodel.wharton.upenn.edu/issues/2025/9/8/projected-impact-of-generative-ai-on-future-productivity-growth",
    },
    {
      source: "Brookings (2026)",
      title: "Future of tax policy in the age of AI",
      detail:
        "AI threatens to erode labor-based tax revenue. Consumption taxation becomes primary instrument as labor income erodes. Some reforms make sense now, others would be premature.",
      url: "https://www.brookings.edu/articles/future-tax-policy-a-public-finance-framework-for-the-age-of-ai/",
    },
  ];

  return (
    <div id="evidence" className="evidence-section">
      <div className="section-header">
        <span className="eyebrow">Key findings (2025-2026)</span>
        <h2>What the research shows</h2>
      </div>

      <div className="evidence-grid">
        {findings.map((finding, idx) => (
          <div key={idx} className="evidence-card">
            <span className="evidence-source">{finding.source}</span>
            <h3>{finding.title}</h3>
            <p className="evidence-detail">{finding.detail}</p>
            <a
              href={finding.url}
              target="_blank"
              rel="noopener noreferrer"
              className="evidence-link"
            >
              Read source{" "}
              <span className="evidence-link-arrow">{"\u2192"}</span>
            </a>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Evidence;
