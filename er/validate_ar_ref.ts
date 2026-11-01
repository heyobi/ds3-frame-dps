import fs from "node:fs";
import { decodeRegulationData } from "./elden-ring-weapon-calculator/src/regulationData.ts";
import getWeaponAttack from "./elden-ring-weapon-calculator/src/calculator/calculator.ts";
const raw = JSON.parse(fs.readFileSync(new URL("./elden-ring-weapon-calculator/public/regulation-vanilla-v1.17.js", import.meta.url), "utf8"));
const W = decodeRegulationData(raw);
const cases = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const out = [];
for (const c of cases) {
  const w = W.find(x => x.name === c.name);
  if (!w) { out.push(null); continue; }
  const [str, dex, int, fai, arc] = c.stats;
  const r = getWeaponAttack({ weapon: w, attributes: { str, dex, int, fai, arc }, twoHanding: c.th, upgradeLevel: c.up });
  out.push(r.attackPower);
}
console.log(JSON.stringify(out));
