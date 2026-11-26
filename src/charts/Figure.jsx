import React from "react";

import { policyEngineLabel } from "../utils/modelMetadata";
import { LEGEND_STYLE } from "./kitTheme";

// A figure on a study page: the finding as its title, a subtitle that says
// what the chart measures, the chart, a footnote and the source line, which
// names the model and baseline year as ShiftSweep's metadata line does.
export default function Figure({
  id,
  title,
  subtitle,
  legend,
  children,
  footnote,
  metadata,
  year,
}) {
  const titleId = `${id}-title`;
  return (
    <figure id={id} className="study-figure" aria-labelledby={titleId}>
      <h3 id={titleId} className="study-figure-title">
        {title}
      </h3>
      {subtitle && <p className="study-figure-subtitle">{subtitle}</p>}
      {legend}
      {children}
      <figcaption className="study-figure-notes">
        {footnote && <p className="study-figure-footnote">{footnote}</p>}
        <p className="study-figure-source">
          {policyEngineLabel(metadata)}, {year} baseline.
        </p>
      </figcaption>
    </figure>
  );
}

// A legend for line charts: a sample of each line's stroke and its name.
// Each item takes the stroke, and dash if any, its line draws with.
export function LineLegend({ items }) {
  return (
    <ul className="study-figure-legend" style={LEGEND_STYLE.wrapperStyle}>
      {items.map(({ label, stroke, strokeDasharray }) => (
        <li key={label} className="study-figure-legend-item">
          <svg
            width="28"
            height="10"
            viewBox="0 0 28 10"
            aria-hidden="true"
            focusable="false"
          >
            <line
              x1="0"
              y1="5"
              x2="28"
              y2="5"
              stroke={stroke}
              strokeWidth="2.5"
              strokeDasharray={strokeDasharray}
            />
          </svg>
          {label}
        </li>
      ))}
    </ul>
  );
}
