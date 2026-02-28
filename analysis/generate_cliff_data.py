"""Generate capital income cliff data as JSON for the React app."""

import json
import os
import numpy as np
from policyengine_us import Simulation

from .constants import YEAR


def make_situation(capital_income, capital_type):
    return {
        "people": {
            "parent": {
                "age": {YEAR: 30},
                "employment_income": {YEAR: 7.25 * 2080},
                capital_type: {YEAR: capital_income},
            },
            "child": {"age": {YEAR: 5}},
        },
        "tax_units": {"tax_unit": {"members": ["parent", "child"]}},
        "spm_units": {"spm_unit": {"members": ["parent", "child"]}},
        "families": {"family": {"members": ["parent", "child"]}},
        "households": {
            "household": {
                "members": ["parent", "child"],
                "state_code": {YEAR: "TX"},
            },
        },
        "marital_units": {"marital_unit": {"members": ["parent"]}},
    }


def compute_series(capital_type, max_cap=30_000, steps=200):
    cap_values = np.linspace(0, max_cap, steps)
    results = []

    for cap in cap_values:
        sim = Simulation(situation=make_situation(float(cap), capital_type))
        results.append({
            "capitalIncome": round(float(cap), 0),
            "netIncome": round(float(sim.calculate("household_net_income", YEAR).sum()), 0),
            "eitc": round(float(sim.calculate("eitc", YEAR).sum()), 0),
            "snap": round(float(sim.calculate("snap", YEAR).sum()), 0),
            "incomeTax": round(float(sim.calculate("income_tax", YEAR).sum()), 0),
            "ssi": round(float(sim.calculate("ssi", YEAR).sum()), 0),
        })

    return results


if __name__ == "__main__":
    output_path = os.path.join(
        os.path.dirname(__file__), "..", "src", "data", "cliffData.json"
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    data = {}
    for cap_type, key in [
        ("qualified_dividend_income", "dividends"),
        ("long_term_capital_gains", "ltcg"),
    ]:
        print(f"Computing {key}...")
        data[key] = compute_series(cap_type)

    data["household"] = {
        "description": "Single parent, 1 child, federal minimum wage ($15,080/yr), Texas",
        "year": YEAR,
    }

    with open(output_path, "w") as f:
        json.dump(data, f)

    print(f"Saved to {output_path}")
