import { currentBasePath, withBasePath } from "./basePath";

const CONFIGURED = process.env.NEXT_PUBLIC_BASE_PATH || "/us/ai-inequality";

afterEach(() => {
  window.history.replaceState(null, "", "/");
});

test("the base follows the browser's path each time it's read", () => {
  window.history.replaceState(null, "", "/uk/ai-inequality/income-shift");
  expect(currentBasePath()).toBe("/uk/ai-inequality");
  expect(withBasePath("/images/x.png")).toBe("/uk/ai-inequality/images/x.png");

  window.history.replaceState(null, "", "/us/ai-inequality/income-shift");
  expect(currentBasePath()).toBe(CONFIGURED);
  expect(withBasePath("images/x.png")).toBe(`${CONFIGURED}/images/x.png`);
  expect(withBasePath("")).toBe(CONFIGURED);
});
