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
})();
