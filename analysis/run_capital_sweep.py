"""Entry point: python -m analysis.run_capital_sweep"""

import os

import pandas as pd

from .capital_share_sweep import run_sweep
from .sweep_charts import generate_all as generate_charts

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs", "capital_sweep")


def main():
    results = run_sweep()

    # Build results DataFrame
    rows = results["rows"]
    df = pd.DataFrame([{
        "multiplier": r["multiplier"],
        "capital_share": r["capital_share"],
        "label": r["label"],
        "market_gini": r["market_gini"],
        "net_gini": r["net_gini"],
        "spm_poverty_rate": r["spm_poverty_rate"],
        "fed_revenue": r["fed_revenue"],
        "state_revenue": r["state_revenue"],
        "total_revenue": r["total_revenue"],
        "mean_net_income": r["mean_net_income"],
        "top_10_share": r["top_10_share"],
        "bottom_10_share": r["bottom_10_share"],
        "top_20_share": r["top_20_share"],
        "bottom_20_share": r["bottom_20_share"],
    } for r in rows])

    # Print summary
    print("\n" + "=" * 90)
    print("CAPITAL INCOME SWEEP: 1x -> 5x (positive-only)")
    print("=" * 90)

    display = df[["label", "capital_share", "net_gini", "market_gini",
                   "spm_poverty_rate", "top_10_share", "bottom_10_share"]].copy()
    display["capital_share"] = display["capital_share"].map("{:.1%}".format)
    display["net_gini"] = display["net_gini"].map("{:.4f}".format)
    display["market_gini"] = display["market_gini"].map("{:.4f}".format)
    display["spm_poverty_rate"] = display["spm_poverty_rate"].map("{:.2%}".format)
    display["top_10_share"] = display["top_10_share"].map("{:.2%}".format)
    display["bottom_10_share"] = display["bottom_10_share"].map("{:.2%}".format)
    display.columns = ["Scenario", "Cap share", "Net Gini", "Mkt Gini",
                        "Poverty", "Top 10%", "Bot 10%"]
    print(display.to_string(index=False))

    # Revenue detail
    print("\n" + "-" * 60)
    print("REVENUE")
    print("-" * 60)
    baseline_rev = rows[0]["total_revenue"]
    for r in rows:
        extra = r["total_revenue"] - baseline_rev
        sign = "+" if extra >= 0 else ""
        print(f"  {r['label']:>10s}  "
              f"Fed: ${r['fed_revenue']/1e9:>8,.1f}B  "
              f"State: ${r['state_revenue']/1e9:>7,.1f}B  "
              f"Extra: {sign}${extra/1e9:,.1f}B")

    # Decile detail for baseline vs 2x vs 5x
    print("\n" + "-" * 60)
    print("DECILE SHARES (baseline vs 2x vs 5x)")
    print("-" * 60)
    decile_rows = []
    for r in rows:
        if r["multiplier"] in (1.0, 2.0, 5.0):
            for i, share in enumerate(r["decile_shares"]):
                decile_rows.append({
                    "scenario": r["label"],
                    "decile": f"D{i+1}",
                    "share": share,
                })
    dec_df = pd.DataFrame(decile_rows).pivot(
        index="decile", columns="scenario", values="share"
    )
    dec_df = dec_df[["Baseline", "2x", "5x"]]
    print(dec_df.to_string(float_format="{:.2%}".format))

    # Charts
    print("\nGenerating visualizations...")
    generate_charts(results, OUTPUT_DIR)

    # Export
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"\nExporting to {OUTPUT_DIR}/...")
    df.to_csv(os.path.join(OUTPUT_DIR, "sweep_metrics.csv"), index=False)

    decile_data = {"decile": list(range(1, 11))}
    for r in rows:
        key = r["label"].replace(".", "p")
        decile_data[key] = r["decile_shares"]
    pd.DataFrame(decile_data).to_csv(
        os.path.join(OUTPUT_DIR, "sweep_deciles.csv"), index=False
    )

    print("Done!")


if __name__ == "__main__":
    main()
