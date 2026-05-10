const configuredBasePath =
  process.env.NEXT_PUBLIC_BASE_PATH || "/us/ai-inequality";

export const basePath =
  typeof window !== "undefined" &&
  window.location.pathname.startsWith("/uk/ai-inequality")
    ? "/uk/ai-inequality"
    : configuredBasePath;

export function withBasePath(path) {
  if (!path) {
    return basePath;
  }

  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${basePath}${normalizedPath}`;
}
