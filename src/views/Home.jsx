import React from "react";
import { Link, useSearchParams } from "react-router-dom";
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
  const researchPath =
    countryKey === "us" ? "/research" : `/research?country=${countryKey}`;
  const referencesPath =
    countryKey === "us" ? "/references" : `/references?country=${countryKey}`;

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
            Income-shift experiment {"→"}
          </a>
          <Link to={researchPath} className="cta-button primary">
            Research context {"→"}
          </Link>
          <Link to={referencesPath} className="cta-button secondary">
            References {"→"}
          </Link>
        </div>
      </div>
    </main>
  );
}

export default Home;
