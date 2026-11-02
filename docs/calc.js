// DS3 light-attack DPS model (same formulas as tools/compute_dps.py) plus boss targets, bleed/frost and stamina.
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

  // Target: { def:[5 per element], mul:[std,slash,strike,thrust,magic,fire,lightning,dark] or null, hp, bleed,
  //          frost (status thresholds, null = immune), bloodRate (% of bleed damage taken), stamina (bool) }
  function flatTarget(def, stamina) {
    return { def: [def, def, def, def, def], mul: null, hp: 0, bleed: null, frost: null, bloodRate: 100, stamina: !!stamina };
  }
  function bossTarget(b, stamina) {
    return { def: b.df, mul: b.mul, hp: b.hp, bleed: b.bleed, frost: b.frost, bloodRate: b.bloodRate, stamina: !!stamina };
  }
  const REGEN = 45;          // stamina per second (equip load under 70%)
  const FROST_AMP = 0.07, FROST_TIME = 14;   // frostbite: target takes 7% more damage for 14 s

  // One full 3-step chain against target T. Returns dps and its parts.
  function chainEval(D, w, key, li, st, T) {
    const steps = D.moves[w.n][key];
    const A = ar(D, w, li, st, { twoHand: key !== "r1h" });
    let direct = 0, frames = 0, hits = 0, stam = 0;
    for (const [f, sc, hs] of steps) {
      frames += f; stam += sc;
      for (const h of hs) {
        hits++;
        for (let e = 0; e < 5; e++) {
          if (!h[e] || !A[e]) continue;
          const m = T.mul ? T.mul[e === 0 ? h[5] : e + 3] : 1;
          direct += eff(A[e] * h[e] / 100, T.def[e]) * m;
        }
      }
    }
    let t = frames / 60;
    const stamUse = stam * (w.scr || 1);
    if (T.stamina) t += stamUse / REGEN;     // no regen while attacking, so every point spent costs 1/45 s
    let bleed = 0, frost = 0;
    if (T.hp) {
      const L = w.lv[li];
      if (L[10] > 0 && T.bleed && w.pb) {
        const luck = 1 + (w.lc || 0) / 100 * L[12] * (D.sats[w.sb] ? D.sats[w.sb][Math.min(99, st[4])] / 100 : 0);
        const procs = hits * L[10] * luck / T.bleed;
        bleed = procs * (w.pb[0] / 100 * T.hp + w.pb[1]) * T.bloodRate / 100;
      }
      if (L[11] > 0 && T.frost && w.pf) {
        const procs = hits * L[11] / T.frost;
        // the NPC bleed-damage rate (bosses: usually 50%) is applied to frostbite too; not confirmed in game
        frost = procs * (w.pf[0] / 100 * T.hp + w.pf[1]) * T.bloodRate / 100;
        const uptime = Math.min(1, FROST_TIME * procs / t);
        direct *= 1 + FROST_AMP * uptime;
      }
    }
    return { dps: (direct + bleed + frost) / t, ar: A, frames: steps.map(x => x[0]),
             parts: { direct: direct / t, bleed: bleed / t, frost: frost / t }, stamina: stamUse / steps.length, secs: t / steps.length };
  }

  function wieldable(w, st, twoHand) {
    return st[0] * (twoHand ? 1.5 : 1) >= w.req[0] && st[1] >= w.req[1] && st[2] >= w.req[2] && st[3] >= w.req[3];
  }

  // Which stats can change this weapon's damage at this level
  function relevant(w, li, T) {
    const L = w.lv[li], d = L.slice(0, 5), s = L.slice(5);
    const out = [];
    if (s[0] > 0 && d[0] > 0) out.push(0);
    if (s[1] > 0 && d[0] > 0) out.push(1);
    if (s[2] > 0 && (d[1] > 0 || d[2] > 0 || d[4] > 0)) out.push(2);
    if (s[3] > 0 && (d[2] > 0 || d[3] > 0 || d[4] > 0 || (w.i === "Blessed" && d[0] > 0))) out.push(3);
    if ((s[4] > 0 && d[0] > 0) || (T && T.bleed && L[10] > 0 && w.lc > 0)) out.push(4);
    return out;
  }

  // Fixed stats: DPS of one move
  function evalMove(D, w, key, st, up, T) {
    const mvset = D.moves[w.n][key];
    if (!mvset || !wieldable(w, st, key !== "r1h")) return null;
    return Object.assign({ move: key, stats: st.slice() }, chainEval(D, w, key, levelIndex(w, up), st, T));
  }

  // Free points: meet requirements first, then search the spread of the rest over the stats that matter
  function optimizeMove(D, w, key, base, budget, up, T) {
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
    const rel = relevant(w, li, T);
    const k = rel.length;
    const step = k <= 2 ? 1 : k === 3 ? 2 : k === 4 ? 3 : 5;
    const units = Math.floor(R / step), rem = R - units * step;
    let best = null;
    const cur = st.slice();
    const tryOne = () => {
      const variants = rem > 0 && k > 0 ? rel : [-1];
      for (const v of variants) {
        const t = cur.slice();
        if (v >= 0) t[v] += rem;
        for (let i = 0; i < 5; i++) if (t[i] > 99) t[i] = 99;
        const r = chainEval(D, w, key, li, t, T);
        if (!best || r.dps > best.dps + 1e-9) best = Object.assign({ move: key, stats: t }, r);
      }
    };
    const rec = (j, left) => {
      if (j === k - 1) { const i = rel[j]; const keep = cur[i]; cur[i] += left * step; tryOne(); cur[i] = keep; return; }
      const i = rel[j], keep = cur[i];
      for (let u = 0; u <= left; u++) { cur[i] = keep + u * step; if (cur[i] > 99 + step) break; rec(j + 1, left - u); }
      cur[i] = keep;
    };
    if (k === 0) tryOne(); else rec(0, units);
    // points no stat can use any more (e.g. SL802) go to the stats that don't change DPS, so the shown spread
    // adds up to the soul level; DPS is unchanged
    if (best) {
      let left = budget - best.stats.reduce((a, v, i) => a + v - base[i], 0);
      for (const i of [4, 3, 2, 1, 0]) { const a = Math.max(0, Math.min(left, 99 - best.stats[i])); best.stats[i] += a; left -= a; }
    }
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

  // Leveling path: meet the requirements, then add points one at a time to whichever stat gives the most DPS
  // per point (judged over the next 1 to 25 points, so slow-starting curves are not skipped). Every point in the
  // path extends the previous one, so the spread never jumps around between soul levels.
  function levelPath(D, w, key, base, maxBudget, up, T, step) {
    step = step || 1;
    const mvset = D.moves[w.n][key];
    if (!mvset) return null;
    const twoHand = key !== "r1h";
    const li = levelIndex(w, up);
    const st = base.slice();
    const need = [twoHand ? Math.ceil(w.req[0] / 1.5) : w.req[0], w.req[1], w.req[2], w.req[3], 0];
    let pts = 0;
    const chunks = [];
    for (let i = 0; i < 5; i++) if (st[i] < need[i]) { pts += need[i] - st[i]; chunks.push({ stat: i, from: st[i], to: need[i], req: true }); st[i] = need[i]; }
    if (pts > maxBudget) return { cost: pts, points: [], chunks };
    const dpsOf = (t) => chainEval(D, w, key, li, t, T).dps;
    const rel = relevant(w, li, T);
    let cur = dpsOf(st);
    const points = [{ pts, stats: st.slice(), dps: cur }];
    while (pts + step <= maxBudget) {
      let bestGain = 1e-9, pick = -1;
      for (const i of rel) {
        for (const c of [step, 5, 10, 15, 20, 25]) {
          const t = st.slice(); t[i] = Math.min(99, t[i] + c);
          if (t[i] === st[i]) continue;
          const g = (dpsOf(t) - cur) / c;
          if (g > bestGain) { bestGain = g; pick = i; }
        }
      }
      if (pick < 0) break;                          // nothing raises DPS any more
      const from = st[pick];
      st[pick] = Math.min(99, st[pick] + step);
      pts += step;
      cur = dpsOf(st);
      const last = chunks[chunks.length - 1];
      if (last && !last.req && last.stat === pick) last.to = st[pick];
      else chunks.push({ stat: pick, from, to: st[pick] });
      points.push({ pts, stats: st.slice(), dps: cur });
    }
    return { cost: points[0].pts, points, chunks };
  }

  const api = { eff, ar, rank, flatTarget, bossTarget, chainEval, optimizeMove, evalMove, levelPath, levelIndex, MOVES, STATS };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.DS3 = api;
})(this);
