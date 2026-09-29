import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import Home from "./Home";
import { references } from "../data/references";

function renderHome(initialEntry = "/") {
  render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Home />
    </MemoryRouter>,
  );
}

// Every page a citation may link to: the document itself or its landing site.
const REGISTRY_URLS = new Set(
  references.flatMap((ref) => [ref.url, ref.site].filter(Boolean)),
);

// The three sections that cite evidence: hero stat cards, inline sources in
// the challenge cards, and evidence-card links. Organisation links are exempt.
function citationHrefs() {
  return Array.from(
    document.querySelectorAll(
      [
        "a.hero-stat",
        ".challenge-section a.inline-source:not(.inline-org)",
        ".evidence-section a.evidence-link",
      ].join(", "),
    ),
  ).map((link) => link.getAttribute("href"));
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

test.each([
  ["US", "/"],
  ["UK", "/?country=uk"],
])(
  "every citation on the %s overview resolves to the references database",
  (_country, entry) => {
    renderHome(entry);

    const hrefs = citationHrefs();
    expect(hrefs.length).toBeGreaterThanOrEqual(10);
    expect(hrefs.filter((href) => !REGISTRY_URLS.has(href))).toEqual([]);
    expect(hrefs.filter((href) => href.includes("futuretech.mit.edu"))).toEqual(
      [],
    );
  },
);

test("sources the Iceberg Index to iceberg.mit.edu on the US overview", () => {
  renderHome("/");

  const icebergLinks = screen
    .getAllByRole("link")
    .filter((link) => /iceberg/i.test(link.textContent ?? ""));
  expect(icebergLinks.length).toBeGreaterThanOrEqual(3);
  icebergLinks.forEach((link) => {
    expect(link).toHaveAttribute("href", "https://iceberg.mit.edu");
  });
  expect(
    screen.getByRole("link", { name: /MIT Media Lab Camera Culture/i }),
  ).toHaveAttribute("href", "https://iceberg.mit.edu");
});

test("shows the current Canaries figure with its revision year", () => {
  renderHome("/");

  expect(screen.getByText("19%")).toBeInTheDocument();
  expect(screen.getAllByText("Stanford DEL (2026)").length).toBeGreaterThan(0);
  expect(screen.queryByText(/16% decline/)).not.toBeInTheDocument();
});
