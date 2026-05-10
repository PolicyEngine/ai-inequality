import { fireEvent, render, screen } from "@testing-library/react";

import IncomeDistributionBreakdown from "./IncomeDistributionBreakdown";

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
