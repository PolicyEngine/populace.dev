/* Provenance diagram for the homepage — where every layer of populace comes
   from. Data-driven from data/calibration.json (variable counts per donor
   source); no hand-typed numbers. Lifted from the retired observatory so the
   one piece of it not covered by the calibration dashboard survives. */
(async function () {
  const mount = document.getElementById("sources-diagram");
  if (!mount) return;
  let d;
  try {
    d = await (await fetch("./data/calibration.json", { cache: "no-store" })).json();
  } catch {
    return; // best-effort; the rest of the page is static
  }
  const compact = (x) => {
    const a = Math.abs(x);
    if (a >= 1e12) return (x / 1e12).toFixed(2) + "T";
    if (a >= 1e9) return (x / 1e9).toFixed(2) + "B";
    if (a >= 1e6) return (x / 1e6).toFixed(2) + "M";
    if (a >= 1e3) return (x / 1e3).toFixed(1) + "k";
    return String(Math.round(x));
  };

  const counts = {};
  for (const r of d.lineage || []) counts[r.source] = (counts[r.source] || 0) + 1;

  const SOURCES = [
    { name: "Census CPS ASEC 2023", note: "household structure · demographics · incomes · benefits · tenure · hours · occupation · retirement contributions · childcare", keys: ["cps-carried", "cps-derived"] },
    { name: "IRS SOI Public Use File 2015 (uprated)", note: "tax detail: capital gains · dividends · interest · deduction inputs · pass-through · estates", keys: ["puf-imputed"] },
    { name: "Census block crosswalk", note: "geography: state · county · tract · block · congressional district", keys: [] },
    { name: "Fed SCF 2022", note: "wealth: accounts · stocks · bonds · debts · net worth · mortgage balance hints", keys: ["scf-imputed"] },
    { name: "Census SIPP", note: "tip income for tipped occupations · household vehicles (count + value)", keys: ["sipp-imputed"] },
    { name: "CPS-ORG", note: "hourly wage · paid-hourly status · union coverage", keys: ["org-imputed"] },
    { name: "MEPS-IC parameters", note: "employer-sponsored insurance premiums", keys: ["meps-imputed"] },
    { name: "Census ACS 2022", note: "rent for renter households", keys: ["acs-imputed"] },
    { name: "Spec + microunit structure", note: "tax units · SPM units · families · marital units · clone strata", keys: ["spec/structural"] },
  ];
  const TARGETS_NAME = "IRS SOI · Census · program administrative totals";

  const W = 980, ROW = 86, H = SOURCES.length * ROW + 40;
  const sx = 10, sw = 380, mx = 520, mw = 200, tx = 790, tw = 180;
  const midY = H / 2 - 20;
  const p = [];
  p.push(`<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;font-family:var(--mono);">`);
  SOURCES.forEach((srcDef, i) => {
    const y = 16 + i * ROW;
    const n = srcDef.keys.reduce((a, k) => a + (counts[k] || 0), 0);
    p.push(`<rect x="${sx}" y="${y}" width="${sw}" height="${ROW - 18}" rx="6" fill="var(--ink-2)" stroke="var(--line)"/>`);
    p.push(`<text x="${sx + 14}" y="${y + 22}" fill="var(--paper)" font-size="13">${srcDef.name}${n ? ` · ${n} vars` : ""}</text>`);
    const words = srcDef.note.split(" ");
    let line = "";
    const lines = [];
    for (const w2 of words) { if ((line + w2).length > 58) { lines.push(line); line = ""; } line += w2 + " "; }
    lines.push(line);
    lines.slice(0, 3).forEach((ln, k) =>
      p.push(`<text x="${sx + 14}" y="${y + 38 + k * 13}" fill="var(--paper-faint)" font-size="10.5">${ln.trim()}</text>`));
    p.push(`<path d="M ${sx + sw} ${y + (ROW - 18) / 2} C ${sx + sw + 60} ${y + (ROW - 18) / 2}, ${mx - 60} ${midY}, ${mx} ${midY}" fill="none" stroke="var(--paper-faint)" stroke-opacity="0.55"/>`);
  });
  p.push(`<rect x="${mx}" y="${midY - 34}" width="${mw}" height="68" rx="6" fill="var(--ink-2)" stroke="var(--amber-soft)"/>`);
  p.push(`<text x="${mx + mw / 2}" y="${midY - 8}" text-anchor="middle" fill="var(--paper)" font-size="13">populace-us 2024</text>`);
  p.push(`<text x="${mx + mw / 2}" y="${midY + 10}" text-anchor="middle" fill="var(--paper-faint)" font-size="10.5">${(d.headline.n_households || 0).toLocaleString()} households</text>`);
  p.push(`<text x="${mx + mw / 2}" y="${midY + 24}" text-anchor="middle" fill="var(--paper-faint)" font-size="10.5">${compact(d.headline.weighted_persons)} people represented</text>`);
  p.push(`<path d="M ${mx + mw} ${midY} L ${tx} ${midY}" stroke="var(--paper-faint)" stroke-opacity="0.55"/>`);
  p.push(`<rect x="${tx}" y="${midY - 34}" width="${tw}" height="68" rx="6" fill="var(--ink-2)" stroke="var(--line)"/>`);
  p.push(`<text x="${tx + tw / 2}" y="${midY - 8}" text-anchor="middle" fill="var(--paper)" font-size="12">calibration</text>`);
  TARGETS_NAME.split(" · ").forEach((tword, k) =>
    p.push(`<text x="${tx + tw / 2}" y="${midY + 8 + k * 12}" text-anchor="middle" fill="var(--paper-faint)" font-size="9.5">${tword}</text>`));
  p.push("</svg>");
  mount.innerHTML = p.join("");

  const note = document.getElementById("sources-note");
  if (note)
    note.textContent =
      `Variable counts are live from this release's lineage table (${(d.headline.n_targets || 3704).toLocaleString()} calibration targets). ` +
      "Every donor is a primary survey; the enhanced CPS appears only as the benchmark the finished dataset is scored against, never as a build input. " +
      "Calibration adjusts weights only — no target value is ever written into a record.";
})();
