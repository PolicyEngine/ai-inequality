"""Entry point: python -m analysis.run_labor_shift"""

import os

import pandas as pd

from .labor_capital_shift import run_scenarios

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs", "labor_shift")


def main():
    results = run_scenarios()

    # Print summary table
    print("\n" + "=" * 70)
    print("LABOR → CAPITAL SHIFT ANALYSIS")
    print("=" * 70)

    columns = {"Metric": [
        "Market income Gini",
        "Net income Gini",
        "SPM poverty rate",
        "Federal income tax revenue",
        "Top decile income share",
        "Bottom decile income share",
    ]}
    columns["Baseline"] = _format_row(results["baseline"])
    for r in results["shifts"]:
        columns[r["label"]] = _format_row(r)
    if results["ubi"]:
        columns[results["ubi"]["label"]] = _format_row(results["ubi"])

    summary = pd.DataFrame(columns)
    print(summary.to_string(index=False))

    # Export CSVs
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("\nExporting CSV results...")

    rows = [results["baseline"]] + results["shifts"]
    if results["ubi"]:
        rows.append(results["ubi"])

    numeric = pd.DataFrame([{
        "scenario": r["label"],
        "market_gini": r["market_gini"],
        "net_gini": r["net_gini"],
        "spm_poverty_rate": r["spm_poverty_rate"],
        "fed_revenue": r["fed_revenue"],
        "top_decile_share": r["decile_shares"][9],
        "bottom_decile_share": r["decile_shares"][0],
    } for r in rows])
    numeric.to_csv(os.path.join(OUTPUT_DIR, "summary_metrics.csv"), index=False)

    decile_data = {"decile": list(range(1, 11))}
    for r in rows:
        key = r["label"].lower().replace(" ", "_").replace("%", "pct")
        decile_data[key] = r["decile_shares"]
    pd.DataFrame(decile_data).to_csv(
        os.path.join(OUTPUT_DIR, "decile_shares.csv"), index=False
    )

    print(f"  Saved to {OUTPUT_DIR}/")
    print("Done!")


def _format_row(r):
    return [
        f"{r['market_gini']:.4f}",
        f"{r['net_gini']:.4f}",
        f"{r['spm_poverty_rate']:.2%}",
        f"${r['fed_revenue']:,.0f}",
        f"{r['decile_shares'][9]:.2%}",
        f"{r['decile_shares'][0]:.2%}",
    ]


if __name__ == "__main__":
    main()
