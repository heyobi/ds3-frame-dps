// DS3 light-attack DPS model, same formulas as tools/compute_dps.py.
// Works in the browser (window.DS3) and in node (module.exports) for testing.
(function (root) {
  "use strict";
  const MOVES = { r1h: "1H R1", r2h: "2H R1", l1: "L1 dual" };
  const STATS = ["str", "dex", "int", "fth", "lck"];

  // DS-series attack/defense curve
  function eff(ar, def) {
    if (ar <= 0) return 0;
    const r = ar / def;
    let m;
    if (r < 0.125) m = 0.1;
    else if (r < 1) m = 19.2 / 49 * (r - 0.125) ** 2 + 0.1;
    else if (r < 2.5) m = -0.4 / 3 * (r - 2.5) ** 2 + 0.7;
    else if (r < 8) m = -0.8 / 121 * (r - 8) ** 2 + 0.9;
    else m = 0.9;
    return m * ar;
  }

  // weapon level index: unique / boss weapons have 6 levels (+0..+5); "+10" means their max
  function levelIndex(w, up) {
    return w.lv.length === 6 ? Math.floor(up / 2) : up;
  }

  // AR split [phys, magic, fire, lightning, dark]
  function ar(D, w, li, st, s) {
    const L = w.lv[li], sat = w.sat, curves = D.sats;
    const S = (k, v) => curves[sat[k]][Math.max(0, Math.min(99, v))] / 100;
    const [str, dex, int, fth, lck] = st;
    const st2 = s.twoHand ? Math.min(Math.floor(str * 1.5), 99) : str;
    const sc = (i) => L[5 + i] / 100;
    return [
      L[0] * (1 + sc(0) * S(0, st2) + sc(1) * S(0, dex) + sc(4) * S(0, lck) + (w.i === "Blessed" ? sc(3) * S(0, fth) : 0)),
      L[1] * (1 + sc(2) * S(1, int)),
      L[2] * (1 + sc(2) * S(2, int) + sc(3) * S(2, fth)),
      L[3] * (1 + sc(3) * S(3, fth)),
      L[4] * (1 + sc(2) * S(4, int) + sc(3) * S(4, fth)),
    ];
  }

  function moveDps(A, frames, mv, def) {
    const secs = frames.reduce((a, b) => a + b, 0) / frames.length / 60;
    let dmg = 0;
    for (const m of mv) for (let e = 0; e < 5; e++) dmg += eff(A[e] * m / 100, def);
    return dmg / secs;
  }

  function wieldable(w, st, twoHand) {
    return st[0] * (twoHand ? 1.5 : 1) >= w.req[0] && st[1] >= w.req[1] && st[2] >= w.req[2] && st[3] >= w.req[3];
  }

  // Which stats can change this weapon's AR at this level
  function relevant(w, li) {
    const L = w.lv[li], d = L.slice(0, 5), s = L.slice(5);
    const out = [];
    if (s[0] > 0 && d[0] > 0) out.push(0);
    if (s[1] > 0 && d[0] > 0) out.push(1);
    if (s[2] > 0 && (d[1] > 0 || d[2] > 0 || d[4] > 0)) out.push(2);
    if (s[3] > 0 && (d[2] > 0 || d[3] > 0 || d[4] > 0 || (w.i === "Blessed" && d[0] > 0))) out.push(3);
    if (s[4] > 0 && d[0] > 0) out.push(4);
    return out;
  }

  // Fixed stats: DPS of one move
  function evalMove(D, w, key, st, up, def) {
    const mvset = D.moves[w.n][key];
    const twoHand = key !== "r1h";
    if (!mvset || !wieldable(w, st, twoHand)) return null;
    const li = levelIndex(w, up);
    const A = ar(D, w, li, st, { twoHand });
    return { move: key, dps: moveDps(A, mvset[0], mvset[1], def), ar: A, stats: st.slice(), frames: mvset[0] };
  }

  // Free points: meet requirements first, then search the spread of the rest over the stats that matter
  function optimizeMove(D, w, key, base, budget, up, def) {
    const mvset = D.moves[w.n][key];
    if (!mvset) return null;
    const twoHand = key !== "r1h";
    const li = levelIndex(w, up);
    const st = base.slice();
    const need = [twoHand ? Math.ceil(w.req[0] / 1.5) : w.req[0], w.req[1], w.req[2], w.req[3], 0];
    let cost = 0;
    for (let i = 0; i < 5; i++) if (st[i] < need[i]) { cost += need[i] - st[i]; st[i] = need[i]; }
    if (cost > budget) return null;
    const R = budget - cost;
    const rel = relevant(w, li);
    const k = rel.length;
    const step = k <= 2 ? 1 : k === 3 ? 2 : 3;
    const units = Math.floor(R / step), rem = R - units * step;
    let best = null;
    const cur = st.slice();
    const tryOne = () => {
      const variants = rem > 0 && k > 0 ? rel : [-1];
      for (const v of variants) {
        const t = cur.slice();
        if (v >= 0) t[v] += rem;
        for (let i = 0; i < 5; i++) if (t[i] > 99) t[i] = 99;
        const A = ar(D, w, li, t, { twoHand });
        const dps = moveDps(A, mvset[0], mvset[1], def);
        if (!best || dps > best.dps + 1e-9) best = { move: key, dps, ar: A, stats: t, frames: mvset[0] };
      }
    };
    const rec = (j, left) => {
      if (j === k - 1) { const i = rel[j]; const keep = cur[i]; cur[i] += left * step; tryOne(); cur[i] = keep; return; }
      const i = rel[j], keep = cur[i];
      for (let u = 0; u <= left; u++) { cur[i] = keep + u * step; if (cur[i] > 99 + step) break; rec(j + 1, left - u); }
      cur[i] = keep;
    };
    if (k === 0) tryOne(); else rec(0, units);
    return best;
  }

  // Rank every weapon/infusion. opts: {mode:"opt"|"fixed", stats, base, budget, up, def, moves:{r1h,r2h,l1}}
  function rank(D, opts) {
    const rows = [];
    for (const w of D.weapons) {
      let best = null;
      const per = {};
      for (const key of Object.keys(MOVES)) {
        if (!opts.moves[key]) continue;
        const r = opts.mode === "opt"
          ? optimizeMove(D, w, key, opts.base, opts.budget, opts.up, opts.def)
          : evalMove(D, w, key, opts.stats, opts.up, opts.def);
        if (!r) continue;
        per[key] = r.dps;
        if (!best || r.dps > best.dps) best = r;
      }
      if (best) rows.push(Object.assign({ w, per }, best));
    }
    rows.sort((a, b) => b.dps - a.dps);
    return rows;
  }

  const api = { eff, ar, rank, optimizeMove, evalMove, levelIndex, MOVES, STATS };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.DS3 = api;
})(this);
