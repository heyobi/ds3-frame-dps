// Elden Ring light-attack DPS model (same formulas as er/er_model.py). Browser: window.ER, node: module.exports.
(function (root) {
  "use strict";
  const MOVES = { "1h": "1H R1", "2h": "2H R1", ps: "Powerstance L1" };
  const STATS = ["Str", "Dex", "Int", "Fai", "Arc"];

  function eff(a, d) {
    if (a <= 0) return 0;
    const r = a / d;
    let m;
    if (r < 0.125) m = 0.1;
    else if (r < 1) m = 19.2 / 49 * (r - 0.125) ** 2 + 0.1;
    else if (r < 2.5) m = -0.4 / 3 * (r - 2.5) ** 2 + 0.7;
    else if (r < 8) m = -0.8 / 121 * (r - 8) ** 2 + 0.9;
    else m = 0.9;
    return m * a;
  }

  const G = (D, g, x) => D.graphs[g][Math.max(0, Math.min(99, x))] / 100;

  // AR per element [phys, magic, fire, lightning, holy]
  function ar(D, w, st, twoHand) {
    const s = st.slice();
    if (twoHand && !w.pair) s[0] = Math.min(99, Math.floor(s[0] * 1.5));
    return w.el.map((e) => {
      if (!e) return 0;
      const [base, coef, g, mask] = e;
      for (let i = 0; i < 5; i++) if (mask[i] && s[i] < w.req[i]) return base * 0.6;   // unmet requirement
      let add = 0;
      for (let i = 0; i < 5; i++) if (coef[i]) add += coef[i] * G(D, g, s[i]);
      return base * (1 + add);
    });
  }

  function meets(w, st, twoHand) {
    const s0 = twoHand && !w.pair ? Math.floor(st[0] * 1.5) : st[0];
    return s0 >= w.req[0] && st[1] >= w.req[1] && st[2] >= w.req[2] && st[3] >= w.req[3] && st[4] >= w.req[4];
  }

  function flatTarget(def) { return { df: [def, def, def, def, def], mul: null, hp: 0 }; }

  // T: flat target or a boss from data.json. Returns {dps, direct, bleed, frost, ttk, procsB, procsF, ar}
  function evaluate(D, w, st, key, T) {
    const steps = D.moves[w.m][key];
    const A = ar(D, w, st, key === "2h");
    let frames = 0, direct = 0, nh = 0;
    for (const [f, hits] of steps) {
      frames += f;
      for (const cands of hits) {
        nh++;
        let best = 0;
        for (const c of cands) {
          let v = 0;
          for (let e = 0; e < 5; e++) {
            if (!A[e] || !c[e]) continue;
            v += eff(A[e] * c[e] / 100, T.df[e]) * (T.mul ? T.mul[e === 0 ? c[5] : e + 3] : 1);
          }
          if (v > best) best = v;
        }
        direct += best;
      }
    }
    const secs = frames / 60, d = direct / secs;
    const out = { dps: d, direct: d, bleed: 0, frost: 0, ttk: 0, procsB: 0, procsF: 0, ar: A, frames: steps.map((s) => s[0]), hits: steps.map((s) => s[1].length) };
    if (!T.hp || d <= 0) return out;
    const hp = T.hp, rate = nh / secs, ev = [];
    if (w.b && T.bleed) {
      let luck = 1;
      if (st[4] < w.req[4]) luck = 0.6;
      else if (w.lc) luck += w.lc * G(D, w.lg, st[4]);
      ev.push({ k: "b", r: w.b[0] * luck * rate, th: T.bleed, dmg: (w.b[1] / 100 * hp + w.b[2]) * T.br / 100 });
    }
    if (w.f && T.frost) ev.push({ k: "f", r: w.f[0] * rate, th: T.frost, dmg: (w.f[1] / 100 * hp + w.f[2]) * T.fr / 100 });
    let t = 0, left = hp, frostUntil = -1;
    const acc = { b: 0, f: 0 }, n = { b: 0, f: 0 }, got = { b: 0, f: 0 };
    for (let it = 0; it < 400; it++) {
      const amp = t < frostUntil ? 1.2 : 1;
      let tn = Infinity, e = null;
      for (const x of ev) {
        const dt = (x.th[Math.min(n[x.k], x.th.length - 1)] - acc[x.k]) / x.r;
        if (dt < tn) { tn = dt; e = x; }
      }
      let dtKill = left / (d * amp);
      if (frostUntil > t && left > d * amp * (frostUntil - t)) dtKill = Math.min(dtKill, frostUntil - t);
      const step = Math.min(dtKill, tn);
      left -= d * amp * step; t += step;
      for (const x of ev) acc[x.k] += x.r * step;
      if (left <= 0) break;
      if (e && Math.abs(step - tn) < 1e-9) {
        acc[e.k] = 0; n[e.k]++; left -= e.dmg; got[e.k] += e.dmg;
        if (e.k === "f") frostUntil = t + 30;
        if (left <= 0) break;
      }
    }
    return Object.assign(out, { dps: hp / t, ttk: t, bleed: got.b / t, frost: got.f / t, procsB: n.b, procsF: n.f });
  }

  function need(w, key) {
    const r = w.req.slice();
    if (key === "2h" && !w.pair) r[0] = Math.ceil(r[0] / 1.5);
    return r;
  }

  // Stats that can change this weapon's damage
  function relevant(w, T) {
    const rel = new Set();
    for (const e of w.el) if (e) e[1].forEach((c, i) => { if (c > 0) rel.add(i); });
    if (T.hp && w.b && w.lc && T.bleed) rel.add(4);
    return [...rel].sort();
  }

  // Free points: requirements first, then greedy by gain per point (looking 1..20 points ahead), then for
  // bleed weapons against a boss, move points into Arcane while that kills faster.
  function optimize(D, w, key, base, budget, T, chunk) {
    if (!D.moves[w.m][key]) return null;
    const nd = need(w, key), st = base.slice();
    let cost = 0;
    for (let i = 0; i < 5; i++) if (st[i] < nd[i]) { cost += nd[i] - st[i]; st[i] = nd[i]; }
    if (cost > budget) return null;
    let left = budget - cost;
    const rel = relevant(w, T), flat = { df: T.df, mul: T.mul, hp: 0 };
    const f = (s) => evaluate(D, w, s, key, flat).dps;
    let cur = f(st);
    const step = chunk || 1;
    while (left > 0 && rel.length) {
      let bg = 0, bi = -1;
      for (const i of rel) {
        for (const c of [1, 5, 10, 20]) {
          if (c > left || st[i] + c > 99) continue;
          const t = st.slice(); t[i] += c;
          const g = (f(t) - cur) / c;
          if (g > bg) { bg = g; bi = i; }
        }
      }
      if (bi < 0) break;
      const a = Math.min(step, left, 99 - st[bi]);
      st[bi] += a; left -= a; cur = f(st);
    }
    if (left > 0) for (const i of [4, 1, 0, 2, 3]) { const a = Math.min(left, 99 - st[i]); st[i] += a; left -= a; }
    let res = evaluate(D, w, st, key, T);
    if (T.hp && w.lc && w.b && T.bleed) {
      for (let k = 0; k < 20; k++) {
        let better = null, bs = null;
        for (const i of rel) {
          if (i === 4 || st[i] - 5 < nd[i]) continue;
          const t = st.slice(); t[i] -= 5; t[4] = Math.min(99, t[4] + 5);
          const r = evaluate(D, w, t, key, T);
          if (r.dps > res.dps + 1e-6 && (!better || r.dps > better.dps)) { better = r; bs = t; }
        }
        if (!better) break;
        res = better; st.splice(0, 5, ...bs);
      }
    }
    return Object.assign(res, { stats: st, move: key });
  }

  function evalFixed(D, w, key, st, T) {
    if (!D.moves[w.m][key] || !meets(w, st, key === "2h")) return null;
    return Object.assign(evaluate(D, w, st, key, T), { stats: st.slice(), move: key });
  }

  const api = { eff, ar, meets, evaluate, optimize, evalFixed, flatTarget, relevant, MOVES, STATS };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.ER = api;
})(this);
