import React from "react";
import "./Ecosystem.css";

function Ecosystem() {
  const categories = [
    {
      title: "Research & academia",
      tagClass: "research",
      orgs: [
        {
          name: "EconTAI Initiative (UVA)",
          desc: "Led by Anton Korinek. Economics of Transformative AI curriculum and research.",
          url: "https://www.econtai.org/",
        },
        {
          name: "Stanford Digital Economy Lab",
          desc: 'Led by Erik Brynjolfsson. "Canaries in the Coal Mine" study, ETAI course.',
          url: "https://digitaleconomy.stanford.edu/",
        },
        {
          name: "MIT Future Tech Lab",
          desc: "Job displacement modeling by skill category. Iceberg Index.",
          url: "https://futuretech.mit.edu/",
        },
        {
          name: "Seth Benzell (Chapman)",
          desc: "17-region OLG CGE model of AI\u2019s global economic impact.",
          url: "https://digitalcommons.chapman.edu/economics_articles/288/",
        },
        {
          name: "Penn Wharton Budget Model",
          desc: "Fiscal and distributional analysis of economic policy proposals.",
          url: "https://budgetmodel.wharton.upenn.edu/",
        },
        {
          name: "Yale Budget Lab",
          desc: "Nonpartisan analysis of fiscal and economic policy.",
          url: "https://budgetlab.yale.edu/",
        },
        {
          name: "Epoch AI",
          desc: "Research on AI trends, compute scaling, and timelines.",
          url: "https://epochai.org/",
        },
        {
          name: "McKinsey Global Institute",
          desc: "Research on technology, labor markets, and economic disruption.",
          url: "https://www.mckinsey.com/mgi",
        },
      ],
    },
    {
      title: "AI companies",
      tagClass: "ai-companies",
      orgs: [
        {
          name: "Anthropic",
          desc: "Economic impact research. Anthropic Economic Index tracking AI on labor.",
          url: "https://www.anthropic.com/",
        },
        {
          name: "OpenAI",
          desc: "AI capabilities research and economic preparedness.",
          url: "https://openai.com/",
        },
        {
          name: "Google DeepMind",
          desc: "AI research with economic applications and safety focus.",
          url: "https://deepmind.google/",
        },
      ],
    },
    {
      title: "Policy & advocacy",
      tagClass: "policy",
      orgs: [
        {
          name: "Windfall Trust",
          desc: "Policy accelerator for the age of AI. Building global dividend fund mechanisms. FLI-funded.",
          url: "https://windfallclause.org/",
        },
        {
          name: "AGI Social Contract",
          desc: "Expert anthology on AI economic governance. Part of Windfall Trust.",
          url: "https://windfallclause.org/agi-social-contract",
        },
        {
          name: "Convergence Analysis",
          desc: "\u201CThreshold 2030\u201D conference modeling AI economic futures through 2030.",
          url: "https://www.convergenceanalysis.org/",
        },
        {
          name: "Brookings",
          desc: "AI tax policy frameworks, labor displacement analysis.",
          url: "https://www.brookings.edu/articles/future-tax-policy-a-public-finance-framework-for-the-age-of-ai/",
        },
        {
          name: "Center for AI Safety",
          desc: "Research and advocacy reducing societal-scale risks from AI.",
          url: "https://www.safe.ai/",
        },
        {
          name: "AI Now Institute",
          desc: "Research on the social implications of AI.",
          url: "https://ainowinstitute.org/",
        },
        {
          name: "Centre for Long-Term Resilience",
          desc: "UK-based policy institute focused on catastrophic and existential risks.",
          url: "https://www.longtermresilience.org/",
        },
      ],
    },
    {
      title: "Models & tools",
      tagClass: "models",
      orgs: [
        {
          name: "PolicyEngine",
          desc: "Open-source microsimulation for US, UK, Canada. This project.",
          url: "https://policyengine.org/us/model",
        },
        {
          name: "OG-USA (DeBacker & Evans)",
          desc: "Open-source overlapping generations model for fiscal policy.",
          url: "https://github.com/PSLmodels/OG-USA",
        },
        {
          name: "Don\u2019t Lose Your Job (Clay Wren)",
          desc: "Task-dependent AI displacement forecasting model.",
          url: "https://dontloseyour.job",
        },
      ],
    },
    {
      title: "Funders & forecasting",
      tagClass: "funders",
      orgs: [
        {
          name: "Open Philanthropy",
          desc: "Major funder of AI safety and economic research.",
          url: "https://www.openphilanthropy.org/",
        },
        {
          name: "Future of Life Institute",
          desc: "Funds Windfall Trust and AI governance work.",
          url: "https://futureoflife.org/",
        },
        {
          name: "EA Funds",
          desc: "Grantmaking across cause areas including AI governance.",
          url: "https://funds.effectivealtruism.org/",
        },
        {
          name: "Good Ventures",
          desc: "Philanthropic foundation partnering with Open Philanthropy.",
          url: "https://www.goodventures.org/",
        },
        {
          name: "Metaculus",
          desc: "Forecasting platform with AGI timeline and labor market questions.",
          url: "https://www.metaculus.com/",
        },
        {
          name: "QURI",
          desc: "Quantified Uncertainty Research Institute. Tools for forecasting and estimation.",
          url: "https://quantifieduncertainty.org/",
        },
      ],
    },
  ];

  return (
    <div id="ecosystem" className="ecosystem-section">
      <div className="section-header">
        <span className="eyebrow">Who's working on this</span>
        <h2>The ecosystem</h2>
      </div>

      {categories.map((category, catIdx) => (
        <div key={catIdx} className="ecosystem-category">
          <h3 className="ecosystem-category-title">{category.title}</h3>
          <div className="ecosystem-org-grid">
            {category.orgs.map((org, orgIdx) => (
              <a
                key={orgIdx}
                href={org.url}
                target="_blank"
                rel="noopener noreferrer"
                className="ecosystem-org-card"
              >
                <div className="ecosystem-org-name">
                  {org.name} <span className="ecosystem-org-arrow">{"\u2192"}</span>
                </div>
                <p className="ecosystem-org-desc">{org.desc}</p>
                <span
                  className={`ecosystem-org-tag ${category.tagClass}`}
                >
                  {category.title}
                </span>
              </a>
            ))}
          </div>
        </div>
      ))}

      <div className="international-box">
        <h3>International expansion</h3>
        <p>
          While initial work focuses on the United States using PolicyEngine-US,
          this framework extends to other countries with existing PolicyEngine models:
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
              <span className="status-tag development">In development</span>
            </div>
          </a>
        </div>
      </div>
    </div>
  );
}

export default Ecosystem;
