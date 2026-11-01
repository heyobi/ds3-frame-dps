// Ranks every weapon off the main thread so the page stays responsive.
importScripts("calc.js?v=1");
let D = null;
onmessage = (ev) => {
  const m = ev.data;
  if (m.data) { D = m.data; return; }
  const { id, opts } = m;
  const T = opts.boss != null ? D.bosses[opts.boss] : ER.flatTarget(opts.def);
  const rows = [];
  const list = D.weapons;
  for (let k = 0; k < list.length; k++) {
    const w = list[k];
    if (opts.classes && !opts.classes.includes(w.c)) continue;
    if (opts.infs && !opts.infs.includes(w.i)) continue;
    let best = null; const per = {};
    for (const key of opts.moves) {
      const r = opts.mode === "opt" ? ER.optimize(D, w, key, opts.base, opts.budget, T, 3) : ER.evalFixed(D, w, key, opts.stats, T);
      if (!r) continue;
      per[key] = r.dps;
      if (!best || r.dps > best.dps) best = r;
    }
    if (best) rows.push({ k, per, dps: best.dps, move: best.move, stats: best.stats, ar: best.ar, direct: best.direct,
                          bleed: best.bleed, frost: best.frost, ttk: best.ttk, procsB: best.procsB, procsF: best.procsF });
    if (k % 100 === 0) postMessage({ id, progress: k / list.length });
  }
  rows.sort((a, b) => b.dps - a.dps);
  postMessage({ id, rows });
};
