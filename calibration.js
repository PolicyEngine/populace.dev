(async function () {
  const params = new URLSearchParams(location.search);
  const requestedRelease = params.get("release");
  const dataUrl = requestedRelease
    ? `./data/releases/${encodeURIComponent(requestedRelease)}.json`
    : "./data/calibration.json";

  const response = await fetch(dataUrl, { cache: "no-store" });
  const data = await response.json();
  let releases = [];
  try {
    releases = await (await fetch("./data/releases/index.json", { cache: "no-store" })).json();
  } catch {
    releases = [];
  }

  const $ = (id) => document.getElementById(id);
  const el = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const pct = (value, digits = 1) => `${(100 * value).toFixed(digits)}%`;
  const compact = (value) => {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
    const x = Number(value);
    const abs = Math.abs(x);
    if (abs >= 1e12) return `${(x / 1e12).toFixed(2)}T`;
    if (abs >= 1e9) return `${(x / 1e9).toFixed(2)}B`;
    if (abs >= 1e6) return `${(x / 1e6).toFixed(2)}M`;
    if (abs >= 1e3) return `${(x / 1e3).toFixed(1)}k`;
    if (abs > 0 && abs < 1) return x.toPrecision(2);
    return Math.round(x).toLocaleString();
  };

  $("cal-stamp").textContent =
    `release ${data.release || "latest"} · regenerated ${data.generated_at || "unknown"}`;

  const releaseBox = $("cal-releases");
  for (const release of releases) {
    const link = el("a", null, release);
    link.href = `?release=${encodeURIComponent(release)}`;
    if (release === data.release) link.setAttribute("aria-current", "page");
    releaseBox.append(link);
  }

  const headline = data.headline || {};
  const metric = (label, value, note) => {
    const node = el("div", "metric");
    node.append(el("span", "metric-label mono", label));
    node.append(el("span", "metric-val", value));
    node.append(el("span", "metric-note", note));
    return node;
  };
  $("cal-headline").append(
    metric(
      "targets within 10%",
      headline.within10_final == null ? "—" : pct(headline.within10_final),
      `${(headline.n_targets || 0).toLocaleString()} target rows`
    ),
    metric(
      "calibration loss",
      headline.loss_final == null
        ? "—"
        : `${headline.loss_initial.toFixed(2)} → ${headline.loss_final.toFixed(3)}`,
      "relative-error loss, before to after"
    ),
    metric(
      "represented people",
      compact(headline.weighted_persons),
      `${(headline.n_households || 0).toLocaleString()} weighted households`
    )
  );

  function renderBars(container, rows, options = {}) {
    const max = Math.max(...rows.map((row) => row.value), 1);
    container.replaceChildren();
    for (const row of rows) {
      const item = el("div", "cal-bar-row");
      item.append(el("span", "cal-bar-label", row.label));
      const track = el("span", "cal-bar-track");
      const fill = el("i", row.dim ? "dim" : null);
      fill.style.width = `${Math.max(1, (100 * row.value) / max)}%`;
      track.append(fill);
      item.append(track);
      item.append(el("span", "cal-bar-value mono", row.display));
      if (options.title) item.title = row.title || "";
      container.append(item);
    }
  }

  const histogram = data.histogram || { labels: [], counts: [] };
  renderBars(
    $("cal-hist"),
    histogram.labels.map((label, index) => ({
      label: `|miss| ${label}`,
      value: histogram.counts[index] || 0,
      display: `${(histogram.counts[index] || 0).toLocaleString()} rows`,
      dim: index >= 4,
    }))
  );

  const familyRows = (data.families || []).slice(0, 18).map((row) => ({
    label: row.family,
    value: row.within10 || 0,
    display: `${pct(row.within10 || 0, 0)} of ${row.n}`,
    dim: (row.within10 || 0) < 0.8,
    title: `${row.n} targets · median miss ${pct(row.median_abs_rel_err || 0)}`,
  }));
  renderBars($("cal-families"), familyRows, { title: true });

  const sourceTargets =
    Array.isArray(data.targets) && data.targets.length
      ? data.targets
      : (data.worst || []).map((row) => ({
          ...row,
          family: row.name ? row.name.split("/").slice(0, 3).join(" · ") : "unknown",
          signed_rel_err: null,
          within10: false,
        }));
  const targetRows = sourceTargets.map((row) => ({
    name: row.name || "",
    family: row.family || "unknown",
    target: Number(row.target),
    estimate: Number(row.estimate),
    absRelErr: Number(row.abs_rel_err || 0),
    signedRelErr:
      row.signed_rel_err === null || row.signed_rel_err === undefined
        ? null
        : Number(row.signed_rel_err),
    within10: Boolean(row.within10),
  }));

  const familySelect = $("cal-family");
  for (const family of [...new Set(targetRows.map((row) => row.family))].sort()) {
    const option = el("option", null, family);
    option.value = family;
    familySelect.append(option);
  }

  function sortRows(rows) {
    const sort = $("cal-sort").value;
    return rows.sort((a, b) => {
      if (sort === "name") return a.name.localeCompare(b.name);
      if (sort === "family") return a.family.localeCompare(b.family) || b.absRelErr - a.absRelErr;
      return b.absRelErr - a.absRelErr;
    });
  }

  function renderTargetTable() {
    const query = $("cal-search").value.trim().toLowerCase();
    const family = $("cal-family").value;
    const status = $("cal-status").value;
    let rows = targetRows.filter((row) => {
      if (family && row.family !== family) return false;
      if (status === "hit" && !row.within10) return false;
      if (status === "miss" && row.within10) return false;
      if (query && !`${row.name} ${row.family}`.toLowerCase().includes(query)) return false;
      return true;
    });
    rows = sortRows(rows);

    const table = $("cal-targets");
    table.replaceChildren();
    const head = el("tr");
    for (const col of ["target", "family", "aimed", "fit", "miss", "status"]) {
      head.append(el("th", null, col));
    }
    table.append(head);

    for (const row of rows.slice(0, 200)) {
      const tr = el("tr");
      const targetCell = el("td", "cal-target-name", row.name);
      targetCell.title = row.name;
      tr.append(targetCell);
      tr.append(el("td", null, row.family));
      tr.append(el("td", "num", compact(row.target)));
      tr.append(el("td", "num", compact(row.estimate)));
      tr.append(el("td", "num", pct(row.absRelErr, row.absRelErr >= 1 ? 0 : 1)));
      tr.append(el("td", row.within10 ? "ok" : "hot", row.within10 ? "within" : "miss"));
      table.append(tr);
    }

    const misses = rows.filter((row) => !row.within10).length;
    $("cal-table-note").textContent =
      `${rows.length.toLocaleString()} rows match` +
      (rows.length > 200 ? " · first 200 shown" : "") +
      ` · ${misses.toLocaleString()} outside ten percent`;
  }

  for (const id of ["cal-search", "cal-family", "cal-status", "cal-sort"]) {
    $(id).addEventListener("input", renderTargetTable);
    $(id).addEventListener("change", renderTargetTable);
  }
  renderTargetTable();
})();
