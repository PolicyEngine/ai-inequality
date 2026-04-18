"""Serialization helpers for website data files."""

LABOR_SHIFT_DESCRIPTION = (
    "Employment and self-employment income reduced by X%, redistributed to "
    "capital income proportional to existing holdings while modeled market "
    "income stays constant. Website resource metrics count the cash-equivalent "
    "value of Medicaid, CHIP, and ACA premium support in household resources."
)


def _to_billions(amount):
    return amount / 1e9


def _serialize_labor_shift_row(row, shift_pct):
    serialized = {
        "label": row["label"],
        "shiftPct": shift_pct,
        "marketGini": row["market_gini"],
        "netGini": row["net_gini_including_health_benefits"],
        "standardNetGini": row["net_gini"],
        "povertyRate": row["spm_poverty_rate"],
        "fedRevenue": _to_billions(row["fed_revenue"]),
        "stateRevenue": _to_billions(row["state_revenue"]),
        "totalRevenue": _to_billions(row["total_revenue"]),
        "top10Share": row["top_10_share_including_health_benefits"],
        "bottom10Share": row["bottom_10_share_including_health_benefits"],
        "meanNetIncome": row["mean_net_income_including_health_benefits"],
        "standardMeanNetIncome": row["mean_net_income"],
        "healthcareBenefitValue": _to_billions(
            row["healthcare_benefit_value_total"]
        ),
        "medicaidBenefits": _to_billions(row["medicaid_cost_total"]),
        "chipBenefits": _to_billions(row["chip_benefit_total"]),
        "acaBenefits": _to_billions(row["aca_ptc_total"]),
    }
    if "ubi_per_person" in row:
        serialized["ubiPerPerson"] = row["ubi_per_person"]
    return serialized


def labor_shift_website_payload(results):
    """Convert labor-shift analysis output into the website JSON shape."""
    scenarios = [_serialize_labor_shift_row(results["baseline"], 0)]
    deciles = {
        "labels": [f"D{i}" for i in range(1, 11)],
        "baseline": list(
            results["baseline"]["decile_shares_including_health_benefits"]
        ),
    }

    last_shift_pct = 0
    for row in results["shifts"]:
        shift_pct = int(round(row["shift_pct"] * 100))
        last_shift_pct = shift_pct
        scenarios.append(_serialize_labor_shift_row(row, shift_pct))
        deciles[f"{shift_pct}pctShift"] = list(
            row["decile_shares_including_health_benefits"]
        )

    ubi = results.get("ubi")
    if ubi is not None:
        scenarios.append(_serialize_labor_shift_row(ubi, last_shift_pct))
        deciles[f"{last_shift_pct}pctUBI"] = list(
            ubi["decile_shares_including_health_benefits"]
        )

    return {
        "scenarios": scenarios,
        "deciles": deciles,
        "metadata": {
            "year": results["meta"]["year"],
            "description": LABOR_SHIFT_DESCRIPTION,
            "ubiScenarioAvailable": ubi is not None,
        },
    }
