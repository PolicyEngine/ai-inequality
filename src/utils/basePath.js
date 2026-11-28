const configuredBasePath =
  process.env.NEXT_PUBLIC_BASE_PATH || "/us/ai-inequality";

// policyengine.org serves the UK view here by rewriting it to this export's
// /us/ai-inequality pages, so the browser keeps this path.
export const UK_STUDY_PATH = "/uk/ai-inequality";

export function isUkStudyPath(pathname) {
  return pathname === UK_STUDY_PATH || pathname.startsWith(`${UK_STUDY_PATH}/`);
}

// The base the browser shows: the UK path when policyengine.org serves the
// study there, and the configured one otherwise. It reads the browser's path
// on each call, not once when the module loads, so callers build URLs at
// render time.
export function currentBasePath() {
  return typeof window !== "undefined" &&
    isUkStudyPath(window.location.pathname)
    ? UK_STUDY_PATH
    : configuredBasePath;
}

export function withBasePath(path) {
  const base = currentBasePath();
  if (!path) {
    return base;
  }

  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${base}${normalizedPath}`;
}
