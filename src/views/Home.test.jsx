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

test("sources the Iceberg Index to iceberg.mit.edu on the US overview", () => {
  renderHome("/");

  const links = screen.getAllByRole("link");
  const icebergLinks = links.filter((link) =>
    /iceberg/i.test(link.textContent ?? ""),
  );
  expect(icebergLinks.length).toBeGreaterThanOrEqual(4);
  icebergLinks.forEach((link) => {
    expect(link.getAttribute("href")).toMatch(/^https:\/\/iceberg\.mit\.edu/);
  });
  expect(
    screen.getByRole("link", { name: /MIT Media Lab Camera Culture/i }),
  ).toHaveAttribute("href", "https://iceberg.mit.edu");
  expect(
    links.filter((link) =>
      (link.getAttribute("href") ?? "").includes("futuretech.mit.edu"),
    ),
  ).toHaveLength(0);
});
