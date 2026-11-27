const configuredBasePath =
  process.env.NEXT_PUBLIC_BASE_PATH || "/us/ai-inequality";

// policyengine.org serves the UK view here by rewriting it to this export's
// /us/ai-inequality pages, so the browser keeps this path.
export const UK_STUDY_PATH = "/uk/ai-inequality";

export function isUkStudyPath(pathname) {
  return pathname === UK_STUDY_PATH || pathname.startsWith(`${UK_STUDY_PATH}/`);
}

export const basePath =
  typeof window !== "undefined" && isUkStudyPath(window.location.pathname)
    ? UK_STUDY_PATH
    : configuredBasePath;

export function withBasePath(path) {
  if (!path) {
    return basePath;
  }

  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${basePath}${normalizedPath}`;
}
