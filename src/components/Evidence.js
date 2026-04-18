import React from "react";
import "./Evidence.css";

const FINDINGS = {
  us: [
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
      title:
        "AI may reduce wage inequality but always increases wealth inequality",
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
  ],
  uk: [
    {
      source: "IPPR (2024)",
      title: "UK GenAI exposure depends heavily on policy choices",
      detail:
        "IPPR estimates 11% of UK tasks are exposed to current generative AI and 59% under deeper integration. Its central second-wave scenario has 4.4 million jobs displaced alongside £144bn in annual GDP gains.",
      url: "https://www.ippr.org/media-office/up-to-8-million-uk-jobs-at-risk-from-ai-unless-government-acts-finds-ippr",
    },
    {
      source: "GOV.UK / DfE (2023)",
      title:
        "Finance, professional services, education, and London are more exposed",
      detail:
        "The UK government's AI exposure study finds professional occupations, finance and insurance, information and communication, public administration, education, London, and the South East are relatively more exposed to AI and LLM applications.",
      url: "https://assets.publishing.service.gov.uk/media/656856b8cc1ec500138eef49/Gov.UK_Impact_of_AI_on_UK_Jobs_and_Training.pdf",
    },
    {
      source: "GOV.UK AI skills projections (2026)",
      title: "AI-related UK jobs could grow sharply by 2035",
      detail:
        "The AI Skills for Life and Work projections show jobs directly involving AI activities rising from 158,000 in 2024 to 3.9 million by 2035, with AI occupations projected to grow 12.4% in the adjusted Technological Opportunities scenario.",
      url: "https://www.gov.uk/government/publications/ai-skills-for-life-and-work-labour-market-and-skills-projections/ai-skills-for-life-and-work-labour-market-and-skills-projections",
    },
    {
      source: "PwC UK (2025)",
      title: "AI-exposed UK roles show wage premia but slower vacancy growth",
      detail:
        "PwC reports an 11% UK wage premium for roles requiring AI skills, while vacancies in AI-exposed occupations grew 12% from 2019 to 2024 compared with 50% for less exposed occupations.",
      url: "https://www.pwc.co.uk/press-room/press-releases/research-commentary/2024/ai-exposed-sectors-see-pay-and-productivity-uplift--but-job-open.html",
    },
    {
      source: "GOV.UK AI Opportunities Action Plan (2026)",
      title: "UK policy is starting to build the evidence pipeline",
      detail:
        "The government has created a Future of Work Unit to provide evidence on AI's impact on the economy and labour market, and reports more than one million AI courses delivered toward a 10 million worker upskilling goal by 2030.",
      url: "https://www.gov.uk/government/publications/ai-opportunities-action-plan-one-year-on/ai-opportunities-action-plan-one-year-on",
    },
  ],
};

function Evidence({ countryKey = "us" }) {
  const findings = FINDINGS[countryKey] ?? FINDINGS.us;
  const eyebrow =
    countryKey === "uk"
      ? "UK evidence and transferable research"
      : "Key findings (2025-2026)";

  return (
    <div id="evidence" className="evidence-section">
      <div className="section-header">
        <span className="eyebrow">{eyebrow}</span>
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
