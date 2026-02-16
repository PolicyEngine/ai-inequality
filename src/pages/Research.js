import React from "react";
import { Link } from "react-router-dom";
import Research from "../components/Research";
import StochasticForecasting from "../components/StochasticForecasting";
import TechnicalRequirements from "../components/TechnicalRequirements";

function ResearchPage() {
  return (
    <>
      <div
        className="section"
        style={{ paddingTop: "2rem", paddingBottom: "0" }}
      >
        <Link
          to="/"
          style={{
            color: "var(--pe-teal-600)",
            fontSize: "0.95rem",
            textDecoration: "none",
            fontWeight: 500,
            display: "inline-flex",
            alignItems: "center",
            gap: "0.25rem",
          }}
        >
          ← Back to overview
        </Link>
      </div>
      <div className="section section-alt" style={{ paddingTop: "2rem" }}>
        <h1
          style={{
            textAlign: "center",
            marginBottom: "1rem",
            fontSize: "clamp(2rem, 5vw, 3rem)",
            color: "var(--pe-gray-900)",
            letterSpacing: "-0.03em",
          }}
        >
          Research context
        </h1>
        <p
          style={{
            textAlign: "center",
            fontSize: "clamp(1rem, 2.5vw, 1.2rem)",
            maxWidth: "800px",
            margin: "0 auto 3rem",
            color: "var(--pe-gray-500)",
            lineHeight: 1.7,
          }}
        >
          Academic research on AI economics, labor markets, and probabilistic
          forecasting for microsimulation
        </p>
      </div>
      <Research />
      <StochasticForecasting />
      <TechnicalRequirements />
      <div
        className="section"
        style={{ textAlign: "center", padding: "3rem 2rem" }}
      >
        <Link
          to="/"
          style={{
            color: "var(--pe-teal-600)",
            fontSize: "1.05rem",
            textDecoration: "none",
            fontWeight: 500,
          }}
        >
          ← Back to overview
        </Link>
      </div>
    </>
  );
}

export default ResearchPage;
