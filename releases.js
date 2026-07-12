// Live release strip. Reads the populace-us release registry (Hugging Face)
// and the policyengine.py bundle manifest. Each row stays hidden unless its
// source loads — the strip renders real registry data or nothing.
(async () => {
  const HF =
    "https://huggingface.co/datasets/policyengine/populace-us/resolve/main/";
  const PY_MANIFEST =
    "https://raw.githubusercontent.com/PolicyEngine/policyengine.py/main/src/policyengine/data/bundle/manifest.json";

  const day = (iso) => (typeof iso === "string" ? iso.slice(0, 10) : "");
  const getJSON = async (url) => {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error(String(res.status));
    return res.json();
  };
  const show = (rowId, id, meta) => {
    const row = document.getElementById(rowId);
    if (!row || !id) return;
    row.querySelector('[data-slot="id"]').textContent = id;
    row.querySelector('[data-slot="meta"]').textContent = meta;
    row.hidden = false;
  };

  try {
    const latest = await getJSON(HF + "latest.json");
    let meta = day(latest.updated_at);
    try {
      const bm = await getJSON(HF + latest.paths.build_manifest);
      const def = (bm.dataset && bm.dataset.default) || {};
      const cal = (bm.gates && bm.gates.calibration) || {};
      const bits = [day(bm.created_at) || day(latest.updated_at)];
      if (def.n_exported_households)
        bits.push(def.n_exported_households.toLocaleString("en-US") + " households");
      const loss = def.final_loss ?? cal.final_loss;
      if (typeof loss === "number") bits.push("calibration loss " + loss.toFixed(3));
      if (typeof cal.fraction_within_10pct === "number")
        bits.push(Math.round(cal.fraction_within_10pct * 100) + "% of targets within 10%");
      meta = bits.join(" · ");
    } catch (_) {}
    show("release-row-latest", latest.release_id, meta);
  } catch (_) {}

  try {
    const manifest = await getJSON(PY_MANIFEST);
    const us = manifest.data_releases && manifest.data_releases.us;
    if (us && us.build_id) {
      const cert = us.certification || {};
      const bits = ["policyengine.py " + (manifest.bundle_version || "")];
      if (cert.certified_for_model_version)
        bits.push("policyengine-us " + cert.certified_for_model_version);
      show("release-row-certified", us.build_id, bits.join(" · "));
    }
  } catch (_) {}

  // Local-area (non-default) row. Same cannot-go-stale contract as the rows
  // above: list tags from the public HF refs API, keep the -acs-local- builds,
  // pick the newest by trailing timestamp, then read that release's published
  // manifests. If no local build is published, the row and its note stay hidden.
  try {
    const refs = await getJSON(
      "https://huggingface.co/api/datasets/policyengine/populace-us/refs"
    );
    const localTags = (refs.tags || [])
      .map((t) => t && t.name)
      .filter((n) => typeof n === "string" && n.includes("-acs-local-"));
    if (!localTags.length) throw new Error("no local build");

    // newest by the trailing ...-YYYYMMDDThhmmssZ segment: lexicographic compare
    // of the last dash-delimited part orders these timestamps chronologically.
    const trailing = (n) => n.split("-").pop();
    const id = localTags.reduce((a, b) => (trailing(b) > trailing(a) ? b : a));

    const relDir = "releases/" + id + "/";
    const rm = await getJSON(HF + relDir + "release_manifest.json");
    const gs = await getJSON(HF + relDir + "gate_summary.json");
    const cal = (gs.gates && gs.gates.calibration) || {};

    const bits = [];
    const date = day((rm.build && rm.build.built_at) || "");
    if (date) bits.push(date);
    // household count is the export record count; the two manifests above don't
    // carry it directly, so read it from the release's calibration diagnostics.
    try {
      const cd = await getJSON(HF + relDir + "calibration_diagnostics.json");
      const n =
        (cd.target_surface && cd.target_surface.n_records) ?? cd.n_records;
      if (typeof n === "number")
        bits.push(n.toLocaleString("en-US") + " households");
    } catch (_) {}
    if (typeof cal.n_targets === "number")
      bits.push(cal.n_targets.toLocaleString("en-US") + " targets");
    if (typeof cal.fraction_within_10pct === "number")
      bits.push(
        Math.round(cal.fraction_within_10pct * 100) + "% of targets within 10%"
      );

    show("release-row-local", id, bits.join(" · "));
    const note = document.getElementById("release-local-note");
    if (note) note.hidden = false;
  } catch (_) {}
})();
