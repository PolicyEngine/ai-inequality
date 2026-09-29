import React from "react";
import {
  IconTrendingUp,
  IconBuildingBank,
  IconUsers,
} from "@tabler/icons-react";
import { cite } from "../data/references";

// A citation: the link resolves through the references database.
const Cite = ({ id, children }) => (
  <a
    href={cite(id).url}
    target="_blank"
    rel="noopener noreferrer"
    className="inline-source"
  >
    {children}
  </a>
);

// An organisation's own page, which is not a citation.
const Org = ({ href, children }) => (
  <a
    href={href}
    target="_blank"
    rel="noopener noreferrer"
    className="inline-source inline-org"
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
              <Cite id="PwC2025">PwC's 2025 AI Jobs Barometer</Cite> finds an
              11% UK wage premium for roles requiring AI skills, while vacancies
              in AI-exposed occupations grew more slowly than less exposed roles
              from 2019 to 2024.
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
              while global <Cite id="Rockalletal2025">IMF research</Cite>{" "}
              suggests AI can raise wealth inequality even where it narrows wage
              gaps.
            </>
          ),
        },
        {
          icon: <IconUsers size={28} stroke={1.5} />,
          title: "Labour displacement",
          description: (
            <>
              <Cite id="IPPR2024">IPPR</Cite> estimates 11% of UK tasks are
              exposed to existing generative AI, rising to 59% under deeper
              integration; its adverse scenario has 7.9 million jobs displaced,
              while its augmentation scenario has no net job loss.
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
              <Cite id="BrynjolfssonChandarandChen2026">
                Stanford DEL (2026)
              </Cite>{" "}
              finds employment of workers aged 22-25 in AI-exposed occupations
              19% below where it would be had it kept pace with less-exposed
              peers, with no comparable gap for experienced workers and the
              adjustment running through hiring rather than pay.
            </>
          ),
        },
        {
          icon: <IconBuildingBank size={28} stroke={1.5} />,
          title: "Capital-labor shift",
          description: (
            <>
              As AI raises returns to capital, the labor share of income can
              fall: across European regions, each doubling of AI innovation
              lowers it by{" "}
              <Cite id="MinnitiPrettnerandVenturini2025">
                0.5-1.6%, or 0.09-0.31 percentage points from a 52% average
              </Cite>
              . The <Cite id="Rockalletal2025">IMF (2025)</Cite> finds AI could
              narrow wage inequality by displacing high-income workers, but
              those workers gain most from higher capital returns, so wealth
              inequality rises most when firms choose how much AI to adopt.
            </>
          ),
        },
        {
          icon: <IconUsers size={28} stroke={1.5} />,
          title: "Labor displacement",
          description: (
            <>
              The <Cite id="Chopraetal2025">Iceberg Index</Cite> finds AI
              systems can already perform skills worth 11.7% of US wage value,
              about $1.2 trillion. It measures technical exposure, not
              displacement or adoption timelines, and visible adoption in
              computing covers only 2.2%.
            </>
          ),
        },
      ];
  const callout = isUK ? (
    <>
      UK-specific research is thinner than the US evidence base. The
      government's <Cite id="DSITActionPlan2026">Future of Work Unit</Cite> is
      explicitly being built to improve evidence on AI's labour-market effects;
      this prototype shows how that evidence can be translated into
      distributional policy analysis.
    </>
  ) : (
    <>
      Current policy scoring institutions like{" "}
      <Org href="https://www.cbo.gov/">CBO</Org> operate under a single baseline
      economic scenario. AI amplifies the need for{" "}
      <Cite id="BrynjolfssonKorinekAgrawal2025">
        probabilistic policy analysis
      </Cite>{" "}
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
        {mechanisms.map((item) => (
          <div key={item.title} className="mechanism-card">
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
