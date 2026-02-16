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

function Challenge() {
  const mechanisms = [
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
          As AI increases returns to capital, the labor share of income could
          decline{" "}
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
          project labor force participation dropping from 83.5% to 78% by 2030.
        </>
      ),
    },
  ];

  return (
    <div className="challenge-section">
      <div className="section-header">
        <span className="eyebrow">Why this matters</span>
        <h2>The challenge</h2>
        <p className="section-intro">
          AI could reshape market incomes through three mechanisms, each creating
          profound uncertainty:
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
        <p>
          Current policy scoring institutions like{" "}
          <Source href="https://www.cbo.gov/">CBO</Source> operate under a single
          baseline economic scenario. AI amplifies the need for{" "}
          <Source href="https://www.nber.org/papers/w34256">
            probabilistic policy analysis
          </Source>{" "}
          across multiple growth trajectories.
        </p>
      </div>
    </div>
  );
}

export default Challenge;
