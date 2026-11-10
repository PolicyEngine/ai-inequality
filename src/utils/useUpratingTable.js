import { useEffect, useState } from "react";

import { withBasePath } from "./basePath";
import { UPRATING_TABLE_PATH, parseUpratingTable } from "./upratingTable";

// Loads public/data/uprating_analysis.csv once per mount.
export function useUpratingTable() {
  const [state, setState] = useState({
    rows: [],
    loading: true,
    error: null,
  });

  useEffect(() => {
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
  }, []);

  return state;
}
