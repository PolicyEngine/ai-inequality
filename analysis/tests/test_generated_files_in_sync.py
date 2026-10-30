"""Every generated file must be what its generator makes from the committed run.

The site payload, the state exposure deltas and the paper's values and tables
are regenerated from ``analysis/outputs/ai_scenarios.json`` by repo code. These
tests regenerate them (or recompute their deltas) and compare with the
committed copies, so a rerun cannot ship next to stale derived files. The two
Budget Lab workbooks are pinned to the git blobs of AI-Fiscal's own copies.
"""

import filecmp
import hashlib
import json
from pathlib import Path

import pytest

from analysis.website_exports import ai_scenarios_website_payload

ROOT = Path(__file__).resolve().parents[2]
OUTPUTS = ROOT / "analysis" / "outputs"

#: Git blob ids of AI-Fiscal's ``results/aggregates/ai_fiscal_publishable_2030_latest.xlsx``:
#: v1.0.1 (also at 1c25162c9aae, equal to run D of results/erratum_v1.0.1) and
#: the copy at their tag v1.0.0 (53a92aa61c2d).
WORKBOOK_BLOBS = {
    "yale_publishable_2030.xlsx": "b4cdf12c8f7b0fbc6064d59647521451f86f0e88",
    "yale_publishable_2030_v1_0_0.xlsx": "3090e94d86cad2fe7f1bf8f9271248c7afef6981",
}


def _git_blob_id(path):
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


@pytest.fixture(scope="module")
def run():
    return json.loads((OUTPUTS / "ai_scenarios.json").read_text())


def test_site_payload_is_the_run(run):
    committed = json.loads((ROOT / "src" / "data" / "aiScenariosData.json").read_text())
    regenerated = json.loads(json.dumps(ai_scenarios_website_payload(run), default=float))
    assert committed == regenerated


def test_state_exposure_deltas_are_the_runs(run):
    exposure = json.loads((ROOT / "src" / "data" / "stateExposureData.json").read_text())
    assert exposure["metadata"]["certified_data_build_id"] == (
        run["metadata"]["certified_data_build_id"]
    )
    rapid = {
        row["scenario"]["inequality"]: row["state_deltas"]
        for row in run["scenarios"]
        if row["scenario"]["name"] == "Rapid" and not row["scenario"]["hold_shares_fixed"]
    }
    checked = 0
    for state in exposure["states"]:
        for variant, delta in state["deltas_b"].items():
            assert delta == pytest.approx(
                rapid[variant][state["state"]]["state_net_change_b"], abs=1e-12
            ), (state["state"], variant)
            checked += 1
    assert checked == 3 * len(exposure["states"])


@pytest.mark.parametrize("name", sorted(WORKBOOK_BLOBS))
def test_budget_lab_workbooks_are_their_committed_copies(name):
    assert _git_blob_id(OUTPUTS / name) == WORKBOOK_BLOBS[name]


def test_paper_values_and_tables_regenerate_identically(tmp_path):
    pytest.importorskip("openpyxl")
    from analysis.emit_paper_values import main

    main(paper_dir=str(tmp_path))
    for name in ("values_generated.tex", "tables_generated.tex"):
        assert filecmp.cmp(tmp_path / name, ROOT / "paper" / name, shallow=False), name
