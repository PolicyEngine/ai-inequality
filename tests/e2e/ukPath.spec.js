import { test, expect } from "@playwright/test";
import { appUrl } from "./basePath";

// policyengine.org serves /uk/ai-inequality and each page below it by
// fetching this export's /us/ai-inequality page with ?country=uk
// (policyengine-app-v2, website/src/data/appZoneRoutes.ts). The browser keeps
// the UK path and its own query. The route below does the same, and notes any
// upstream request that answers with anything but the page itself, such as a
// redirect or a 404. A reload may get a 304, which keeps the page it already
// has.
//
// policyengine.org answers a trailing slash with a 308 to the path without it
// (checked on 2026-11-27), so its pages see a slashed UK path only on a host
// that doesn't. The route serves the slashed spelling as it stands, and each
// page must show the UK view under it too.
const UK_PATH = "/uk/ai-inequality";
const isUkPath = (url) =>
  url.pathname === UK_PATH || url.pathname.startsWith(`${UK_PATH}/`);

let upstreamFailures = [];

test.beforeEach(async ({ page }) => {
  upstreamFailures = [];
  await page.route(isUkPath, async (route) => {
    const url = new URL(route.request().url());
    const rest = url.pathname.slice(UK_PATH.length).replace(/\/+$/, "");
    const upstream = new URL(appUrl(rest).replace(/\/$/, ""), url);
    upstream.searchParams.set("country", "uk");
    const response = await route.fetch({
      url: upstream.href,
      maxRedirects: 0,
    });
    if (![200, 304].includes(response.status())) {
      upstreamFailures.push(`${upstream.pathname}: ${response.status()}`);
    }
    await route.fulfill({ response });
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
