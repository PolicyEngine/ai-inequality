import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import Home from "./Home";

function renderHome(initialEntry = "/") {
  render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Home />
    </MemoryRouter>,
  );
}

test("renders the UK overview with UK-specific evidence", () => {
  renderHome("/?country=uk");

  expect(screen.getByText("£144bn")).toBeInTheDocument();
  expect(screen.getAllByText(/labour/i).length).toBeGreaterThan(0);
  expect(screen.getByText(/UK GenAI exposure/i)).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: /income-shift experiment/i }),
  ).toHaveAttribute(
    "href",
    "https://www.policyengine.org/uk/ai-inequality/income-shift",
  );
  expect(screen.queryByText(/MIT Iceberg Index/i)).not.toBeInTheDocument();
});
