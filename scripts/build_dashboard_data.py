"""Generate data/calibration.json for the populace.dev dashboard.

Every number on the dashboard is computed here from the build artifacts —
the raw PE-native target surface, the shipped (bounded) weights, and the
preserved unbounded run — plus the sound-comparison result JSON when it
exists. Nothing is hand-typed into the page.

Run with any python that has numpy + h5py:

    /tmp/populace-build-venv/bin/python scripts/build_dashboard_data.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path


import numpy as np

ART = Path("/Users/maxghenis/.claude-worktrees/microplex-spec-build/artifacts")
SCORE_JSON = Path.home() / "populace-score-work" / "score_out" / (
    "sound_ecps_replacement_comparison.json"
)
RELEASE = "us-2024-20260611"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT = DATA_DIR / "calibration.json"  # alias of the latest release
ECPS = Path(
    "/Users/maxghenis/CosilicoAI/microplex-us/artifacts/baselines/"
    "enhanced_cps_2024_hf_main.h5"
)
POP_TP = ART / "populace_us_2024_v2_timeperiod.h5"


def loss_and_hits(A: np.ndarray, b: np.ndarray, w: np.ndarray):
    est = w @ A
    rel = (est - b) / (b + 1.0)
    loss = float((rel**2).mean())
    miss = np.abs(est - b)
    within = np.where(b != 0, miss <= 0.10 * np.abs(b), miss <= 0.10)
    abs_rel = np.where(b != 0, miss / np.abs(b), miss)
    return est, loss, within, abs_rel


def family_of(name: str) -> str:
    parts = name.split("/")
    if len(parts) >= 3 and parts[0] == "nation":
        return f"{parts[1]} · {parts[2]}"
    if len(parts) >= 2:
        return f"{parts[0]} · {parts[1]}"
    return name


WORKTREE = Path("/Users/maxghenis/.claude-worktrees/microplex-spec-build")


def _parse_list(src: str, name: str) -> set[str]:
    """Extract quoted strings from a `NAME = (...)` or `NAME = [...]` block."""
    import re

    m = re.search(rf"{name}\s*[:=].*?[\(\[{{](.*?)[\)\]}}]", src, re.S)
    if not m:
        return set()
    return set(re.findall(r'"([a-z0-9_]+)"', m.group(1)))


def build_source_map() -> dict[str, str]:
    """Variable -> source family, parsed from the build scripts (never typed)."""
    import re

    driver = (WORKTREE / "scripts" / "build_us_candidate.py").read_text()
    donor = (WORKTREE / "scripts" / "primary_source_impute.py").read_text()
    src_map: dict[str, str] = {}
    # CPS-derived: p["..."] assignments in _derive_person_columns + tenure map.
    body = driver.split("def _derive_person_columns", 1)[-1].split("\ndef ", 1)[0]
    for var in re.findall(r'p\["([a-z0-9_]+)"\]', body):
        src_map[var] = "cps-derived"
    src_map["tenure_type"] = "cps-derived"
    for var in _parse_list(driver, "PERSON_INCOME_COLUMNS"):
        src_map[var] = "cps-carried"
    donor_to_pe = dict(
        re.findall(r'"([a-z0-9_]+)":\s*"([a-z0-9_]+)"', driver.split("DONOR_TO_PE", 1)[-1].split("}", 1)[0])
    )
    for var in _parse_list(driver, "PUF_IMPUTE_VARS"):
        src_map[donor_to_pe.get(var, var)] = "puf-imputed"
    for var in _parse_list(donor, "PERSON_TARGETS") | _parse_list(donor, "HOUSEHOLD_TARGETS"):
        src_map[var] = "ecps-donor-imputed"
    for var in _parse_list(driver, "V1_ZERO_DEFAULTS"):
        src_map.setdefault(var, "zero-default")
    return src_map


def _profile_flat(path):
    """Per-variable (entity_n, fill, weighted_total) from a flat h5."""
    import h5py

    out = {}
    with h5py.File(path) as f:
        hw = f["household_weight/2024"][:].astype(np.float64)
        phh = f["person_household_id/2024"][:]
        hid = f["household_id/2024"][:]
        wmap = dict(zip(hid.tolist(), hw.tolist()))
        pw = np.fromiter(
            (wmap.get(h, 0.0) for h in phh.tolist()), dtype=np.float64
        )
        for k in f:
            g = f[k]
            if "2024" not in g:
                continue
            v = g["2024"][:]
            if v.dtype.kind not in "fiu":
                out[k] = (len(v), None, None)
                continue
            v = v.astype(np.float64)
            wt = (
                float((v * pw).sum())
                if len(v) == len(pw)
                else (float((v * hw).sum()) if len(v) == len(hw) else None)
            )
            out[k] = (len(v), float((v != 0).mean()), wt)
    return out


def build_lineage():
    """Variable-level lineage: populace vs eCPS fill and weighted totals."""
    pop = _profile_flat(POP_TP)
    ecps = _profile_flat(ECPS)
    sources = build_source_map()
    rows = []
    for var in sorted(set(pop) | set(ecps)):
        if var.endswith("_id") or "weight" in var:
            continue
        p_n, p_fill, p_wt = pop.get(var, (None, None, None))
        e_n, e_fill, e_wt = ecps.get(var, (None, None, None))
        if p_fill is None and e_fill is None:
            continue
        alive_p = (p_fill or 0) > 1e-9
        alive_e = (e_fill or 0) > 0.005
        status = (
            "live" if alive_p else ("gap" if alive_e else "degenerate-both")
        )
        rows.append(
            {
                "variable": var,
                "fill": round(p_fill, 4) if p_fill is not None else None,
                "total_B": round((p_wt or 0) / 1e9, 2) if p_wt is not None else None,
                "ecps_fill": round(e_fill, 4) if e_fill is not None else None,
                "ecps_total_B": round((e_wt or 0) / 1e9, 2) if e_wt is not None else None,
                "status": status,
                "source": sources.get(var, "spec/structural"),
            }
        )
    rows.sort(key=lambda r: -abs(r["ecps_total_B"] or 0))
    return rows


def main() -> None:
    surf = np.load(ART / "target_surface_raw.npz", allow_pickle=True)
    A = surf["A"].astype(np.float64)
    b = surf["b"].astype(np.float64)
    w0 = surf["w0"].astype(np.float64)
    names = [str(x) for x in surf["names"]]

    bounded = np.load(ART / "populace_us_2024_v2_calibration.npz")["calibrated_weights"].astype(np.float64)
    # v2 was calibrated bounded from the start; the unbounded cautionary row
    # is the preserved v1 experiment (same pool family, same surface design).
    unbounded = np.load(ART / "populace_us_2024_calibration_unbounded.npz")[
        "calibrated_weights"
    ].astype(np.float64)

    # The artifact is a pandas-HDF5 USSingleYearDataset; count rows through
    # the engine's own loader rather than poking at the pytables layout.
    from policyengine_us.data import USSingleYearDataset

    ds = USSingleYearDataset(file_path=str(ART / "populace_us_2024.h5"))
    n_persons = len(ds.person)
    n_households = len(ds.household)
    assert n_households == len(bounded)
    # The represented (weighted) population: each person carries their
    # household's calibrated weight.
    hh_ids = ds.household["household_id"].to_numpy()
    weight_of = dict(zip(hh_ids.tolist(), bounded.tolist()))
    person_hh = ds.person["person_household_id"].to_numpy()
    weighted_persons = float(
        np.fromiter((weight_of[h] for h in person_hh.tolist()), dtype=np.float64).sum()
    )

    _, loss0, within0, _ = loss_and_hits(A, b, w0)
    est, loss, within, abs_rel = loss_and_hits(A, b, bounded)
    # The preserved unbounded run belongs to the v1 pool; it only evaluates
    # on a surface of matching size.
    if len(unbounded) == len(w0):
        _, loss_unb, within_unb, _ = loss_and_hits(A, b, unbounded)
    else:
        loss_unb, within_unb = None, None

    # Per-family fit, sorted by target count.
    families: dict[str, dict] = {}
    fams = [family_of(n) for n in names]
    for i, fam in enumerate(fams):
        f = families.setdefault(fam, {"n": 0, "hits": 0, "errs": []})
        f["n"] += 1
        f["hits"] += int(within[i])
        f["errs"].append(float(abs_rel[i]))
    family_rows = sorted(
        (
            {
                "family": fam,
                "n": f["n"],
                "within10": round(f["hits"] / f["n"], 4),
                "median_abs_rel_err": round(float(np.median(f["errs"])), 4),
            }
            for fam, f in families.items()
        ),
        key=lambda r: -r["n"],
    )

    # |relative error| histogram over fixed buckets.
    edges = [0, 0.01, 0.025, 0.05, 0.10, 0.25, 0.50, np.inf]
    labels = ["<1%", "1–2.5%", "2.5–5%", "5–10%", "10–25%", "25–50%", ">50%"]
    hist = [
        int(((abs_rel >= lo) & (abs_rel < hi)).sum())
        for lo, hi in zip(edges[:-1], edges[1:])
    ]

    worst_idx = np.argsort(-abs_rel)[:15]
    worst = [
        {
            "name": names[i],
            "target": float(b[i]),
            "estimate": float(est[i]),
            "abs_rel_err": round(float(abs_rel[i]), 3),
        }
        for i in worst_idx
    ]

    def wstats(w: np.ndarray) -> dict:
        return {
            "sum_M": round(float(w.sum()) / 1e6, 2),
            "p50": round(float(np.percentile(w, 50))),
            "p99": round(float(np.percentile(w, 99))),
            "max": round(float(w.max())),
            "n_gt_100k": int((w > 1e5).sum()),
            "n_gt_500k": int((w > 5e5).sum()),
        }

    score: dict = {"status": "running"}
    if SCORE_JSON.exists():
        raw = json.loads(SCORE_JSON.read_text())
        cr, br = raw["candidate_refit"], raw["baseline_refit"]
        summ = raw.get("target_diagnostics", {}).get("summary", {})
        score = {
            "status": "complete",
            "matched_households": cr.get("household_count"),
            "candidate": {
                "train_loss": round(cr["optimized_train_loss"], 4),
                "holdout_loss": round(cr["optimized_holdout_loss"], 4),
                "full_loss": round(cr["optimized_full_loss"], 4),
            },
            "baseline": {
                "train_loss": round(br["optimized_train_loss"], 4),
                "holdout_loss": round(br["optimized_holdout_loss"], 4),
                "full_loss": round(br["optimized_full_loss"], 4),
            },
            "per_target": {
                "candidate_wins": summ.get("candidate_wins"),
                "baseline_wins": summ.get("baseline_wins"),
                "ties": summ.get("ties"),
                "n_targets": summ.get("n_targets"),
                "holdout_targets": summ.get("holdout_targets"),
            },
        }

    payload = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
        "headline": {
            "n_targets": len(names),
            "n_households": n_households,
            "n_persons": n_persons,
            "weighted_persons": round(weighted_persons),
            "loss_initial": round(loss0, 4),
            "loss_final": round(loss, 4),
            "within10_initial": round(float(within0.mean()), 4),
            "within10_final": round(float(within.mean()), 4),
            "within10_unbounded": (
                round(float(within_unb.mean()), 4) if within_unb is not None else None
            ),
            "loss_unbounded": round(loss_unb, 4) if loss_unb is not None else None,
            "max_weight_ratio": 50,
        },
        "weights": {
            "design": wstats(w0),
            **(
                {"unbounded": wstats(unbounded)}
                if len(unbounded) == len(w0)
                else {}
            ),
            "bounded": wstats(bounded),
        },
        "histogram": {"labels": labels, "counts": hist},
        "families": family_rows,
        "worst": worst,
        "score": score,
        "stages": [
            {
                "key": "pool",
                "title": "pool",
                "status": "done",
                "note": f"{n_households:,} households · {n_persons:,} persons, "
                "spec-built from CPS ASEC + IRS PUF",
            },
            {
                "key": "fit",
                "title": "fit",
                "status": "done",
                "note": "weight-aware regime-gated quantile forests "
                "(weighted bootstrap)",
            },
            {
                "key": "calibrate",
                "title": "calibrate",
                "status": "done",
                "note": f"{len(names):,} targets · loss {loss0:.2f} → {loss:.3f} "
                f"· hard {50}× weight bound",
            },
            {
                "key": "score",
                "title": "score",
                "status": score["status"],
                "note": "matched-sample, symmetric-refit comparison vs the "
                "enhanced CPS",
            },
            {
                "key": "publish",
                "title": "publish",
                "status": "pending",
                "note": "Hugging Face artifact + populace.data registry entry",
            },
        ],
    }
    payload["release"] = RELEASE
    payload["lineage"] = build_lineage()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    releases_dir = DATA_DIR / "releases"
    releases_dir.mkdir(parents=True, exist_ok=True)
    (releases_dir / f"{RELEASE}.json").write_text(json.dumps(payload, indent=1))
    known = sorted(
        f.stem for f in releases_dir.glob("*.json") if f.stem != "index"
    )
    (releases_dir / "index.json").write_text(json.dumps(known))
    OUT.write_text(json.dumps(payload, indent=1))
    print(f"wrote {OUT} ({OUT.stat().st_size/1024:.0f} KB)")
    print(
        f"headline: {len(names)} targets, within10 {within.mean()*100:.2f}%, "
        f"loss {loss0:.3f}->{loss:.4f}"
    )


if __name__ == "__main__":
    main()
