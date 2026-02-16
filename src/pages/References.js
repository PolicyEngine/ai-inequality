import React from "react";
import { Link } from "react-router-dom";
import {
  getAllReferences,
  formatAPACitation,
  formatBibTeX,
} from "../data/references";
import "./References.css";

function References() {
  const references = getAllReferences();

  return (
    <div className="references-page">
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
          References
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
          Academic literature on AI economics, labor impacts, distributional
          effects, and microsimulation modeling
        </p>
      </div>

      <div className="container references-content">
        <div className="references-list">
          {references.length === 0 ? (
            <div className="no-references">
              <p>No references found for this category.</p>
            </div>
          ) : (
            references.map((ref) => (
              <div key={ref.id} className="reference-item">
                <a
                  href={ref.doi ? `https://doi.org/${ref.doi}` : ref.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="reference-citation-link"
                >
                  <div
                    className="reference-citation"
                    dangerouslySetInnerHTML={{
                      __html: formatAPACitation(ref),
                    }}
                  />
                </a>
              </div>
            ))
          )}
        </div>

        <div className="references-footer">
          <h3>Download all references</h3>
          <p>
            Click below to download all references in BibTeX format for use with
            citation managers like Zotero, Mendeley, or BibDesk.
          </p>
          <button
            onClick={() => {
              const allBibtex = getAllReferences()
                .map((ref) => formatBibTeX(ref))
                .join("\n\n");
              const blob = new Blob([allBibtex], { type: "text/plain" });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = "ai-growth-references.bib";
              a.click();
              URL.revokeObjectURL(url);
            }}
            className="download-button"
          >
            Download BibTeX File
          </button>
        </div>
      </div>
    </div>
  );
}

export default References;
