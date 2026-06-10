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
OUT = Path(__file__).resolve().parent.parent / "data" / "calibration.json"


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


def main() -> None:
    surf = np.load(ART / "v5_target_surface_raw.npz", allow_pickle=True)
    A = surf["A"].astype(np.float64)
    b = surf["b"].astype(np.float64)
    w0 = surf["w0"].astype(np.float64)
    names = [str(x) for x in surf["names"]]

    bounded = np.load(ART / "bounded_recal_w_ratio50.npy").astype(np.float64)
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
    _, loss_unb, within_unb, _ = loss_and_hits(A, b, unbounded)

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
        score = {"status": "complete", "raw": raw}

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
            "within10_unbounded": round(float(within_unb.mean()), 4),
            "loss_unbounded": round(loss_unb, 4),
            "max_weight_ratio": 50,
        },
        "weights": {
            "design": wstats(w0),
            "unbounded": wstats(unbounded),
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
                "spec-built from CPS ASEC + IRS PUF + SCF",
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
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1))
    print(f"wrote {OUT} ({OUT.stat().st_size/1024:.0f} KB)")
    print(
        f"headline: {len(names)} targets, within10 {within.mean()*100:.2f}%, "
        f"loss {loss0:.3f}->{loss:.4f}"
    )


if __name__ == "__main__":
    main()
