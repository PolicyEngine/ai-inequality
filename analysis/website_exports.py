"""Serialization helpers for website data files."""

from importlib.metadata import PackageNotFoundError, version

LABOR_SHIFT_DESCRIPTION = (
    "Employment and self-employment income reduced by X%, redistributed to "
    "capital income proportional to existing holdings while modeled market "
    "income stays constant. Website resource metrics count the cash-equivalent "
    "value of Medicaid, CHIP, and ACA premium support in household resources."
)


def _package_version(package_name):
    try:
        return version(package_name)
    except PackageNotFoundError:
        return None


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
        "healthcareBenefitValue": _to_billions(row["healthcare_benefit_value_total"]),
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
            "policyengine_version": _package_version("policyengine"),
            "version_note": (
                "Generated with PolicyEngine "
                f"{_package_version('policyengine') or 'version unavailable'}."
            ),
        },
    }


AI_SCENARIO_DESCRIPTION = (
    "AI scenarios calibrated to the Karger et al. (2026) forecaster survey as "
    "implemented by The Budget Lab. Labor and capital income grow at "
    "scenario-specific rates implied by a 2030 labor-share target, with an "
    "optional change in the spread of labor income. Static current-law "
    "microsimulation of the household sector: no behavioural response and no "
    "corporate income tax."
)


def _serialize_ai_scenario_row(row):
    """Convert one scenario result row into the website JSON shape."""
    scenario = row["scenario"]
    diagnostics = row.get("diagnostics", {})
    serialized = {
        "name": scenario.get("name"),
        "label": scenario.get("label"),
        "inequality": scenario.get("inequality"),
        "holdSharesFixed": scenario.get("hold_shares_fixed"),
        "realizationRate": scenario.get("realization_rate"),
        "annualGdpGrowth": scenario.get("annual_gdp_growth"),
        "targetLaborShare": scenario.get("target_labor_share"),
        "gdpGrowth": scenario.get("gdp_growth"),
        "capitalGrowth": scenario.get("capital_growth"),
        "laborGrowth": scenario.get("labor_growth"),
        "inequalityLambda": scenario.get("inequality_lambda"),
        "laborCrossoverIncome": diagnostics.get("labor_crossover_income"),
        "revenueChange": row.get("total_rev_change_b"),
        "incomeTaxChange": row.get("fed_income_tax_change_b"),
        "payrollChange": row.get("payroll_change_b"),
        "capitalGainsTaxChange": row.get("fed_capital_gains_tax_change_b"),
        "benefitsChange": row.get("benefits_change_b"),
        "refundableCreditsChange": row.get("refundable_credits_change_b"),
        "stateTaxChange": row.get("state_tax_change_b"),
        "snapChange": row.get("snap_change_b"),
        "eitcChange": row.get("eitc_change_b"),
        "marketIncomeChange": row.get("market_income_change_b"),
        "netIncomeChange": row.get("net_income_change_b"),
        "povertyRate": row.get("spm_poverty_rate"),
        "netGini": row.get("net_gini"),
        "marketGini": row.get("market_gini"),
        "netTop1Share": row.get("net_top_1_share"),
        "netTop10Share": row.get("net_top_10_share"),
        "netBottom20Share": row.get("net_bottom_20_share"),
        "decileShares": row.get("decile_shares"),
    }
    return {key: value for key, value in serialized.items() if value is not None}


def ai_scenarios_website_payload(result):
    """Convert `compute_ai_scenarios.run_ai_scenarios` output for the website.

    Poverty and Gini are carried as changes against the same-year baseline as
    well as levels, because the levels alone invite comparison against
    published poverty statistics built on a different baseline.
    """
    baseline = result["baseline"]
    baseline_poverty = baseline.get("spm_poverty_rate")
    baseline_gini = baseline.get("net_gini")

    def with_deltas(row):
        serialized = _serialize_ai_scenario_row(row)
        if baseline_poverty is not None and "povertyRate" in serialized:
            serialized["povertyRateChange"] = (
                serialized["povertyRate"] - baseline_poverty
            )
        if baseline_gini is not None and "netGini" in serialized:
            serialized["netGiniChange"] = serialized["netGini"] - baseline_gini
        return serialized

    metadata = dict(result.get("metadata", {}))
    return {
        "year": result["year"],
        "baseline": {
            "povertyRate": baseline_poverty,
            "netGini": baseline_gini,
            "marketGini": baseline.get("market_gini"),
            "netTop1Share": baseline.get("net_top_1_share"),
            "decileShares": baseline.get("decile_shares"),
            "context": baseline.get("context", {}),
        },
        "scenarios": [with_deltas(row) for row in result.get("scenarios", [])],
        "sensitivities": {
            key: [with_deltas(row) for row in rows]
            for key, rows in (result.get("sensitivities") or {}).items()
        },
        "metadata": {
            "year": result["year"],
            "description": AI_SCENARIO_DESCRIPTION,
            "corporateTaxScopeNote": metadata.get("corporate_tax_scope_note"),
            "policyengineVersion": metadata.get("policyengine_version"),
            "countryModelPackage": metadata.get("country_model_package"),
            "countryModelVersion": metadata.get("country_model_version"),
            "dataPackage": metadata.get("data_package"),
            "dataVersion": metadata.get("data_version"),
            "datasetName": metadata.get("dataset_name"),
            "certifiedDataBuildId": metadata.get("certified_data_build_id"),
            "capitalIncomeVars": metadata.get("capital_income_vars"),
        },
    }
