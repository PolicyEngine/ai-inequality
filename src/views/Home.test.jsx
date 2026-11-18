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

test.each(["us", "uk"])(
  "links the %s users and citations pages, with no Iceberg tile or past event",
  (country) => {
    renderHome(`/?country=${country}`);

    expect(
      screen.getByRole("link", { name: /government teams, research groups/i }),
    ).toHaveAttribute("href", `https://www.policyengine.org/${country}/users`);
    expect(
      screen.getByRole("link", {
        name: /legislators and academic researchers/i,
      }),
    ).toHaveAttribute(
      "href",
      `https://www.policyengine.org/${country}/citations`,
    );
    expect(screen.queryByText(/workers simulated/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/EA Global/i)).not.toBeInTheDocument();
  },
);
