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
import os
import re
import time
from pathlib import Path


import numpy as np

ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_DIR_ENV = "POPULACE_ARTIFACT_DIR"
SCORE_JSON_ENV = "POPULACE_SCORE_JSON"
REFERENCE_H5_ENV = "POPULACE_REFERENCE_H5"
TIMEPERIOD_H5_ENV = "POPULACE_TIMEPERIOD_H5"
REPO_DIR_ENV = "POPULACE_REPO_DIR"

ART = Path(os.environ.get(ARTIFACT_DIR_ENV, ROOT / "output"))
SCORE_JSON = Path(
    os.environ.get(
        SCORE_JSON_ENV,
        Path.home()
        / "populace-score-work"
        / "score_out"
        / "sound_ecps_replacement_comparison.json",
    )
)
RELEASE = "populace-us-2024-5da5a95-20260611"
DATA_DIR = ROOT / "data"
OUT = DATA_DIR / "calibration.json"  # alias of the latest release
REFERENCE_H5 = (
    Path(os.environ[REFERENCE_H5_ENV]) if os.environ.get(REFERENCE_H5_ENV) else None
)
POP_TP = Path(os.environ.get(TIMEPERIOD_H5_ENV, ART / "populace_us_2024_timeperiod.h5"))


def loss_and_hits(A: np.ndarray, b: np.ndarray, w: np.ndarray):
    est = w @ A
    rel = (est - b) / (b + 1.0)
    loss = float((rel**2).mean())
    miss = np.abs(est - b)
    within = np.where(b != 0, miss <= 0.10 * np.abs(b), miss <= 0.10)
    abs_rel = np.where(b != 0, miss / np.abs(b), miss)
    return est, loss, within, abs_rel


#: 2-letter postal codes that appear as the trailing geography of a state row.
_STATE_ABBRS = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO",
    "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA",
    "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "US",
}
_FIPS_TO_ABBR = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO",
    "09": "CT", "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI",
    "16": "ID", "17": "IL", "18": "IN", "19": "IA", "20": "KS", "21": "KY",
    "22": "LA", "23": "ME", "24": "MD", "25": "MA", "26": "MI", "27": "MN",
    "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
    "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH",
    "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD",
    "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA",
    "54": "WV", "55": "WI", "56": "WY",
}


def parse_target(name: str) -> dict[str, str]:
    """Decompose a target row into structured criteria.

    The surface persists targets as slash-joined strings under three
    conventions (``state/<source>/<variable>/<ABBR>``,
    ``nation/<source>/<variable>[/<dims>]``, ``US<fips>/<metric>``). This
    reconstructs the geography / source / variable / breakdown fields so the
    page never displays the raw slash string. The durable fix is for the
    surface to carry these as real columns (the registry already knows them).
    """
    parts = name.split("/")
    p0 = parts[0]
    fips = re.match(r"^US(\d{2})$", p0)
    if fips:
        return {
            "geography": _FIPS_TO_ABBR.get(fips.group(1), p0),
            "level": "state",
            "source": "admin",
            "variable": parts[1] if len(parts) > 1 else "",
            "breakdown": " · ".join(parts[2:]),
        }
    if p0 == "state":
        if len(parts) >= 4 and parts[-1] in _STATE_ABBRS:
            return {
                "geography": parts[-1],
                "level": "state",
                "source": parts[1],
                "variable": parts[2],
                "breakdown": " · ".join(parts[3:-1]),
            }
        return {
            "geography": "state",
            "level": "state",
            "source": parts[1] if len(parts) > 1 else "",
            "variable": parts[2] if len(parts) > 2 else "",
            "breakdown": " · ".join(parts[3:]),
        }
    if p0 in ("nation", "national", "us"):
        return {
            "geography": "United States",
            "level": "national",
            "source": parts[1] if len(parts) > 1 else "",
            "variable": parts[2] if len(parts) > 2 else "",
            "breakdown": " · ".join(parts[3:]),
        }
    return {
        "geography": "",
        "level": "",
        "source": parts[0],
        "variable": parts[1] if len(parts) > 1 else "",
        "breakdown": " · ".join(parts[2:]),
    }


def family_of(name: str) -> str:
    """Group key for the by-family view: source and variable."""
    p = parse_target(name)
    return " · ".join(x for x in (p["source"], p["variable"]) if x) or name


def compact_float(value: float) -> float:
    """Round large target values enough for web display without stringifying."""
    if not np.isfinite(value):
        return float(value)
    if value == 0:
        return 0.0
    return float(f"{value:.6g}")


WORKTREE = Path(os.environ.get(REPO_DIR_ENV, Path.home() / "PolicyEngine/populace"))


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

    driver_path = WORKTREE / "scripts" / "build_us_candidate.py"
    donor_path = WORKTREE / "packages/populace-build/src/populace/build/us/sources.py"
    if not driver_path.exists() or not donor_path.exists():
        return {}
    driver = driver_path.read_text()
    donor = donor_path.read_text()
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
    if REFERENCE_H5 is None or not REFERENCE_H5.exists() or not POP_TP.exists():
        return []
    pop = _profile_flat(POP_TP)
    ecps = _profile_flat(REFERENCE_H5)
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

    bounded = np.load(ART / "populace_us_2024_calibration.npz")["calibrated_weights"].astype(np.float64)
    # v2 was calibrated bounded from the start; the unbounded cautionary row
    # is the preserved v1 experiment (same pool family, same surface design).
    # The unbounded cautionary run was a v2-era experiment; later builds are
    # bounded from birth and ship no unbounded twin.
    unbounded_path = ART / "populace_us_2024_calibration_unbounded.npz"
    unbounded = (
        np.load(unbounded_path)["calibrated_weights"].astype(np.float64)
        if unbounded_path.exists()
        else np.array([])
    )

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
    targets = sorted(
        (
            {
                **parse_target(names[i]),
                "family": fams[i],
                "target": compact_float(float(b[i])),
                "estimate": compact_float(float(est[i])),
                "signed_rel_err": round(float((est[i] - b[i]) / (b[i] + 1.0)), 6),
                "abs_rel_err": round(float(abs_rel[i]), 6),
                "within10": bool(within[i]),
            }
            for i in range(len(names))
        ),
        key=lambda row: -row["abs_rel_err"],
    )

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
        "targets": targets,
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
