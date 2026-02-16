"""Entry point: python -m analysis"""

import os

import pandas as pd

from .simulation import run_scenarios
from .charts import generate_all

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")


def main():
    results = run_scenarios()

    # Print summary table
    print("\n" + "=" * 70)
    print("SUMMARY COMPARISON")
    print("=" * 70)
    summary = pd.DataFrame({
        "Metric": [
            "Market income Gini",
            "Net income Gini",
            "SPM poverty rate",
            "Federal income tax revenue",
            "Top decile income share",
            "Bottom decile income share",
        ],
        "Baseline": _format_row(results["baseline"]),
        "Doubled capital": _format_row(results["doubled"]),
        "Doubled + UBI": _format_row(results["ubi"]),
    })
    print(summary.to_string(index=False))

    # Generate charts
    print("\nGenerating visualizations...")
    generate_all(results, OUTPUT_DIR)

    # Export CSVs
    print("\nExporting CSV results...")
    results["state_summary"].to_csv(os.path.join(OUTPUT_DIR, "state_breakdown.csv"), index=False)

    decile_df = pd.DataFrame({
        "decile": list(range(1, 11)),
        "baseline_share": results["baseline"]["decile_shares"],
        "doubled_share": results["doubled"]["decile_shares"],
        "ubi_share": results["ubi"]["decile_shares"],
    })
    decile_df.to_csv(os.path.join(OUTPUT_DIR, "decile_shares.csv"), index=False)
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
