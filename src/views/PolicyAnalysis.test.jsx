import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import PolicyAnalysis from "./PolicyAnalysis";

function renderPolicyAnalysis(initialEntry = "/policy-analysis") {
  render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <PolicyAnalysis />
    </MemoryRouter>,
  );
}

const EXPERIMENT = "We reduce positive employment and self-employment income by 0% to 100% in 10-point steps, then add the same weighted total to positive capital income. We scale every positive amount by one common factor, so each person gains in proportion to the capital income they already receive.";

test("the US experiment card says market income stays the same", () => {
  renderPolicyAnalysis();
  expect(document.body).toHaveTextContent(
    `${EXPERIMENT} Total market income stays the same, and we model no behavioral responses.`,
  );
});

test("the UK experiment card makes no market income claim", () => {
  // policyengine-uk's household_market_income leaves out ISA interest, which
  // the UK shift raises, so UK market income falls by the ISA share.
  renderPolicyAnalysis("/policy-analysis?country=uk");
  expect(document.body).toHaveTextContent(
    `${EXPERIMENT} We model no behavioural responses.`,
  );
  expect(document.body).not.toHaveTextContent(/market income stays/i);
  expect(document.body).not.toHaveTextContent(/behavioral/);
});
