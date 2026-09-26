import React from "react";
import { cite } from "../data/references";

const FINDINGS = {
  us: [
    {
      source: "BrynjolfssonChandarandChen2026",
      title: "Young workers in AI-exposed jobs are 19% below trend",
      detail:
        "ADP payroll data through June 2026 put employment of workers aged 22-25 in AI-exposed occupations 19% below where it would be had it kept pace with less-exposed peers. Experienced workers show no comparable gap, and the adjustment runs through hiring rather than pay.",
    },
    {
      source: "Chopraetal2025",
      title: "AI can already perform skills worth 11.7% of US wage value",
      detail:
        "A Large Population Model of 151 million workers, 32,000+ skills, and 3,000 counties. The index measures technical exposure, about $1.2 trillion in wage value, not displacement or adoption timelines. Visible adoption in computing covers only 2.2%.",
    },
    {
      source: "Rockalletal2025",
      title: "AI may narrow wage gaps while widening wealth gaps",
      detail:
        "Unlike earlier automation, AI could reduce wage inequality by displacing high-income workers, but their tasks complement AI and they benefit most from higher capital returns. When firms choose how much AI to adopt, the wealth-inequality effect is strongest.",
    },
    {
      source: "AnthropicEconomicIndex2026",
      title: "Half of jobs now have a quarter of their tasks done with AI",
      detail:
        "Jobs with at least a quarter of their tasks done with Claude rose from 36% (January 2025 data) to 49% pooled across reports. Augmentation (52% of conversations) has overtaken automation (45%).",
    },
    {
      source: "PWBM2025",
      title: "Generative AI projected to boost GDP 1.5% by 2035",
      detail:
        "Generative AI will increase productivity and GDP by 1.5% by 2035 and nearly 3% by 2055. 40% of current GDP could be substantially affected.",
    },
    {
      source: "KorinekandLockwood2026",
      title: "The future of tax policy in the age of AI",
      detail:
        "About three quarters of US federal revenue comes from labor, which AI threatens to erode. Korinek and Lockwood recommend shifting the primary revenue base from labor to consumption; some reforms make sense now, while others would undermine efficiency.",
    },
  ],
  uk: [
    {
      source: "IPPR2024",
      title: "UK GenAI exposure depends heavily on policy choices",
      detail:
        "IPPR estimates 11% of UK tasks are exposed to current generative AI and 59% under deeper integration. Its central second-wave scenario has 4.4 million jobs displaced alongside £144bn in annual GDP gains.",
    },
    {
      source: "DfE2023",
      title:
        "Finance, professional services, education, and London are more exposed",
      detail:
        "The UK government's AI exposure study finds professional occupations, finance and insurance, information and communication, public administration, education, London, and the South East are relatively more exposed to AI and LLM applications.",
    },
    {
      source: "AISkillsProjections2026",
      title: "AI-related UK jobs could grow sharply by 2035",
      detail:
        "The AI Skills for Life and Work projections show jobs directly involving AI activities rising from 158,000 in 2024 to 3.9 million by 2035, with AI occupations projected to grow 12.4% in the adjusted Technological Opportunities scenario.",
    },
    {
      source: "PwC2025",
      title: "AI-exposed UK roles show wage premia but slower vacancy growth",
      detail:
        "PwC reports an 11% UK wage premium for roles requiring AI skills, while vacancies in AI-exposed occupations grew 12% from 2019 to 2024 compared with 50% for less exposed occupations.",
    },
    {
      source: "DSITActionPlan2026",
      title: "UK policy is starting to build the evidence pipeline",
      detail:
        "The government has created a Future of Work Unit to provide evidence on AI's impact on the economy and labour market, and reports more than one million AI courses delivered toward a 10 million worker upskilling goal by 2030.",
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
        {findings.map((finding) => {
          const { label, url, ref } = cite(finding.source);
          return (
            <div key={finding.source} className="evidence-card">
              <span className="evidence-source">
                {label} ({ref.year})
              </span>
              <h3>{finding.title}</h3>
              <p className="evidence-detail">{finding.detail}</p>
              <a
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="evidence-link"
              >
                Read source <span className="evidence-link-arrow">{"→"}</span>
              </a>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default Evidence;
