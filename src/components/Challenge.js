import React from "react";
import "./Challenge.css";
import {
  IconTrendingUp,
  IconBuildingBank,
  IconUsers,
} from "@tabler/icons-react";

const Source = ({ href, children }) => (
  <a
    href={href}
    target="_blank"
    rel="noopener noreferrer"
    className="inline-source"
  >
    {children}
  </a>
);

function Challenge({ countryKey = "us" }) {
  const isUK = countryKey === "uk";
  const mechanisms = isUK
    ? [
        {
          icon: <IconTrendingUp size={28} stroke={1.5} />,
          title: "Wage inequality",
          description: (
            <>
              UK evidence is still emerging, but{" "}
              <Source href="https://www.pwc.co.uk/press-room/press-releases/research-commentary/2024/ai-exposed-sectors-see-pay-and-productivity-uplift--but-job-open.html">
                PwC's 2025 AI Jobs Barometer
              </Source>{" "}
              finds an 11% UK wage premium for roles requiring AI skills, while
              vacancies in AI-exposed occupations grew more slowly than less
              exposed roles from 2019 to 2024.
            </>
          ),
        },
        {
          icon: <IconBuildingBank size={28} stroke={1.5} />,
          title: "Capital-labour shift",
          description: (
            <>
              We do not yet have a strong UK-specific forecast for AI shifting
              income from labour to capital. The prototype therefore
              stress-tests that mechanism directly in the UK tax-benefit system,
              while global{" "}
              <Source href="https://www.imf.org/en/Publications/WP/Issues/2025/04/04/AI-Adoption-and-Inequality-565729">
                IMF research
              </Source>{" "}
              suggests AI adoption can raise capital-income and wealth
              inequality.
            </>
          ),
        },
        {
          icon: <IconUsers size={28} stroke={1.5} />,
          title: "Labour displacement",
          description: (
            <>
              <Source href="https://www.ippr.org/media-office/up-to-8-million-uk-jobs-at-risk-from-ai-unless-government-acts-finds-ippr">
                IPPR
              </Source>{" "}
              estimates 11% of UK tasks are exposed to existing generative AI,
              rising to 59% under deeper integration; its adverse scenario has
              7.9 million jobs displaced, while its augmentation scenario has no
              net job loss.
            </>
          ),
        },
      ]
    : [
        {
          icon: <IconTrendingUp size={28} stroke={1.5} />,
          title: "Wage inequality",
          description: (
            <>
              AI may widen or narrow wage gaps depending on which tasks are
              complemented vs. automated.{" "}
              <Source href="https://digitaleconomy.stanford.edu/publications/canaries-in-the-coal-mine/">
                Stanford DEL (2025)
              </Source>{" "}
              finds early-career workers in AI-exposed jobs saw a 16% employment
              decline, while senior workers gained 6-12%.
            </>
          ),
        },
        {
          icon: <IconBuildingBank size={28} stroke={1.5} />,
          title: "Capital-labor shift",
          description: (
            <>
              As AI increases returns to capital, the labor share of income
              could decline{" "}
              <Source href="https://www.nber.org/papers/w28453">
                0.5-1.6 percentage points per doubling of AI innovation
              </Source>
              . The{" "}
              <Source href="https://www.imf.org/en/Publications/WP/Issues/2025/04/04/AI-Adoption-and-Inequality-565729">
                IMF (2025)
              </Source>{" "}
              finds capital income and wealth inequality always increase with AI
              adoption.
            </>
          ),
        },
        {
          icon: <IconUsers size={28} stroke={1.5} />,
          title: "Labor displacement",
          description: (
            <>
              <Source href="https://futuretech.mit.edu/research">
                MIT's Iceberg Index
              </Source>{" "}
              estimates AI can currently automate 11.7% of the US labor market
              (~$1.2 trillion in wage value).{" "}
              <Source href="https://www.metaculus.com/questions/">
                Metaculus forecasters
              </Source>{" "}
              project labor force participation dropping from 83.5% to 78% by
              2030.
            </>
          ),
        },
      ];
  const callout = isUK ? (
    <>
      UK-specific research is thinner than the US evidence base. The
      government's{" "}
      <Source href="https://www.gov.uk/government/publications/ai-opportunities-action-plan-one-year-on/ai-opportunities-action-plan-one-year-on">
        Future of Work Unit
      </Source>{" "}
      is explicitly being built to improve evidence on AI's labour-market
      effects; this prototype shows how that evidence can be translated into
      distributional policy analysis.
    </>
  ) : (
    <>
      Current policy scoring institutions like{" "}
      <Source href="https://www.cbo.gov/">CBO</Source> operate under a single
      baseline economic scenario. AI amplifies the need for{" "}
      <Source href="https://www.nber.org/papers/w34256">
        probabilistic policy analysis
      </Source>{" "}
      across multiple growth trajectories.
    </>
  );

  return (
    <div className="challenge-section">
      <div className="section-header">
        <span className="eyebrow">Why this matters</span>
        <h2>The challenge</h2>
        <p className="section-intro">
          AI could reshape market incomes through three mechanisms, each
          creating profound uncertainty:
        </p>
      </div>

      <div className="challenge-cards">
        {mechanisms.map((item, idx) => (
          <div key={idx} className="mechanism-card">
            <div className="mechanism-icon">{item.icon}</div>
            <h3>{item.title}</h3>
            <p>{item.description}</p>
          </div>
        ))}
      </div>

      <div className="challenge-callout">
        <p>{callout}</p>
      </div>
    </div>
  );
}

export default Challenge;
