import React from "react";
import { useSearchParams } from "react-router-dom";
import Hero from "../components/Hero";
import Challenge from "../components/Challenge";
import Approach from "../components/Approach";
import ExampleProjects from "../components/ExampleProjects";
import Evidence from "../components/Evidence";
import Ecosystem from "../components/Ecosystem";
import GetInvolved from "../components/GetInvolved";
import {
  COUNTRIES,
  countryFromSearchParams,
  incomeShiftUrl,
} from "../utils/countryConfig";

function Home() {
  const [searchParams] = useSearchParams();
  const countryKey = countryFromSearchParams(searchParams);
  const country = COUNTRIES[countryKey];
  const isUK = countryKey === "uk";

  return (
    <main>
      <Hero countryKey={countryKey} />
      <Challenge countryKey={countryKey} />
      <Approach countryKey={countryKey} />
      <ExampleProjects countryKey={countryKey} />
      <Evidence countryKey={countryKey} />
      <Ecosystem countryKey={countryKey} />
      <div id="get-involved">
        <GetInvolved countryKey={countryKey} />
      </div>
      <div className="dive-deeper-section">
        <h2>Dive deeper</h2>
        <p>
          Explore the {country.label} prototype experiment and the research
          context behind AI, labour markets, and tax-benefit policy.
        </p>
        <div className="dive-deeper-links">
          <a
            href={incomeShiftUrl(countryKey)}
            target="_top"
            className="cta-button primary"
          >
            Income-shift experiment {"\u2192"}
          </a>
          {isUK ? (
            <a
              href="https://www.policyengine.org/uk/model"
              target="_top"
              className="cta-button primary"
            >
              UK model documentation {"\u2192"}
            </a>
          ) : (
            <a href="/research" className="cta-button primary">
              Research context {"\u2192"}
            </a>
          )}
          <a href="/references" className="cta-button secondary">
            References {"\u2192"}
          </a>
        </div>
      </div>
    </main>
  );
}

export default Home;
