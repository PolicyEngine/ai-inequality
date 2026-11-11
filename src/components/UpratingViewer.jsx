import React, { useState, useMemo } from "react";
import { IconBulb } from "@tabler/icons-react";
import {
  POLICYENGINE_US_SNAPSHOT,
  formatReleaseMonth,
  policyengineUsSourceUrl,
} from "../utils/policyengineUsSource";
import {
  cardForCategory,
  counted,
  formulaSourceUrl,
} from "../utils/upratingTable";
import { useUpratingTable } from "../utils/useUpratingTable";

const INCOME_CARD = "income-by-source";
const isIncomeCategory = (category) =>
  cardForCategory(category).id === INCOME_CARD;

// A parent that already loaded the table hands it over as `table`, so the
// page fetches it once; on its own, the viewer loads it.
function UpratingViewer({ table }) {
  const loaded = useUpratingTable({ enabled: !table });
  const { rows, loading, error } = table ?? loaded;
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [expandedCategory, setExpandedCategory] = useState(null);

  const data = useMemo(
    () =>
      rows.map((row) => ({
        ...row,
        sourceUrl: policyengineUsSourceUrl(row),
        formulaUrl: formulaSourceUrl(row),
      })),
    [rows],
  );

  const groupedData = useMemo(() => {
    if (!data.length) return {};

    const grouped = {};
    data.forEach((row) => {
      const category = row.uprating_category || "Unknown";
      if (!grouped[category]) {
        grouped[category] = { parameters: [], variables: [] };
      }
      if (row.type === "parameter") {
        grouped[category].parameters.push(row);
      } else if (row.type === "variable") {
        grouped[category].variables.push(row);
      }
    });

    return grouped;
  }, [data]);

  const categories = useMemo(() => {
    // Income-by-source categories first, then by row count.
    return Object.keys(groupedData).sort((a, b) => {
      const aIsIncome = isIncomeCategory(a);
      const bIsIncome = isIncomeCategory(b);

      if (aIsIncome && !bIsIncome) return -1;
      if (!aIsIncome && bIsIncome) return 1;

      const aTotal =
        groupedData[a].parameters.length + groupedData[a].variables.length;
      const bTotal =
        groupedData[b].parameters.length + groupedData[b].variables.length;
      return bTotal - aTotal;
    });
  }, [groupedData]);

  const filteredData = useMemo(() => {
    let filtered = groupedData;

    if (selectedCategory !== "all") {
      filtered = { [selectedCategory]: groupedData[selectedCategory] };
    }

    if (searchTerm) {
      const result = {};
      Object.keys(filtered).forEach((category) => {
        const allRows = [
          ...filtered[category].parameters,
          ...filtered[category].variables,
        ];
        const matchingRows = allRows.filter((row) => {
          const searchLower = searchTerm.toLowerCase();
          return (
            row.path?.toLowerCase().includes(searchLower) ||
            row.description?.toLowerCase().includes(searchLower) ||
            row.uprating?.toLowerCase().includes(searchLower)
          );
        });
        if (matchingRows.length > 0) {
          result[category] = {
            parameters: matchingRows.filter((r) => r.type === "parameter"),
            variables: matchingRows.filter((r) => r.type === "variable"),
          };
        }
      });
      return result;
    }

    return filtered;
  }, [groupedData, selectedCategory, searchTerm]);

  const totalCounts = useMemo(() => {
    let parameters = 0;
    let variables = 0;
    Object.values(filteredData).forEach((group) => {
      parameters += group.parameters.length;
      variables += group.variables.length;
    });
    return { parameters, variables, total: parameters + variables };
  }, [filteredData]);

  const datasetCounts = useMemo(
    () => ({
      parameters: data.filter((row) => row.type === "parameter").length,
      variables: data.filter((row) => row.type === "variable").length,
    }),
    [data],
  );

  if (loading) {
    return (
      <div className="section" style={{ textAlign: "center", padding: "3rem" }}>
        <p>Loading the uprating table…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="section" style={{ textAlign: "center", padding: "3rem" }}>
        <p style={{ color: "#e53e3e" }}>Error loading data: {error}</p>
      </div>
    );
  }

  return (
    <div id="uprating-viewer" className="section section-alt">
      <h2>
        Parameter files and variables that{" "}
        <span style={{ whiteSpace: "nowrap" }}>PolicyEngine-US</span> uprates
      </h2>
      <p
        style={{
          textAlign: "center",
          maxWidth: "800px",
          margin: "0 auto 1rem",
          fontSize: "1.1rem",
        }}
      >
        Explore the values that PolicyEngine-US{" "}
        {POLICYENGINE_US_SNAPSHOT.version} (
        {formatReleaseMonth(POLICYENGINE_US_SNAPSHOT.date)}) grows over time
        with economic indexes, in{" "}
        <strong>{datasetCounts.parameters} parameter files</strong> and{" "}
        <strong>{datasetCounts.variables} input variables</strong>.
      </p>
      <div
        style={{
          textAlign: "center",
          marginBottom: "2rem",
          padding: "1rem",
          backgroundColor: "#fff3cd",
          borderRadius: "8px",
          maxWidth: "800px",
          margin: "0 auto 2rem",
        }}
      >
        <p
          style={{
            margin: 0,
            fontWeight: "500",
            display: "flex",
            alignItems: "flex-start",
            gap: "0.5rem",
          }}
        >
          <IconBulb
            size={20}
            stroke={1.5}
            style={{ flexShrink: 0, marginTop: "2px" }}
          />
          <span>
            PolicyEngine-US grows wages, capital gains, Social Security benefits
            and most other incomes in its microdata with CBO's projections. AI
            could speed or slow the growth of those incomes, or shift income
            from wages to capital.
          </span>
        </p>
      </div>

      {/* Search and Filter Controls */}
      <div
        style={{
          maxWidth: "800px",
          margin: "0 auto 2rem",
          display: "flex",
          flexDirection: "column",
          gap: "1rem",
        }}
      >
        <input
          type="text"
          placeholder="Search by parameter name, path, or description..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{
            padding: "0.75rem 1rem",
            fontSize: "1rem",
            border: "2px solid #e2e8f0",
            borderRadius: "8px",
            width: "100%",
          }}
        />

        <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
          <label htmlFor="category-filter" style={{ fontWeight: "500" }}>
            Filter by category:
          </label>
          <select
            id="category-filter"
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            style={{
              padding: "0.5rem 1rem",
              fontSize: "1rem",
              border: "2px solid #e2e8f0",
              borderRadius: "8px",
              flex: 1,
              // Lets the select shrink below its longest option on a phone.
              minWidth: 0,
            }}
          >
            <option value="all">All categories ({data.length} total)</option>
            {categories.map((category) => {
              const total =
                groupedData[category].parameters.length +
                groupedData[category].variables.length;
              return (
                <option key={category} value={category}>
                  {category} ({total})
                </option>
              );
            })}
          </select>
        </div>

        <p
          style={{ textAlign: "center", color: "#718096", fontSize: "0.95rem" }}
        >
          Showing {counted(totalCounts.total, "item")} (
          {counted(totalCounts.parameters, "parameter file")},{" "}
          {counted(totalCounts.variables, "variable")})
          {searchTerm && ` matching "${searchTerm}"`}
        </p>
      </div>

      {/* Grouped Parameter Display */}
      <div className="grid">
        {Object.keys(filteredData).map((category) => {
          const group = filteredData[category];
          const allItems = [...group.parameters, ...group.variables];
          const isExpanded = expandedCategory === category;
          const isIncome = isIncomeCategory(category);

          return (
            <div
              key={category}
              className={`card ${isExpanded ? "expanded" : ""}`}
              onClick={() => setExpandedCategory(isExpanded ? null : category)}
              style={{
                cursor: "pointer",
                border: isIncome ? "2px solid #fbbf24" : undefined,
                backgroundColor: isIncome ? "#fffbeb" : undefined,
              }}
            >
              <h3
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <span>{category}</span>
                <span
                  style={{
                    fontSize: "0.85rem",
                    color: "#319795",
                    fontWeight: "normal",
                    display: "flex",
                    alignItems: "center",
                    gap: "0.5rem",
                  }}
                >
                  <span>
                    {group.parameters.length}p {group.variables.length}v
                  </span>
                  <span style={{ fontSize: "1.2rem" }}>
                    {isExpanded ? "▼" : "▶"}
                  </span>
                </span>
              </h3>

              {isExpanded && (
                <div
                  style={{ marginTop: "1rem" }}
                  onClick={(e) => e.stopPropagation()}
                >
                  <div
                    style={{
                      maxHeight: "400px",
                      overflowY: "auto",
                      border: "1px solid #e2e8f0",
                      borderRadius: "4px",
                      padding: "1rem",
                    }}
                  >
                    {allItems.slice(0, 50).map((param, idx) => (
                      <div
                        key={idx}
                        style={{
                          marginBottom: "1rem",
                          paddingBottom: "1rem",
                          borderBottom:
                            idx < allItems.length - 1
                              ? "1px solid #e2e8f0"
                              : "none",
                        }}
                      >
                        <div
                          style={{
                            fontFamily: "monospace",
                            fontSize: "0.85rem",
                            color: "#2d3748",
                            marginBottom: "0.25rem",
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                          }}
                        >
                          <strong>{param.path}</strong>
                          <span
                            style={{
                              fontSize: "0.75rem",
                              padding: "0.125rem 0.375rem",
                              borderRadius: "4px",
                              backgroundColor:
                                param.type === "variable"
                                  ? "#e0f2fe"
                                  : "#f3f4f6",
                              color:
                                param.type === "variable"
                                  ? "#0369a1"
                                  : "#374151",
                            }}
                          >
                            {param.type}
                          </span>
                        </div>
                        {param.description && (
                          <div
                            style={{
                              fontSize: "0.9rem",
                              color: "#4a5568",
                              marginBottom: "0.25rem",
                            }}
                          >
                            {param.description}
                          </div>
                        )}
                        <div
                          style={{
                            fontSize: "0.85rem",
                            color: "#718096",
                            marginTop: "0.25rem",
                          }}
                        >
                          Uprating: <code>{param.uprating}</code>
                        </div>
                        {param.sourceUrl && (
                          <a
                            href={param.sourceUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={itemLinkStyle}
                            onClick={(e) => e.stopPropagation()}
                          >
                            View source →
                          </a>
                        )}
                        {param.formulaUrl && (
                          <a
                            href={param.formulaUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ ...itemLinkStyle, marginLeft: "1rem" }}
                            onClick={(e) => e.stopPropagation()}
                          >
                            View formula →
                          </a>
                        )}
                      </div>
                    ))}
                    {allItems.length > 50 && (
                      <p
                        style={{
                          textAlign: "center",
                          color: "#718096",
                          fontSize: "0.9rem",
                          marginTop: "1rem",
                        }}
                      >
                        Showing first 50 of {allItems.length} items. Use search
                        to narrow results.
                      </p>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {Object.keys(filteredData).length === 0 && (
        <p
          style={{
            textAlign: "center",
            color: "#718096",
            fontSize: "1.1rem",
            marginTop: "2rem",
          }}
        >
          No parameter file or variable matches your search.
        </p>
      )}

      <div
        className="card"
        style={{ marginTop: "2rem", backgroundColor: "#f0f9ff" }}
      >
        <h3>How PolicyEngine-US grows these values</h3>
        <p>
          PolicyEngine-US grows most parameters with the index their metadata
          names, starting from the latest value in their file. Lawmakers wrote
          indexing formulas into law for some amounts, such as the payroll tax
          cap and HSA contribution limits, and PolicyEngine-US applies those
          formulas in <code>uprating_extensions.py</code>.
        </p>
        <p style={{ marginTop: "1rem" }}>
          PolicyEngine-US grows dollar inputs that name no index with CBO&apos;s
          projection of adjusted gross income per person. It grows an input that
          names a national total, such as the IRS&apos;s total of wages, with
          that total per person. It holds three federal student loan balances
          flat.
        </p>
      </div>
    </div>
  );
}

const itemLinkStyle = {
  fontSize: "0.85rem",
  color: "#319795",
  textDecoration: "none",
  marginTop: "0.5rem",
  display: "inline-block",
};

UpratingViewer.displayName = "UpratingViewer";

export default UpratingViewer;
