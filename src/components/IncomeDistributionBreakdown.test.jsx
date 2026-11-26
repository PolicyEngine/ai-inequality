import { fireEvent, render, screen } from "@testing-library/react";

import { GAIN, LOSS, SERIES } from "../charts/kitTheme";
import incomeDistributionData from "../data/incomeDistributionData.json";
import IncomeDistributionBreakdown, {
  SEGMENT_COLOURS,
  stackedComponents,
} from "./IncomeDistributionBreakdown";

test("switches income distribution breakdown between concepts and views", () => {
  render(<IncomeDistributionBreakdown />);

  expect(
    screen.getByRole("heading", { name: /current income distribution/i }),
  ).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: /market income/i })).toHaveClass(
    "active",
  );
  expect(document.body).toHaveTextContent(/measured capital income/i);
  expect(document.body).toHaveTextContent(
    /benchmark capital-income concentration/i,
  );
  expect(document.body).toHaveTextContent(/IRS Statistics of Income/i);

  fireEvent.click(screen.getByRole("tab", { name: /net income/i }));
  expect(document.body).toHaveTextContent(/taxes before refundable credits/i);

  fireEvent.click(screen.getByRole("tab", { name: /share of total/i }));
  expect(document.body).toHaveTextContent(/national total income/i);
});

test("segments take kit colours by key, never the data file's", () => {
  expect(SEGMENT_COLOURS.taxes).toBe(LOSS);
  expect(SEGMENT_COLOURS.benefits).toBe(GAIN);
  for (const conceptKey of ["market", "net"]) {
    const components = incomeDistributionData[conceptKey].components;
    const stacked = stackedComponents(conceptKey, components);
    expect(stacked.map((c) => c.key).sort()).toEqual(
      components.map((c) => c.key).sort(),
    );
    const colours = stacked.map((c) => SEGMENT_COLOURS[c.key]);
    for (const colour of colours) {
      expect([...SERIES, GAIN, LOSS]).toContain(colour);
    }
    // Every segment in a concept has its own colour.
    expect(new Set(colours).size).toBe(colours.length);
  }

  render(<IncomeDistributionBreakdown />);
  fireEvent.click(screen.getByRole("tab", { name: /net income/i }));
  const swatches = [...document.querySelectorAll(".income-component-swatch")];
  expect(swatches.map((node) => node.getAttribute("style"))).toEqual(
    incomeDistributionData.net.components.map(
      (c) => `background: ${SEGMENT_COLOURS[c.key]};`,
    ),
  );
});
