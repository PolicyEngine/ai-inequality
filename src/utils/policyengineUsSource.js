import snapshot from "../data/policyengineUsSnapshot.json";

// Each source link opens its file at the commit the snapshot pins. Every path
// the uprating table names exists at that commit, so the links keep working
// whatever the repository moves or deletes later.
export const POLICYENGINE_US_SNAPSHOT = snapshot;

const SOURCE_ROOTS = {
  parameter: "policyengine_us/parameters",
  variable: "policyengine_us/variables",
};

// The row's file as a repository path, or null when the row names no file or
// has a type with no source folder. Only SOURCE_ROOTS' own keys count, so a
// type such as "toString" or "__proto__" gets no folder from Object.prototype.
export function policyengineUsSourcePath(row) {
  const type = row?.type;
  const root = Object.prototype.hasOwnProperty.call(SOURCE_ROOTS, type)
    ? SOURCE_ROOTS[type]
    : null;
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
