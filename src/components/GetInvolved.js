import React from "react";
import "./GetInvolved.css";

function GetInvolved() {
  const columns = [
    {
      title: "Research partners",
      description:
        "We\u2019re looking for economists with macro modeling experience who want to integrate AI scenarios into microsimulation infrastructure. Whether you\u2019re a postdoc, PhD student, or established researcher, we\u2019d love to explore collaboration.",
    },
    {
      title: "Funders",
      description:
        "This work sits at the intersection of AI safety, economic policy, and inequality \u2014 three areas that are individually well-funded but poorly integrated. We\u2019re seeking support to hire a dedicated researcher and expand our modeling capabilities.",
    },
    {
      title: "Community",
      description:
        "Join the TAI Econ Signal group for ongoing discussion. Share your AI economic scenarios for us to model. Provide feedback on our research framework.",
    },
  ];

  return (
    <div id="get-involved" className="getinvolved-section">
      <div className="section-header">
        <span className="eyebrow">Partner with us</span>
        <h2>Get involved</h2>
      </div>

      <div className="getinvolved-columns">
        {columns.map((col, idx) => (
          <div key={idx} className="getinvolved-column">
            <h3>{col.title}</h3>
            <p>{col.description}</p>
          </div>
        ))}
      </div>

      <div className="getinvolved-cta">
        <p>
          Interested in collaborating? Reach out at{" "}
          <a href="mailto:hello@policyengine.org">hello@policyengine.org</a> or
          connect at EA Global SF (Feb 2026).
        </p>
      </div>
    </div>
  );
}

export default GetInvolved;
