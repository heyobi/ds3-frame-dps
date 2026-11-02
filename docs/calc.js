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
  // ng: 0 = NG, 1..7 = NG+..NG+7 (the boss's NG+ effect on top of its NG scaling, then ClearCountCorrectParam HP / defense / status per cycle).
  // zone: body part damage rate (1 = body; weak points 1.5 to 2.0 on some bosses), applied to direct damage.
  function bossTarget(b, stamina, ng, zone, cc) {
    ng = ng || 0;
    const base = ng > 0 && b.ngp ? b.ngp : b;
    const k = ng > 0 && cc ? cc[Math.min(ng, cc.length) - 1] : [1, 1, 1];
    const df = base.df.map((d, i) => d * (k[3 + i] || 1));
    return { def: df, mul: b.mul, hp: Math.round(base.hp * k[0]),
             bleed: base.bleed == null ? null : base.bleed * k[1], frost: base.frost == null ? null : base.frost * k[2],
             bloodRate: b.bloodRate, stamina: !!stamina, zone: zone || 1 };
  }
  // Weapon buffs, all from SpEffectParam. Resins: flat AR (magicAtkPower etc.). Spells: the same fields hold the % of the
  // catalyst's Spell Buff (spell rows 1013xxxxx-1037xxxxx). Blessed Weapon: physAtkPowerRate x1.075. Only weapons with no elemental damage can be buffed.
  // Paired weapons get less from resins and Blessed Weapon; the factors below were fitted to himheart's in-game
  // measurements of Sellsword Twinblades L1 (resins 62/65 exact, Blessed 17/17). Spell buffs are not reduced: Carthus
  // Flame Arc with the in-game spell buff (Pyromancy Flame +10 at 99/99 = 242) matches 16/16 at full value.
  const BUFFS = {
    charcoal: { e: 2, add: 85 }, gold: { e: 3, add: 95 }, pale: { e: 1, add: 90 }, human: { e: 4, add: 95 },
    // req: [Int, Faith] to cast (Magic param)
    mw: { e: 1, pct: 75, req: [10, 0], sch: 0 }, gmw: { e: 1, pct: 85, req: [15, 0], sch: 0 }, cmw: { e: 1, pct: 95, req: [30, 0], sch: 0 },
    lb: { e: 3, pct: 95, req: [0, 30], sch: 1 }, dmb: { e: 1, pct: 95, req: [0, 30], sch: 1 }, db: { e: 4, pct: 85, req: [0, 25], sch: 1 },
    cfa: { e: 2, pct: 80, req: [10, 10], sch: 2 }, blessed: { phys: 1.075, req: [0, 15], sch: 1 },
  };
  const PAIRED_BUFF = 0.826, PAIRED_BLESSED = 0.8;
  // Rings (SpEffectParam via EquipParamAccessory). ar: AtkPowerRate (on attack rating, before defense);
  // dmg: DamageRate2 (on damage, after defense); st: stat bonus [str,dex,int,fth,lck] (counts for requirements).
  const RINGS = {
    clutchM: { dmg: [1, 1.15, 1, 1, 1] }, clutchF: { dmg: [1, 1, 1.15, 1, 1] }, clutchL: { dmg: [1, 1, 1, 1.15, 1] }, clutchD: { dmg: [1, 1, 1, 1, 1.15] },
    lloyd: { ar: [1.1, 1.1, 1.1, 1.1, 1.1] },                 // at full HP
    rts: { dmg: [1.2, 1.2, 1.2, 1.2, 1.2] },                  // HP at or below 20%
    flynn: { ar: [1.15, 1, 1, 1, 1], status: 1.15 },          // max value (low equip load); also bleed / poison buildup x1.15
    pontiff: { ar: [1.1, 1.1, 1.1, 1.1, 1.1] },               // top stack while attacking without a break (1.03 -> 1.05 -> 1.10)
    knight: { st: [5, 0, 0, 0, 0] }, hunter: { st: [0, 5, 0, 0, 0] }, scholar: { st: [0, 0, 5, 0, 0] }, priestess: { st: [0, 0, 0, 5, 0] },
    milk: { st: [0, 3, 0, 0, 0] },
  };
  function ringMods(ids, crown) {
    const m = { ar: [1, 1, 1, 1, 1], dmg: [1, 1, 1, 1, 1], st: [0, 0, 0, 0, 0], status: 1 };
    for (const id of ids || []) {
      const r = RINGS[id]; if (!r) continue;
      for (let i = 0; i < 5; i++) { if (r.ar) m.ar[i] *= r.ar[i]; if (r.dmg) m.dmg[i] *= r.dmg[i]; if (r.st) m.st[i] += r.st[i]; }
      if (r.status) m.status *= r.status;
    }
    if (crown) m.dmg[1] *= 1.05;                              // Crown of Dusk
    return m;
  }
  const addSt = (st, T) => T && T.sbon ? st.map((v, i) => Math.min(99, v + T.sbon[i])) : st;
  // Hollow infusion: +Luck while hollow with 15+ hollowing (resident SpEffect 1290015xx: +2 at +0 ... +5 at +10)
  const HOLLOW_LCK = [2, 3, 3, 3, 3, 4, 4, 4, 4, 4, 5];
  const hollowSt = (w, li, st, T) => T && T.hollow && w.i === "Hollow" ? st.map((v, i) => i === 4 ? Math.min(99, v + HOLLOW_LCK[Math.min(li, 10)]) : v) : st;
  // Catalyst spell buff from the player's stats (tools/ds3_catalysts.py): 100 x (1 + (cInt x S(Int) + cFth x S(Fth)) / 10000),
  // rounded down; Archdeacon's Great Staff counts as 100 for weapon buffs (wiki). buff.cat: "best" = strongest catalyst of
  // the spell's school whose requirements the stats meet (fully upgraded), a catalyst index, or undefined = buff.sb as typed.
  function catSB(D, c, st) {
    if (c.n === "Archdeacon's Great Staff") return 100;
    const S = (g, v) => (D.sats[g] ? D.sats[g][Math.max(0, Math.min(99, v))] : 0);
    return Math.floor(100 * (1 + (c.c[0] * S(c.g[0], st[2]) + c.c[1] * S(c.g[1], st[3])) / 10000));
  }
  function spellBuff(D, buff, st) {
    const b = BUFFS[buff.id];
    if (buff.cat == null || !D || !D.cats) return Math.floor(buff.sb || 0);
    const ok = (c) => c.school[b.sch] && st[0] >= c.req[0] && st[2] >= c.req[1] && st[3] >= c.req[2];
    if (buff.cat === "best") { let m = 0; for (const c of D.cats) if (ok(c)) m = Math.max(m, catSB(D, c, st)); return m; }
    const c = D.cats[buff.cat]; return c && ok(c) ? catSB(D, c, st) : 0;
  }
  function buffable(w, li) { const L = w.lv[li]; return !(L[1] || L[2] || L[3] || L[4]); }
  function applyBuff(w, li, A, buff, st, D) {
    const b = buff && BUFFS[buff.id];
    if (!b || !buffable(w, li)) return A;
    if (b.req && st && (st[2] < b.req[0] || st[3] < b.req[1])) return A;       // can't cast the spell with these stats
    const paired = /Paired/.test(w.c), out = A.slice();
    if (b.phys) out[0] *= 1 + (b.phys - 1) * (paired ? PAIRED_BLESSED : 1);
    else if (b.add != null) out[b.e] += b.add * (paired ? PAIRED_BUFF : 1);          // resins: reduced on paired weapons
    else out[b.e] += b.pct / 100 * spellBuff(D, buff, st);                           // spells: not reduced (measured)
    return out;
  }
  const REGEN = 45;          // base stamina per second; Chloranthy Ring / Green Blossom add to it (T.regen)
  const FROST_AMP = 0.07, FROST_TIME = 14;   // frostbite: target takes 7% more damage for 14 s

  // One full 3-step chain against target T. Returns dps and its parts.
  function chainEval(D, w, key, li, st, T) {
    const steps = D.moves[w.n][key];
    const stE = hollowSt(w, li, addSt(st, T), T);
    const A = applyBuff(w, li, ar(D, w, li, stE, { twoHand: key !== "r1h" }), T.buff, stE, D).map((v, i) => v * (T.armul ? T.armul[i] : 1));
    let direct = 0, frames = 0, hits = 0, stam = 0;
    const stepDmg = [];            // damage of each press as the game shows it (every hit rounded down)
    for (const [f, sc, hs] of steps) {
      frames += f; stam += sc;
      let sd = 0;
      for (const h of hs) {
        hits++;
        let hd = 0;
        for (let e = 0; e < 5; e++) {
          if (!h[e] || !A[e]) continue;
          const m = T.mul ? T.mul[e === 0 ? h[5] : e + 3] : 1;
          hd += eff(A[e] * h[e] / 100, T.def[e]) * m * (T.zone || 1) * (T.emul ? T.emul[e] : 1);
        }
        direct += hd; sd += Math.floor(hd);
      }
      stepDmg.push(sd);
    }
    let t = frames / 60;
    const stamUse = stam * (w.scr || 1);
    if (T.stamina) t += stamUse / (T.regen || REGEN);   // no regen while attacking, so every point spent costs 1/regen s
    let bleed = 0, frost = 0;
    if (T.hp) {
      const L = w.lv[li];
      if (L[10] > 0 && T.bleed && w.pb) {
        const luck = 1 + (w.lc || 0) / 100 * L[12] * (D.sats[w.sb] ? D.sats[w.sb][Math.min(99, stE[4])] / 100 : 0);
        const procs = hits * L[10] * luck * (T.status || 1) / T.bleed;
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
    const rate = (direct + bleed + frost) / t;
    // T.metric "hit": rank and optimize by the damage of one press (first attack of the chain) instead of DPS
    return { dps: T.metric === "hit" ? stepDmg[0] : rate, rate, hit: stepDmg[0], stepDmg, ar: A, frames: steps.map(x => x[0]),
             parts: { direct: direct / t, bleed: bleed / t, frost: frost / t }, stamina: stamUse / steps.length, secs: t / steps.length };
  }

  function wieldable(w, st, twoHand, T) {
    st = addSt(st, T);
    return st[0] * (twoHand ? 1.5 : 1) >= w.req[0] && st[1] >= w.req[1] && st[2] >= w.req[2] && st[3] >= w.req[3];
  }
  const needOf = (w, twoHand, T) => {
    const b = (T && T.sbon) || [0, 0, 0, 0, 0];
    const sp = T && T.buff && BUFFS[T.buff.id] && BUFFS[T.buff.id].req && buffable(w, w.lv.length - 1) ? BUFFS[T.buff.id].req : [0, 0];
    return [twoHand ? Math.ceil(w.req[0] / 1.5) - b[0] : w.req[0] - b[0], w.req[1] - b[1], Math.max(w.req[2], sp[0]) - b[2], Math.max(w.req[3], sp[1]) - b[3], 0];
  };

  // Which stats can change this weapon's damage at this level
  function relevant(w, li, T) {
    const L = w.lv[li], d = L.slice(0, 5), s = L.slice(5);
    const out = [];
    if (s[0] > 0 && d[0] > 0) out.push(0);
    if (s[1] > 0 && d[0] > 0) out.push(1);
    if (s[2] > 0 && (d[1] > 0 || d[2] > 0 || d[4] > 0)) out.push(2);
    if (s[3] > 0 && (d[2] > 0 || d[3] > 0 || d[4] > 0 || (w.i === "Blessed" && d[0] > 0))) out.push(3);
    if ((s[4] > 0 && d[0] > 0) || (T && T.bleed && L[10] > 0 && w.lc > 0)) out.push(4);
    const sp = T && T.buff && T.buff.cat != null && BUFFS[T.buff.id] && BUFFS[T.buff.id].pct && buffable(w, li);
    if (sp) {                                                                    // the catalyst's spell buff grows with Int / Faith
      const sch = BUFFS[T.buff.id].sch, add = sch === 0 ? [2] : sch === 1 ? [3] : [2, 3];
      for (const i of add) if (!out.includes(i)) out.push(i);
    }
    out.sort();
    return out;
  }

  // Fixed stats: DPS of one move
  function evalMove(D, w, key, st, up, T) {
    const mvset = D.moves[w.n][key];
    if (!mvset || !wieldable(w, st, key !== "r1h", T)) return null;
    return Object.assign({ move: key, stats: st.slice() }, chainEval(D, w, key, levelIndex(w, up), st, T));
  }

  // Free points: meet requirements first, then search the spread of the rest over the stats that matter
  function optimizeMove(D, w, key, base, budget, up, T) {
    const mvset = D.moves[w.n][key];
    if (!mvset) return null;
    const twoHand = key !== "r1h";
    const li = levelIndex(w, up);
    const st = base.slice();
    const need = needOf(w, twoHand, T);
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
    if (k === 0) tryOne();
    else if (units <= 14 || T.exhaustive) rec(0, units);
    else {
      // coarse grid, then move points between pairs of stats while it helps, halving the step down to the base step
      let big = step * Math.ceil(units / 10);
      const cu = Math.floor(R / big);
      const save = units;
      const recC = (j, left) => {
        if (j === k - 1) { const i = rel[j]; const keep = cur[i]; cur[i] += left * big; tryC(); cur[i] = keep; return; }
        const i = rel[j], keep = cur[i];
        for (let u = 0; u <= left; u++) { cur[i] = keep + u * big; if (cur[i] > 99 + big) break; recC(j + 1, left - u); }
        cur[i] = keep;
      };
      const cands = [];
      const memo = new Map();
      const evalT = (t) => {
        const c = t.map(v => Math.min(99, v)), kk = c.join(",");
        let v = memo.get(kk); if (v === undefined) { v = chainEval(D, w, key, li, c, T).dps; memo.set(kk, v); }
        return v;
      };
      const tryC = () => { const t = cur.slice(); t[rel[0]] += R - cu * big; cands.push({ t, d: evalT(t) }); };
      recC(0, cu);
      cands.sort((x, y) => y.d - x.d);
      const climb = (t, d) => {
        for (let sz = big; sz >= 1; sz = Math.floor(sz / 2)) {
          let moved = true;
          while (moved) {
            moved = false;
            for (const a of rel) for (const b of rel) {
              if (a === b || t[a] - sz < st[a] || t[b] >= 99) continue;
              const n = t.slice(); n[a] -= sz; n[b] += sz;
              const nd = evalT(n);
              if (nd > d + 1e-9) { t = n; d = nd; moved = true; }
            }
          }
        }
        // line search: for every pair, every transfer size up to two coarse steps, keep the best; repeat while it helps
        let again = true;
        while (again) {
          again = false;
          for (const a of rel) for (const b of rel) {
            if (a === b) continue;
            let bt = null, bd = d;
            for (let q = 1; q <= 2 * big; q++) {
              if (t[a] - q < st[a] || t[b] + q > 99 + q - 1 && t[b] >= 99) break;
              const n = t.slice(); n[a] -= q; n[b] += q;
              const nd = evalT(n);
              if (nd > bd + 1e-9) { bd = nd; bt = n; }
            }
            if (bt) { t = bt; d = bd; again = true; }
          }
        }
        return { t, d };
      };
      let bc = null;
      for (const c of cands.slice(0, 4)) { const r = climb(c.t, c.d); if (!bc || r.d > bc.d + 1e-9) bc = r; }
      const fin = bc.t.map(v => Math.min(99, v));
      best = Object.assign({ move: key, stats: fin }, chainEval(D, w, key, li, fin, T));
      void save;
    }
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

  // Best result for one weapon over the enabled moves (same rules as rank)
  function bestFor(D, w, opts, T) {
    let best = null;
    const per = {};
    for (const key of Object.keys(MOVES)) {
      if (!opts.moves[key]) continue;
      const r = opts.mode === "opt" ? optimizeMove(D, w, key, opts.base, opts.budget, opts.up, T)
                                    : evalMove(D, w, key, opts.stats, opts.up, T);
      if (!r) continue;
      per[key] = r.dps;
      if (!best || r.dps > best.dps) best = r;
    }
    return best && Object.assign({ w, per, T }, best);
  }
  // Auto-pick: best buff, then rings added one at a time (each time the one that adds most), for one weapon.
  // auto: { buff: bool, buffs: [ids], sb, rings: bool, pool: [ids], slots, crown }
  function withPicks(T, buff, rings, auto) {
    const m = ringMods(rings, auto.crown);
    return Object.assign({}, T, { buff, emul: m.dmg, armul: m.ar, sbon: m.st, status: m.status });
  }
  function autoPick(D, w, opts, auto) {
    const T0 = opts.def;
    let buff = T0.buff || null, rings = (auto.fixed || []).slice();
    const start = bestFor(D, w, opts, withPicks(T0, buff, rings, auto));
    if (!start) return null;
    // choose with the stats fixed at the current best spread (fast), re-optimize the spread at the end
    const key = start.move, li = levelIndex(w, opts.up);
    let st = start.stats.slice();
    const score = (b, rg) => {
      const T = withPicks(T0, b, rg, auto);
      if (opts.mode === "opt") {                       // keep the spell's stat requirement inside the budget
        const sp = b && BUFFS[b.id] && BUFFS[b.id].req;
        if (sp) {
          const t = st.slice(), sb = T.sbon || [0, 0, 0, 0, 0];
          // quick estimate: take the missing Int / Faith from the stat that has the most points (the final pass re-optimizes)
          const need = [Math.max(0, sp[0] - sb[2] - t[2]), Math.max(0, sp[1] - sb[3] - t[3])];
          let extra = need[0] + need[1];
          if (extra > 0) {
            t[2] += need[0]; t[3] += need[1];
            for (const i of [1, 0, 4, 2, 3]) { const free = Math.max(0, t[i] - Math.max(opts.base[i], i < 4 ? needOf(w, key !== "r1h", T)[i] : 0)); const a = Math.min(free, extra); t[i] -= a; extra -= a; }
            if (extra > 0) return -1;
            return wieldable(w, t, key !== "r1h", T) ? chainEval(D, w, key, li, t, T).dps : -1;
          }
        }
      }
      return wieldable(w, st, key !== "r1h", T) ? chainEval(D, w, key, li, st, T).dps : -1;
    };
    let curS = score(buff, rings);
    if (auto.buff) {
      for (const id of auto.buffs) {
        const b = { id, sb: auto.sb, cat: auto.cat }, v = score(b, rings);
        if (v > curS + 1e-9) { curS = v; buff = b; }
      }
    }
    if (auto.rings) {
      while (rings.length < auto.slots) {
        let pick = null, pv = curS;
        for (const id of auto.pool) {
          if (rings.includes(id) || (id === "lloyd" && rings.includes("rts")) || (id === "rts" && rings.includes("lloyd"))) continue;
          const v = score(buff, rings.concat([id]));
          if (v > pv + 1e-9) { pv = v; pick = id; }
        }
        if (!pick) break;
        rings.push(pick); curS = pv;
      }
    }
    const cur = bestFor(D, w, opts, withPicks(T0, buff, rings, auto));
    if (!cur) return start;
    cur.picks = { buff: buff && buff.id, rings };
    return cur;
  }
  // Re-rank with auto picks: every weapon is ranked normally first, then the top `n` get their own picks
  function rankAuto(D, opts, auto, n) {
    const base = rank(D, opts);
    const top = base.slice(0, n || 60).map(r => autoPick(D, r.w, opts, auto)).filter(Boolean);
    const done = new Set(top.map(r => r.w));
    const rows = top.concat(base.filter(r => !done.has(r.w)));
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
    const need = needOf(w, twoHand, T);
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

  const api = { eff, ar, rank, rankAuto, spellBuff, catSB, autoPick, BUFFS, RINGS, ringMods, buffable, applyBuff, flatTarget, bossTarget, chainEval, optimizeMove, evalMove, levelPath, levelIndex, MOVES, STATS };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.DS3 = api;
})(this);
