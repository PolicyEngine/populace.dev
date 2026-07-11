// Live coverage contract. Reads the populace-us input-coverage manifest for the
// latest release and renders the required / reviewed-exclusion counts, the gate,
// and the full exclusion list with reasons. Like releases.js, this renders real
// registry data or nothing: the live region stays hidden unless the manifest
// loads, so the page cannot go stale.
//
// Fetch strategy, in order:
//   1) the manifest published in the release directory, if a build ships it there
//      (future builds may publish release_input_coverage_manifest.json next to the
//      other manifests) — keeps the page on-registry when that lands;
//   2) fall back to raw.githubusercontent.com at the build sha embedded in the
//      release id (e.g. ...-75d5add-<timestamp>), where the manifest lives today at
//      packages/populace-build/src/populace/build/us/release_input_coverage_manifest.json.
// Build J renders from (2) today; when a build publishes the manifest in-release,
// (1) takes over and the counts get richer automatically — no code change.
(async () => {
  const HF =
    "https://huggingface.co/datasets/policyengine/populace-us/resolve/main/";
  const RAW = "https://raw.githubusercontent.com/PolicyEngine/populace/";
  const GH_BLOB = "https://github.com/PolicyEngine/populace/blob/";
  const COV_PATH =
    "packages/populace-build/src/populace/build/us/release_input_coverage_manifest.json";
  const COV_FILE = "release_input_coverage_manifest.json";

  const live = document.getElementById("contract-live");
  if (!live) return;
  const slot = (name) => live.querySelector(`[data-slot="${name}"]`);

  const getJSON = async (url) => {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error(String(res.status));
    return res.json();
  };

  // The build sha is the last 7–40 char hex segment of the release id, sitting
  // just before the trailing ...T......Z timestamp segment.
  const shaFromReleaseId = (rid) => {
    const segs = String(rid || "").split("-");
    for (let i = segs.length - 1; i >= 0; i--) {
      if (/^[0-9a-f]{7,40}$/.test(segs[i])) return segs[i];
    }
    return null;
  };

  const issueUrl = (ref) => {
    // "PolicyEngine/populace#38" -> repo issue URL + "#38" label
    const m = String(ref || "").match(/^([\w.-]+\/[\w.-]+)#(\d+)$/);
    if (!m) return null;
    return { href: `https://github.com/${m[1]}/issues/${m[2]}`, label: `#${m[2]}` };
  };

  let manifest = null;
  let releaseId = "";
  let sourceHref = "";
  try {
    const latest = await getJSON(HF + "latest.json");
    releaseId = latest.release_id || "";
    const relDir = String(
      (latest.paths && latest.paths.build_manifest) || ""
    ).replace(/build_manifest\.json$/, "");

    // (1) prefer an in-release manifest if a build ships one
    if (relDir) {
      try {
        const url = HF + relDir + COV_FILE;
        manifest = await getJSON(url);
        sourceHref = url;
      } catch (_) {
        manifest = null;
      }
    }
    // (2) fall back to the source tree at the release's build sha
    if (!manifest) {
      const sha = shaFromReleaseId(releaseId);
      if (!sha) return;
      manifest = await getJSON(RAW + sha + "/" + COV_PATH);
      sourceHref = GH_BLOB + sha + "/" + COV_PATH;
    }
  } catch (_) {
    return; // best-effort, like releases.js
  }
  if (!manifest || !manifest.columns) return;

  const cols = manifest.columns;
  const names = Object.keys(cols);

  // counts: trust the manifest's own block, else derive from the columns
  const c = manifest.counts || {};
  const total = c.total != null ? c.total : names.length;
  const required =
    c.required != null
      ? c.required
      : names.filter((n) => cols[n].status === "required").length;
  const excluded =
    c.reviewed_exclusion != null
      ? c.reviewed_exclusion
      : names.filter((n) => cols[n].status === "reviewed_exclusion").length;

  const setText = (name, v) => {
    const el = slot(name);
    if (el) el.textContent = v;
  };
  setText("total", total.toLocaleString("en-US"));
  setText("required", required.toLocaleString("en-US"));
  setText("excluded", excluded.toLocaleString("en-US"));

  // gate line — name the gate (pulled live from the manifest description) and the
  // count it checks. The mechanism, stated once more next to the live number.
  let gateName = "release_input_coverage";
  const gm = String(manifest.description || "").match(
    /release gate \(([^)]+)\)/
  );
  if (gm) gateName = gm[1].split(".").pop();
  const gateEl = slot("gate");
  if (gateEl) {
    gateEl.textContent =
      `gate ${gateName} · checks all ${total.toLocaleString("en-US")} ` +
      `declared input columns at build time · a required column missing or ` +
      `all-default fails the release`;
  }

  // exclusion list — every reviewed exclusion, its reason, and its tracked issue
  const excl = names
    .filter((n) => cols[n].status === "reviewed_exclusion")
    .sort();
  const table = slot("table");
  if (table && excl.length) {
    const rows = excl.map((n) => {
      const e = cols[n];
      const iss = issueUrl(e.issue);
      const link = iss
        ? `<a class="contract-excl-issue mono" href="${iss.href}" target="_blank" rel="noopener">${iss.label}</a>`
        : "";
      const reason = (e.reason || e.note || "").replace(
        /[<>&]/g,
        (ch) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" }[ch])
      );
      return (
        `<div class="contract-excl-row">` +
        `<div class="contract-excl-head"><span class="contract-excl-col mono">${n}</span>${link}</div>` +
        `<p class="contract-excl-reason">${reason}</p>` +
        `</div>`
      );
    });
    table.innerHTML = rows.join("");
  }
  const summary = slot("summary");
  if (summary)
    summary.textContent = `Show all ${excluded.toLocaleString(
      "en-US"
    )} reviewed exclusions and their reasons`;

  // provenance
  const source = slot("source");
  if (source) {
    const label = releaseId ? ` · ${releaseId}` : "";
    source.innerHTML =
      `Coverage contract read live from ` +
      `<a href="${sourceHref}" target="_blank" rel="noopener">${COV_FILE}</a>${label}`;
  }

  live.hidden = false;
})();
