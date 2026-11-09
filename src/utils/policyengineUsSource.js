import snapshot from "../data/policyengineUsSnapshot.json";

// The uprating table describes one PolicyEngine-US release, so each source
// link opens the file at that release's commit. There the path exists and the
// file shows the uprating its row reports, whatever the repository moves or
// changes later.
export const POLICYENGINE_US_SNAPSHOT = snapshot;

const SOURCE_ROOTS = {
  parameter: "policyengine_us/parameters",
  variable: "policyengine_us/variables",
};

// The row's file as a repository path, or null when the row names no file or
// has a type with no source folder.
export function policyengineUsSourcePath(row) {
  const root = SOURCE_ROOTS[row?.type];
  return root && row.file_path ? `${root}/${row.file_path}` : null;
}

export function policyengineUsSourceUrl(row) {
  const path = policyengineUsSourcePath(row);
  return path
    ? `https://github.com/${snapshot.repository}/blob/${snapshot.commit}/${path}`
    : null;
}

// "October 2025" for "2025-10-09", whatever the reader's time zone.
export function formatReleaseMonth(isoDate) {
  return new Date(`${isoDate}T00:00:00Z`).toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}
