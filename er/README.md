# Elden Ring (work in progress)

The same light-attack DPS pipeline as the DS3 tables, ported to Elden Ring. It reads the game files only and writes nothing to the game folder. The numbers are close to final, but nothing here has been tested in game yet.

## What the model does

- **Attack rating**: base damage × upgrade rate × (1 + Σ scaling × CalcCorrectGraph), using the AttackElementCorrect rules. Two-handing multiplies Strength by 1.5, except on paired weapons. An unmet requirement gives −40% on every element that stat scales. `validate_ar.py` checks 2400 random weapon, stat and upgrade combinations against [ThomasJClark's calculator](https://github.com/ThomasJClark/elden-ring-weapon-calculator). Every melee weapon matches to within 0.6 AR, and bleed and frost buildup match too. Bows are the only mismatches, because the calculator always counts them as two-handed and this model leaves bows out.
- **Moves**: 1H R1 (anim 30000+), 2H R1 (32000+), and powerstance / dual L1 (34000+, the same weapon in both hands, with 1H stats). Each step ends at the first R1-cancel flag (4 or 115).
- **Hit counting**: Hit windows from the same hand that touch or overlap are one swing, and only the strongest phase counts. Different hands, or windows that are separate in time, count as separate hits. Light greatswords also have stamina-free 99x hitboxes; these are dropped, because the wiki hit counts (5th light attack hits twice, 3rd dual attack 3 times, 4th dual attack 4 times) only come out right without them.
- **Bosses**: HP, defense, absorption, area scaling, status resistance and its growth after each proc (ResistCorrectParam), and the bleed and frost damage rates. Bleed procs deal 15% HP + 100. Frost procs deal 10% HP + 30, and the target takes 20% more damage for 30 s afterwards. Time to kill comes from an event simulation.

## Known gaps

- Frost buildup decay is not modeled, so frost may be overvalued against bosses that are hit slowly.
- Powerstance assumes two copies of the weapon. Some unique weapons only have one copy per playthrough.
- No stamina limit yet.

## Files

- `tools/er_extract.py`: pulls files out of the encrypted archives (read-only).
- `er/krak`: a small Rust wrapper around the oozextract crate that decompresses Oodle Kraken DCX files.
- `er/er_load.py`: params + TAE → `er.pkl`. Set `ER_FILES` to the folder holding `c0000.anibnd` and `params/`, and `PARAMDEX_ER` to Paramdex's ER folder.
- `er/er_model.py`: AR, chains, hit grouping, bosses, status, the time-to-kill simulation.
- `er/er_rank2.py`: optimizes stats per weapon, infusion and move against a flat target or a named boss. Example: `python3 er/er_rank2.py "Malenia, Blade of Miquella"`.
- `er/validate_ar.py` + `validate_ar_ref.ts`: AR check against the reference calculator. Clone the calculator into `er/` and run with Node 22 or newer.
