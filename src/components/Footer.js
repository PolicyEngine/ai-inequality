import React from "react";
import "./Footer.css";

function Footer() {
  return (
    <footer className="footer">
      <div className="footer-content">
        <div className="footer-section">
          <h4>About</h4>
          <p>
            PolicyEngine is a nonprofit building open-source tax-benefit
            microsimulation models to make public policy more transparent,
            accessible, and impactful. This research initiative examines how
            policy tools can address AI-driven economic disruption.
          </p>
        </div>
        <div className="footer-section">
          <h4>Links</h4>
          <ul>
            <li>
              <a
                href="https://policyengine.org"
                target="_blank"
                rel="noopener noreferrer"
              >
                PolicyEngine.org
              </a>
            </li>
            <li>
              <a
                href="https://github.com/PolicyEngine/ai-inequality"
                target="_blank"
                rel="noopener noreferrer"
              >
                GitHub
              </a>
            </li>
            <li>
              <a href="mailto:hello@policyengine.org">
                hello@policyengine.org
              </a>
            </li>
          </ul>
        </div>
      </div>
      <div className="footer-bottom">
        <span className="footer-brand">PolicyEngine</span>
        <p>
          &copy; {new Date().getFullYear()} PolicyEngine. All rights reserved.
        </p>
      </div>
    </footer>
  );
}

export default Footer;
