import React, { useState, useEffect, useMemo } from "react";
import Papa from "papaparse";
import { IconBulb } from "@tabler/icons-react";

function UpratingViewer() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [expandedCategory, setExpandedCategory] = useState(null);

  useEffect(() => {
    fetch(`${process.env.PUBLIC_URL}/data/uprating_analysis.csv`)
      .then((response) => response.text())
      .then((csvText) => {
        Papa.parse(csvText, {
          header: true,
          skipEmptyLines: true,
          complete: (results) => {
            setData(results.data);
            setLoading(false);
          },
          error: (err) => {
            setError(err.message);
            setLoading(false);
          },
        });
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

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
    // Sort by total count (parameters + variables), putting income_by_source categories first
    return Object.keys(groupedData).sort((a, b) => {
      const aIsIncome = a.includes("income_by_source");
      const bIsIncome = b.includes("income_by_source");

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

  const getCategoryDisplayName = (category) => {
    // Hard-coded mapping for clean display names
    const nameMap = {
      "IRS (Chained CPI-U)": "IRS Chained CPI-U",
      "CPI-U (Direct)": "CPI-U",
      "SNAP (CPI-U Q2)": "SNAP",
      "SSA (CPI-W)": "Social Security (CPI-W)",
      "HHS (CPI-U)": "HHS Federal Poverty Guidelines",
      "ACA Benchmark Premium": "ACA Benchmark Premium",
      "Other: gov.ssa.nawi": "National Average Wage Index (SSA)",
      "Other: gov.states.ca.cpi": "California CPI",
      "Other: {'parameter': 'gov.states.ca.cpi'": "California CPI",
      "Other: calibration.gov.census.populations.total": "Population (Census)",
      "Other: calibration.gov.cbo.income_by_source.adjusted_gross_income":
        "Adjusted Gross Income (CBO)",
      "Other: calibration.gov.cbo.income_by_source.employment_income":
        "Employment Income (CBO)",
      "Other: calibration.gov.cbo.income_by_source.net_capital_gain":
        "Net Capital Gain (CBO)",
      "Other: calibration.gov.cbo.income_by_source.qualified_dividend_income":
        "Qualified Dividend Income (CBO)",
      "Other: calibration.gov.cbo.income_by_source.self_employment_income":
        "Self Employment Income (CBO)",
      "Other: calibration.gov.cbo.income_by_source.taxable_interest_and_ordinary_dividends":
        "Taxable Interest And Ordinary Dividends (CBO)",
      "Other: calibration.gov.cbo.income_by_source.taxable_pension_income":
        "Taxable Pension Income (CBO)",
      "Other: calibration.gov.cbo.income_by_source.taxable_social_security":
        "Taxable Social Security (CBO)",
    };

    return nameMap[category] || category;
  };

  if (loading) {
    return (
      <div className="section" style={{ textAlign: "center", padding: "3rem" }}>
        <p>Loading uprating parameters...</p>
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
      <h2>PolicyEngine-US uprating parameters & variables</h2>
      <p
        style={{
          textAlign: "center",
          maxWidth: "800px",
          margin: "0 auto 1rem",
          fontSize: "1.1rem",
        }}
      >
        Explore the <strong>294 parameters</strong> and{" "}
        <strong>23 variables</strong> in PolicyEngine-US that grow over time
        based on different economic indicators. These growth factors create
        correlated uncertainty in long-term policy projections.
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
        <p style={{ margin: 0, fontWeight: "500", display: "flex", alignItems: "flex-start", gap: "0.5rem" }}>
          <IconBulb size={20} stroke={1.5} style={{ flexShrink: 0, marginTop: "2px" }} />
          <span><strong>CBO Income by Source</strong> projections (highlighted in
          yellow) are critical for AI scenarios, as AI-driven wage compression
          and capital income shifts directly impact these growth rates.</span>
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
            }}
          >
            <option value="all">All Categories ({data.length} total)</option>
            {categories.map((category) => {
              const total =
                groupedData[category].parameters.length +
                groupedData[category].variables.length;
              return (
                <option key={category} value={category}>
                  {getCategoryDisplayName(category)} ({total})
                </option>
              );
            })}
          </select>
        </div>

        <p
          style={{ textAlign: "center", color: "#718096", fontSize: "0.95rem" }}
        >
          Showing {totalCounts.total} items ({totalCounts.parameters}{" "}
          parameters, {totalCounts.variables} variables)
          {searchTerm && ` matching "${searchTerm}"`}
        </p>
      </div>

      {/* Grouped Parameter Display */}
      <div className="grid">
        {Object.keys(filteredData).map((category) => {
          const group = filteredData[category];
          const allItems = [...group.parameters, ...group.variables];
          const isExpanded = expandedCategory === category;
          const isIncome = category.includes("income_by_source");

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
                <span>{getCategoryDisplayName(category)}</span>
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
                        <a
                          href={`https://github.com/PolicyEngine/policyengine-us/blob/master/policyengine_us/parameters/${param.file_path}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            fontSize: "0.85rem",
                            color: "#319795",
                            textDecoration: "none",
                            marginTop: "0.5rem",
                            display: "inline-block",
                          }}
                          onClick={(e) => e.stopPropagation()}
                        >
                          View source →
                        </a>
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
          No parameters match your search criteria.
        </p>
      )}

      <div
        className="card"
        style={{ marginTop: "2rem", backgroundColor: "#f0f9ff" }}
      >
        <h3>About these parameters</h3>
        <p>
          Each parameter in PolicyEngine-US that changes over time uses an
          "uprating" method to project its value forward. The uprating method
          determines which economic indicator drives the growth:
        </p>
        <ul style={{ marginTop: "1rem" }}>
          <li>
            <strong>IRS Chained CPI-U:</strong> Most federal tax parameters
            (brackets, deductions, credits) indexed to chained CPI-U
          </li>
          <li>
            <strong>CPI-U Direct:</strong> Some state parameters and benefit
            amounts indexed to standard CPI-U
          </li>
          <li>
            <strong>SSA CPI-W:</strong> Social Security parameters indexed to
            CPI-W (wage earners)
          </li>
          <li>
            <strong>Income by Source:</strong> CBO projections for different
            income types (wages, capital gains, dividends, etc.)
          </li>
          <li>
            <strong>Other:</strong> Population growth, state-specific inflation,
            wage indexes
          </li>
        </ul>
        <p style={{ marginTop: "1rem" }}>
          These growth factors are correlated but not perfectly - modeling their
          joint distribution is critical for accurate long-term projections
          under AI scenarios.
        </p>
      </div>
    </div>
  );
}

UpratingViewer.displayName = "UpratingViewer";

export default UpratingViewer;
