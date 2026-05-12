import React, { useState } from "react";
import { Link } from "react-router-dom";
import {
  TOPICS,
  getReferencesByTopic,
  formatAPACitation,
} from "../data/references";

/**
 * The Research card is a single topic from the references DB, rendered with
 * the topic blurb followed by the year-sorted reference list (collapsed
 * until clicked). All link text and summaries come from references.js so
 * there is one canonical source for the literature.
 */

const TOPIC_ORDER = [
  "labor_markets",
  "productivity_empirical",
  "exposure_measurement",
  "ai_adoption",
  "growth_theory",
  "capital_labor",
  "inequality_distribution",
  "tax_policy",
  "ubi_transfers",
  "microsimulation",
  "general_equilibrium",
  "stochastic_forecasting",
  "transformative_ai",
  "scenarios",
  "existential_risk",
];

const UK_TOPIC_ORDER = [
  "uk",
  "labor_markets",
  "productivity_empirical",
  "exposure_measurement",
  "inequality_distribution",
  "tax_policy",
  "ubi_transfers",
  "microsimulation",
];

function ReferenceItem({ reference }) {
  const href = reference.doi
    ? `https://doi.org/${reference.doi}`
    : reference.url;
  return (
    <li className="research-reference">
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        onClick={(e) => e.stopPropagation()}
        dangerouslySetInnerHTML={{
          __html: formatAPACitation(reference),
        }}
      />
      {reference.summary ? (
        <p className="research-reference-summary">{reference.summary}</p>
      ) : null}
    </li>
  );
}

function TopicCard({ slug, isExpanded, onToggle }) {
  const topic = TOPICS[slug];
  const refs = getReferencesByTopic(slug);
  if (!topic || refs.length === 0) return null;
  return (
    <div
      className={`card ${isExpanded ? "expanded" : ""}`}
      onClick={onToggle}
      style={{ cursor: "pointer" }}
    >
      <h3
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "0.75rem",
        }}
      >
        <span>{topic.title}</span>
        <span
          aria-hidden="true"
          style={{
            fontSize: "1.4rem",
            color: "var(--pe-teal-600, #319795)",
            flexShrink: 0,
          }}
        >
          {isExpanded ? "−" : "+"}
        </span>
      </h3>
      <p>{topic.blurb}</p>
      <p
        style={{
          fontSize: "0.85rem",
          color: "var(--pe-gray-500, #718096)",
          marginTop: "-0.25rem",
        }}
      >
        {refs.length} reference{refs.length === 1 ? "" : "s"}
      </p>
      {isExpanded && (
        <ul
          style={{
            marginTop: "1rem",
            paddingLeft: "1.25rem",
            display: "flex",
            flexDirection: "column",
            gap: "1rem",
          }}
        >
          {refs.map((ref) => (
            <ReferenceItem key={ref.id} reference={ref} />
          ))}
        </ul>
      )}
    </div>
  );
}

function Research({ countryKey = "us" }) {
  const [expanded, setExpanded] = useState(null);
  const order = countryKey === "uk" ? UK_TOPIC_ORDER : TOPIC_ORDER;
  return (
    <div id="research" className="section section-alt">
      <h2>Relevant research</h2>
      <p
        style={{
          textAlign: "center",
          maxWidth: "800px",
          margin: "0 auto 1rem",
        }}
      >
        Our work builds on emerging research at the intersection of AI
        economics, labor markets, inequality, and public policy. Each card below
        opens to show the citations behind that topic.
      </p>
      <p
        style={{
          textAlign: "center",
          maxWidth: "800px",
          margin: "0 auto 2rem",
          fontSize: "0.95rem",
          color: "var(--pe-gray-500, #718096)",
        }}
      >
        For the full bibliography (with BibTeX export), see the{" "}
        <Link to="/references">references page</Link>.
      </p>
      <div className="grid">
        {order.map((slug) => (
          <TopicCard
            key={slug}
            slug={slug}
            isExpanded={expanded === slug}
            onToggle={() => setExpanded(expanded === slug ? null : slug)}
          />
        ))}
      </div>
    </div>
  );
}

export default Research;
