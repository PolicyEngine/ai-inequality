import { appUrl } from "./basePath";

// policyengine.org serves /uk/ai-inequality and each page below it by
// fetching this export's /us/ai-inequality page with ?country=uk
// (policyengine-app-v2, website/src/data/appZoneRoutes.ts). The browser keeps
// the UK path and its own query. serveUkStudyPath routes a page's UK-path
// requests the same way, and hands each upstream response to onUpstream, so a
// spec can note one that answers with anything but the page itself, such as a
// redirect or a 404.
//
// policyengine.org answers a trailing slash with a 308 to the path without it
// (checked on 2026-11-27), so its pages see a slashed UK path only on a host
// that doesn't. The route serves the slashed spelling as it stands.
export const UK_PATH = "/uk/ai-inequality";

const isUkPath = (url) =>
  url.pathname === UK_PATH || url.pathname.startsWith(`${UK_PATH}/`);

export async function serveUkStudyPath(page, onUpstream = () => {}) {
  await page.route(isUkPath, async (route) => {
    const url = new URL(route.request().url());
    const rest = url.pathname.slice(UK_PATH.length).replace(/\/+$/, "");
    const upstream = new URL(appUrl(rest).replace(/\/$/, ""), url);
    upstream.searchParams.set("country", "uk");
    const response = await route.fetch({
      url: upstream.href,
      maxRedirects: 0,
    });
    onUpstream(upstream, response);
    await route.fulfill({ response });
  });
}
