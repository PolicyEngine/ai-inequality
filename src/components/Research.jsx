import React, { useState } from "react";

function Research() {
  const [expandedCard, setExpandedCard] = useState(null);
  const researchTopics = [
    {
      title: "AI and Labor Market Impacts",
      description:
        "Fundamental disagreement over AI's labor impact: Autor (2024) argues AI can elevate middle-skill workers by extending expertise, while Liu et al. (2025) find AI reverses historical patterns, favoring low-education jobs and displacing high-skill workers. This uncertainty underscores the importance of policy analysis regardless of which scenario unfolds. Federal agencies (BLS, Fed) now incorporating AI in projections.",
      links: [
        {
          text: "Autor: Applying AI to Rebuild Middle Class Jobs (2024)",
          url: "https://www.nber.org/papers/w32140",
        },
        {
          text: "Liu et al: Technology and Labor Markets - Two Centuries (2025)",
          url: "https://www.brookings.edu/wp-content/uploads/2025/09/4_Liu-et-al_unembargoed.pdf",
        },
        {
          text: "Autor & Thompson: Expertise (2025)",
          url: "https://www.nber.org/papers/w33941",
        },
        {
          text: "Yale Budget Lab: AI Labor Market Impact (2025)",
          url: "https://budgetlab.yale.edu/research/evaluating-impact-ai-labor-market-current-state-affairs",
        },
        {
          text: "St. Louis Fed: AI Contributing to Unemployment? (2025)",
          url: "https://www.stlouisfed.org/on-the-economy/2025/aug/is-ai-contributing-unemployment-evidence-occupational-variation",
        },
        {
          text: "BLS: Incorporating AI in Employment Projections (2025)",
          url: "https://www.bls.gov/opub/mlr/2025/article/incorporating-ai-impacts-in-bls-employment-projections.htm",
        },
        {
          text: "Acemoglu: The Simple Macroeconomics of AI (2024)",
          url: "https://www.nber.org/papers/w32487",
        },
        {
          text: "Eloundou et al: GPTs are GPTs (2024)",
          url: "https://www.science.org/doi/10.1126/science.adj0998",
        },
      ],
    },
    {
      title: "AI Productivity & Growth Modeling",
      description:
        "Penn Wharton estimates 0.01pp TFP boost in 2025. McKinsey sizes opportunity at $4.4T in productivity. IMF projects AI affects 40% of jobs globally. Research examines explosive growth scenarios, capital deepening in AI R&D, and compute scaling impacts.",
      links: [
        {
          text: "Penn Wharton: Projected AI Impact on Productivity (2025)",
          url: "https://budgetmodel.wharton.upenn.edu/issues/2025/9/8/projected-impact-of-generative-ai-on-future-productivity-growth",
        },
        {
          text: "McKinsey: Superagency in the Workplace (2025)",
          url: "https://www.mckinsey.com/capabilities/mckinsey-digital/our-insights/superagency-in-the-workplace-empowering-people-to-unlock-ais-full-potential-at-work",
        },
        {
          text: "IMF: AI Transform Global Economy (2024)",
          url: "https://www.imf.org/en/Blogs/Articles/2024/01/14/ai-will-transform-the-global-economy-lets-make-sure-it-benefits-humanity",
        },
        {
          text: "Erdil & Besiroglu: Explosive Growth from AI Automation (2023)",
          url: "https://arxiv.org/abs/2309.11690",
        },
        {
          text: "Besiroglu, Emery-Xu & Thompson: Economic Impacts of AI-Augmented R&D (2024)",
          url: "https://www.sciencedirect.com/science/article/pii/S0048733324000866",
        },
        {
          text: "Thompson, Ge & Manso: The Importance of (Exponentially More) Computing Power (2022)",
          url: "https://arxiv.org/abs/2206.14007",
        },
      ],
    },
    {
      title: "AI Inequality & Distribution",
      description:
        "IMF finds AI reduces wage inequality but substantially increases wealth inequality through capital returns. New research shows AI may widen global inequality, with high-income countries better positioned despite higher labor displacement. PNAS Nexus: AI exposure predicts unemployment risk with 18% additional variation explained.",
      links: [
        {
          text: "IMF: AI Adoption and Inequality (2025)",
          url: "https://www.imf.org/en/Publications/WP/Issues/2025/04/04/AI-Adoption-and-Inequality-565729",
        },
        {
          text: "IMF: The Global Impact of AI (2025)",
          url: "https://www.imf.org/-/media/files/publications/wp/2025/english/wpiea2025076-print-pdf.pdf",
        },
        {
          text: "PNAS Nexus: AI Exposure Predicts Unemployment Risk (2025)",
          url: "https://academic.oup.com/pnasnexus/article/4/4/pgaf107/8104152",
        },
        {
          text: "EPJ Data Science: AI and Economic Divide in US (2025)",
          url: "https://epjdatascience.springeropen.com/articles/10.1140/epjds/s13688-025-00547-9",
        },
        {
          text: "CGDev: Three Reasons AI May Widen Global Inequality",
          url: "https://www.cgdev.org/blog/three-reasons-why-ai-may-widen-global-inequality",
        },
        {
          text: "Brookings: AI Impact on Income Inequality",
          url: "https://www.brookings.edu/articles/ais-impact-on-income-inequality-in-the-us/",
        },
        {
          text: "Anthropic: Economic Index Report (Sept 2025)",
          url: "https://www.anthropic.com/research/anthropic-economic-index-september-2025-report",
        },
      ],
    },
    {
      title: "Capital, Labor & AI: The Piketty Debate",
      description:
        "Trammell & Patel (Dec 2025) argue AI will make capital fully substitute for labor, causing Piketty-style inequality spirals—proposing progressive capital taxes. Thompson counters that abundance benefits all and humans prefer humans. Zvi accepts premises but questions whether property rights survive superintelligence.",
      links: [
        {
          text: "Trammell & Patel: Capital in the 22nd Century (2025)",
          url: "https://philiptrammell.substack.com/p/capital-in-the-22nd-century",
        },
        {
          text: "Thompson/Stratechery: AI and the Human Condition (2026)",
          url: "https://stratechery.com/2026/ai-and-the-human-condition/",
        },
        {
          text: "Mowshowitz: Dos Capital (2026)",
          url: "https://thezvi.substack.com/p/dos-capital",
        },
        {
          text: "Trammell & Korinek: Economic Growth under Transformative AI",
          url: "https://www.nber.org/papers/w31815",
        },
        {
          text: "Piketty: Capital in the Twenty-First Century",
          url: "https://www.hup.harvard.edu/books/9780674430006",
        },
      ],
    },
    {
      title: "UBI & Automation Tax Modeling",
      description:
        "CMU research shows AI needs 5-6x productivity for 11% GDP UBI. RAND recommends asymmetric automation policy: incentivize vertical automation while moderating horizontal expansion. Proposals include robot taxes, sovereign AI wealth funds, and AI capital taxation.",
      links: [
        {
          text: "RAND: Managing AI's Economic Future (2025)",
          url: "https://www.rand.org/pubs/research_reports/RRA3764-1.html",
        },
        {
          text: "First Movers: Robot Tax Funding UBI",
          url: "https://firstmovers.ai/universal-basic-income-automation/",
        },
        {
          text: "AI Competence: Tax AI, Not Workers",
          url: "https://aicompetence.org/tax-ai-not-workers-funding-ubi-in-agi-economy/",
        },
        {
          text: "Tax Project Institute: UBI and AI",
          url: "https://taxproject.org/ubi-and-ai/",
        },
      ],
    },
    {
      title: "Microsimulation Modeling",
      description:
        "Techniques for analyzing distributional impacts of tax-benefit policies under economic scenarios. PolicyEngine leading open-source approach.",
      links: [
        {
          text: "PolicyEngine US Model",
          url: "https://policyengine.org/us/model",
        },
        {
          text: "Tax Policy Center: Microsimulation Introduction",
          url: "https://www.taxpolicycenter.org/resources/brief-introduction-microsimulation",
        },
      ],
    },
    {
      title: "Dynamic OLG & General Equilibrium Models",
      description:
        "Overlapping generations models capturing intergenerational effects and capital accumulation dynamics under AI. IMF and Penn Wharton using for automation analysis.",
      links: [
        {
          text: "IMF: Automation and Welfare (OLG) (2024)",
          url: "https://www.imf.org/-/media/Files/Publications/WP/2024/English/wpiea2024011-print-pdf.ashx",
        },
        {
          text: "Penn Wharton: Dynamic OLG Model",
          url: "https://budgetmodel.wharton.upenn.edu/dynamic-olg",
        },
        {
          text: "OG-USA: Open-Source OLG Model",
          url: "https://pslmodels.github.io/OG-USA/",
        },
      ],
    },
    {
      title: "Stochastic Economic Forecasting",
      description:
        "Probabilistic forecasts and joint distribution modeling for economic variables. Critical for microsimulation under uncertainty. See detailed analysis below.",
      links: [
        {
          text: "Philadelphia Fed: Survey of Professional Forecasters",
          url: "https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/survey-of-professional-forecasters",
        },
        {
          text: "CBO: Economic Uncertainty Analysis (Bayesian VAR)",
          url: "https://www.cbo.gov/publication/58883",
        },
        {
          text: "NY Fed: Outlook-at-Risk (Quantile VAR)",
          url: "https://www.newyorkfed.org/research/policy/outlook-at-risk",
        },
        {
          text: "↓ See PolicyEngine's Stochastic Forecasting Approach Below",
          url: "#stochastic-forecasting",
        },
      ],
    },
  ];

  return (
    <div id="research" className="section section-alt">
      <h2>Relevant research</h2>
      <p
        style={{
          textAlign: "center",
          maxWidth: "800px",
          margin: "0 auto 2rem",
        }}
      >
        Our work builds on emerging research at the intersection of AI
        economics, labor markets, inequality, and public policy. Key areas
        include:
      </p>
      <div className="grid">
        {researchTopics.map((topic, index) => (
          <div
            key={index}
            className={`card ${expandedCard === index ? "expanded" : ""}`}
            onClick={() =>
              setExpandedCard(expandedCard === index ? null : index)
            }
            style={{ cursor: "pointer" }}
          >
            <h3
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              {topic.title}
              <span style={{ fontSize: "1.2rem", color: "#319795" }}>
                {expandedCard === index ? "−" : "+"}
              </span>
            </h3>
            <p>{topic.description}</p>
            {expandedCard === index && (
              <ul style={{ marginTop: "1rem" }}>
                {topic.links.map((link, linkIndex) => (
                  <li key={linkIndex}>
                    <a
                      href={link.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {link.text}
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default Research;
