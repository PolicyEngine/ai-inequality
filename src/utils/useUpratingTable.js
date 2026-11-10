import { useEffect, useState } from "react";

import { withBasePath } from "./basePath";
import { UPRATING_TABLE_PATH, parseUpratingTable } from "./upratingTable";

// Loads public/data/uprating_analysis.csv once per mount. A component whose
// parent already holds the table passes enabled: false, and the hook skips
// the fetch.
export function useUpratingTable({ enabled = true } = {}) {
  const [state, setState] = useState({
    rows: [],
    loading: enabled,
    error: null,
  });

  useEffect(() => {
    if (!enabled) return undefined;
    let cancelled = false;
    fetch(withBasePath(UPRATING_TABLE_PATH))
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        return response.text();
      })
      .then((text) => {
        if (!cancelled) {
          setState({
            rows: parseUpratingTable(text),
            loading: false,
            error: null,
          });
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setState({ rows: [], loading: false, error: error.message });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [enabled]);

  return state;
}
