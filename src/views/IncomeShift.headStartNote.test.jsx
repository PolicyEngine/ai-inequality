import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import IncomeShift from "./IncomeShift";

// The committed US sweep, as a run from before the September 2026 Head Start
// correction would record it: its bundle has no net_income_excluded_benefits.
vi.mock("../data/shiftSweepData.json", async (importOriginal) => {
  const data = (await importOriginal()).default;
  const bundle = { ...data.metadata.policyengine_bundle };
  delete bundle.net_income_excluded_benefits;
  return {
    default: {
      ...data,
      metadata: { ...data.metadata, policyengine_bundle: bundle },
    },
  };
});

test("discloses that a US sweep from before the correction counts Head Start", () => {
  render(
    <MemoryRouter initialEntries={["/income-shift"]}>
      <IncomeShift />
    </MemoryRouter>,
  );

  // Once in the Model card, once under the sweep chart, each linking to the
  // correction note at the top of the memo page.
  expect(
    document.body.textContent.match(
      /predates? the September 2026 Head Start correction/gi,
    ),
  ).toHaveLength(2);
  const links = screen.getAllByRole("link", {
    name: /September 2026 Head Start correction/i,
  });
  expect(links).toHaveLength(2);
  for (const link of links) {
    expect(link).toHaveAttribute("href", "/budget-lab");
  }
  expect(document.body).toHaveTextContent(
    /still include Head Start and Early Head Start/i,
  );
});
