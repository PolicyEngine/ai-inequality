"""Entry point: python -m analysis.run_capital_sweep"""

import os

import pandas as pd

from .capital_share_sweep import run_sweep

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs", "capital_sweep")


def _build_df(rows):
    return pd.DataFrame([{
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


def _print_summary(df, rows, title):
    print("\n" + "=" * 90)
    print(title)
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


def main():
    # Run both variants
    print("=" * 90)
    print("VARIANT 1: ALL CAPITAL INCOME (gains AND losses scaled)")
    print("=" * 90)
    results_all = run_sweep(positive_only=False)

    print("\n" + "=" * 90)
    print("VARIANT 2: POSITIVE-ONLY (gains scaled, losses unchanged)")
    print("=" * 90)
    results_pos = run_sweep(positive_only=True)

    rows_all = results_all["rows"]
    rows_pos = results_pos["rows"]
    df_all = _build_df(rows_all)
    df_pos = _build_df(rows_pos)

    _print_summary(df_all, rows_all, "ALL CAPITAL INCOME SWEEP: 1x -> 5x")
    _print_summary(df_pos, rows_pos, "POSITIVE-ONLY CAPITAL INCOME SWEEP: 1x -> 5x")

    # Side-by-side comparison at key multipliers
    print("\n" + "=" * 90)
    print("COMPARISON: ALL vs POSITIVE-ONLY")
    print("=" * 90)
    compare_mults = [1.0, 2.0, 3.0, 5.0]
    comp_rows = []
    for mult in compare_mults:
        r_all = next(r for r in rows_all if r["multiplier"] == mult)
        r_pos = next(r for r in rows_pos if r["multiplier"] == mult)
        comp_rows.append({
            "Mult": r_all["label"],
            "Net Gini (all)": f"{r_all['net_gini']:.4f}",
            "Net Gini (pos)": f"{r_pos['net_gini']:.4f}",
            "Poverty (all)": f"{r_all['spm_poverty_rate']:.2%}",
            "Poverty (pos)": f"{r_pos['spm_poverty_rate']:.2%}",
            "Bot 10% (all)": f"{r_all['bottom_10_share']:.2%}",
            "Bot 10% (pos)": f"{r_pos['bottom_10_share']:.2%}",
            "Revenue (all)": f"${r_all['total_revenue']/1e9:,.1f}B",
            "Revenue (pos)": f"${r_pos['total_revenue']/1e9:,.1f}B",
        })
    print(pd.DataFrame(comp_rows).to_string(index=False))

    # Decile detail for baseline vs 2x vs 5x (both variants)
    print("\n" + "-" * 60)
    print("DECILE SHARES: ALL vs POSITIVE-ONLY at 5x")
    print("-" * 60)
    r5_all = next(r for r in rows_all if r["multiplier"] == 5.0)
    r5_pos = next(r for r in rows_pos if r["multiplier"] == 5.0)
    r_base = next(r for r in rows_all if r["multiplier"] == 1.0)
    dec_compare = pd.DataFrame({
        "Decile": [f"D{i+1}" for i in range(10)],
        "Baseline": [f"{s:.2%}" for s in r_base["decile_shares"]],
        "5x All": [f"{s:.2%}" for s in r5_all["decile_shares"]],
        "5x Pos-only": [f"{s:.2%}" for s in r5_pos["decile_shares"]],
    })
    print(dec_compare.to_string(index=False))

    # Export
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"\nExporting to {OUTPUT_DIR}/...")
    df_all.to_csv(os.path.join(OUTPUT_DIR, "sweep_metrics_all.csv"), index=False)
    df_pos.to_csv(os.path.join(OUTPUT_DIR, "sweep_metrics_positive_only.csv"), index=False)

    for suffix, rows in [("all", rows_all), ("positive_only", rows_pos)]:
        decile_data = {"decile": list(range(1, 11))}
        for r in rows:
            key = r["label"].replace(".", "p")
            decile_data[key] = r["decile_shares"]
        pd.DataFrame(decile_data).to_csv(
            os.path.join(OUTPUT_DIR, f"sweep_deciles_{suffix}.csv"), index=False
        )

    print("Done!")


if __name__ == "__main__":
    main()
