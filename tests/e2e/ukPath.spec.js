import { test, expect } from "@playwright/test";
import { appUrl } from "./basePath";
import { UK_PATH, serveUkStudyPath } from "./ukStudyRoute";

// The route in ukStudyRoute.js serves the UK path as policyengine.org does.
// Each test notes any upstream request that answers with anything but the
// page itself, such as a redirect or a 404. A reload may get a 304, which
// keeps the page it already has. Each page must show the UK view under the
// slashed spelling too.
let upstreamFailures = [];

test.beforeEach(async ({ page }) => {
  upstreamFailures = [];
  await serveUkStudyPath(page, (upstream, response) => {
    if (![200, 304].includes(response.status())) {
      upstreamFailures.push(`${upstream.pathname}: ${response.status()}`);
    }
  });
});

test.afterEach(() => {
  expect(upstreamFailures).toEqual([]);
});

const radio = (page, name) => page.getByRole("radio", { name });
const UNITED_STATES = /united states/i;
const UNITED_KINGDOM = /united kingdom/i;

// Each page under both spellings. The browser keeps the path it asked for,
// with no query.
const PAGES = [
  { path: "", uk: "£144bn" },
  { path: "/income-shift", uk: "positive labour income" },
  { path: "/policy-analysis", uk: "We model no behavioural responses." },
];
for (const { path, uk } of PAGES) {
  for (const visit of [`${UK_PATH}${path}`, `${UK_PATH}${path}/`]) {
    test(`${visit} shows the UK view`, async ({ page }) => {
      await page.goto(visit);
      await expect(page.getByText(uk).first()).toBeVisible();
      await expect(page.locator("body")).not.toContainText("Medicaid");
      await expect(page.locator("section.health-coverage")).toHaveCount(0);
      const { pathname, search } = new URL(page.url());
      expect(pathname).toBe(visit);
      expect(search).toBe("");
    });
  }
}

test("an in-app link from the UK overview stays on the UK path", async ({
  page,
}) => {
  await page.goto(UK_PATH);
  await expect(page.getByText("£144bn").first()).toBeVisible();
  await page.locator("a.cta-button", { hasText: "References" }).click();
  await expect(page).toHaveURL(new RegExp(`${UK_PATH}/references$`));
});

test("the US memo's link opens the US experiment from the UK path", async ({
  page,
}) => {
  await page.goto(`${UK_PATH}/budget-lab`);
  await page
    .getByRole("link", { name: /interactive version of this analysis/i })
    .click();
  await expect(page).toHaveURL(
    new RegExp(`${UK_PATH}/income-shift\\?country=us$`),
  );
  await expect(radio(page, UNITED_STATES)).toHaveAttribute(
    "aria-checked",
    "true",
  );
});

test("on the UK path, the selector reaches the US, survives a reload, and comes back", async ({
  page,
}) => {
  await page.goto(`${UK_PATH}/income-shift`);
  await expect(radio(page, UNITED_KINGDOM)).toHaveAttribute(
    "aria-checked",
    "true",
  );

  await radio(page, UNITED_STATES).click();
  await expect(page).toHaveURL(
    new RegExp(`${UK_PATH}/income-shift\\?country=us$`),
  );
  await expect(radio(page, UNITED_STATES)).toHaveAttribute(
    "aria-checked",
    "true",
  );

  await page.reload();
  await expect(radio(page, UNITED_STATES)).toHaveAttribute(
    "aria-checked",
    "true",
  );
  expect(new URL(page.url()).pathname).toBe(`${UK_PATH}/income-shift`);

  await radio(page, UNITED_KINGDOM).click();
  await expect(page).toHaveURL(new RegExp(`${UK_PATH}/income-shift$`));
  await expect(radio(page, UNITED_KINGDOM)).toHaveAttribute(
    "aria-checked",
    "true",
  );
});

test("on the US path, the selector reaches the UK and comes back", async ({
  page,
}) => {
  await page.goto(appUrl("/income-shift"));
  await expect(radio(page, UNITED_STATES)).toHaveAttribute(
    "aria-checked",
    "true",
  );

  await radio(page, UNITED_KINGDOM).click();
  await expect(page).toHaveURL(/\/income-shift\?country=uk$/);
  await expect(page.getByText("positive labour income").first()).toBeVisible();

  await radio(page, UNITED_STATES).click();
  await expect(page).toHaveURL(/\/income-shift$/);
  await expect(radio(page, UNITED_STATES)).toHaveAttribute(
    "aria-checked",
    "true",
  );
});

test("the UK path with ?country=us shows the US policy analysis", async ({
  page,
}) => {
  await page.goto(`${UK_PATH}/policy-analysis?country=us`);
  await expect(page.locator("section.health-coverage")).toHaveCount(1);
  const { pathname, search } = new URL(page.url());
  expect(pathname).toBe(`${UK_PATH}/policy-analysis`);
  expect(search).toBe("?country=us");
});

test("the US policy analysis still shows the US view", async ({ page }) => {
  const response = await page.goto(appUrl("/policy-analysis"));
  // The US page loads directly, with no redirect.
  expect(response.status()).toBe(200);
  expect(response.request().redirectedFrom()).toBeNull();
  await expect(page.locator("section.health-coverage")).toHaveCount(1);
  await expect(page.locator("body")).not.toContainText(
    "We model no behavioural responses.",
  );
});
