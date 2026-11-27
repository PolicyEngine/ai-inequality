import { test, expect } from "@playwright/test";
import { appUrl } from "./basePath";

// policyengine.org serves /uk/ai-inequality/<page> by fetching this export's
// /us/ai-inequality/<page>?country=uk, and the browser keeps the UK path with
// no query. Route the UK path the same way, so each page loads as it does on
// policyengine.org.
const UK_PATH = "/uk/ai-inequality";
const isUkPath = (url) =>
  url.pathname === UK_PATH || url.pathname.startsWith(`${UK_PATH}/`);

test.beforeEach(async ({ page }) => {
  await page.route(isUkPath, async (route) => {
    const url = new URL(route.request().url());
    const upstream = new URL(
      appUrl(url.pathname.slice(UK_PATH.length) || "/"),
      url,
    );
    upstream.searchParams.set("country", "uk");
    await route.fulfill({
      response: await route.fetch({ url: upstream.href }),
    });
  });
});

const PAGES = [
  { path: "/", uk: "£144bn" },
  { path: "/income-shift", uk: "positive labour income" },
  { path: "/policy-analysis", uk: "We model no behavioural responses." },
];

for (const { path, uk } of PAGES) {
  test(`${UK_PATH}${path} shows the UK view`, async ({ page }) => {
    await page.goto(`${UK_PATH}${path}`);
    await expect(page.getByText(uk).first()).toBeVisible();
    await expect(page.locator("body")).not.toContainText("Medicaid");
    await expect(page.locator("section.health-coverage")).toHaveCount(0);
    // The browser keeps the UK path, with no query.
    expect(new URL(page.url()).pathname).toBe(`${UK_PATH}${path}`);
    expect(new URL(page.url()).search).toBe("");
  });
}

test("the US policy analysis still shows the US view", async ({ page }) => {
  await page.goto(appUrl("/policy-analysis"));
  await expect(page.locator("section.health-coverage")).toHaveCount(1);
  await expect(page.locator("body")).not.toContainText(
    "We model no behavioural responses.",
  );
});
