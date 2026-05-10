export const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "/us/ai-inequality";

export function withBasePath(path) {
  if (!path) {
    return basePath;
  }

  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${basePath}${normalizedPath}`;
}
