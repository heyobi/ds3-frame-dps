# Dark Souls III: light-attack DPS for every weapon, from game data

Sustained light-attack DPS for every melee weapon and infusion in Dark Souls III, computed from the game's own
animation timing (TAE) and weapon parameters, with the stat spread that maximises it.

Existing community frame data covers a handful of reference weapons per class, measured from video or from an
early regulation. This set reads the attack and cancel frames for every weapon moveset straight out of
`c0000.anibnd.dcx`, including paired weapons, fists, claws, whips, reapers and DLC weapons.

**Game version:** App ver. 1.15.2, Regulation ver. 1.35, Ashes of Ariandel + The Ringed City (Steam, PC)

## Headline result

Against a flat 120 defense, SL120, +10 / +5 weapons, no buffs, no bleed:

| # | Weapon (wiki) | Infusion | Move | s / attack | DPS def 80 | DPS def 120 | DPS def 160 | Str/Dex/Int/Fth/Lck |
|---|---|---|---|---|---|---|---|---|
| 1 | [Sellsword Twinblades](https://darksouls3.wiki.fextralife.com/Sellsword_Twinblades) | Sharp | L1 dual | 0.733 | 828 | 743 | 698 | 16/91/10/10/10 |
| 2 | [Warden Twinblades](https://darksouls3.wiki.fextralife.com/Warden_Twinblades) | Sharp | L1 dual | 0.733 | 747 | 669 | 630 | 22/85/10/10/10 |
| 3 | [Friede's Great Scythe](https://darksouls3.wiki.fextralife.com/Friede%27s_Great_Scythe) | none (unique) | 2H R1 | 0.944 | 680 | 616 | 569 | 16/58/40/13/10 |
| 4 | [Gotthard Twinswords](https://darksouls3.wiki.fextralife.com/Gotthard_Twinswords) | Chaos | L1 dual | 0.922 | 703 | 613 | 522 | 28/37/31/31/10 |
| 5 | [Falchion](https://darksouls3.wiki.fextralife.com/Falchion) | Sharp | 2H R1 | 0.656 | 661 | 603 | 558 | 22/85/10/10/10 |
| 6 | [Rotten Ghru Curved Sword](https://darksouls3.wiki.fextralife.com/Rotten_Ghru_Curved_Sword) | Sharp | 2H R1 | 0.611 | 660 | 598 | 553 | 16/91/10/10/10 |
| 7 | [Winged Knight Twinaxes](https://darksouls3.wiki.fextralife.com/Winged_Knight_Twinaxes) | Refined | L1 dual | 1.111 | 661 | 596 | 552 | 46/61/10/10/10 |
| 8 | [Exile Greatsword](https://darksouls3.wiki.fextralife.com/Exile_Greatsword) | Chaos | 2H R1 | 1.022 | 652 | 590 | 547 | 28/37/31/31/10 |
| 9 | [Dancer's Enchanted Swords](https://darksouls3.wiki.fextralife.com/Dancer%27s_Enchanted_Swords) | none (unique) | L1 dual | 0.956 | 724 | 589 | 457 | 25/37/40/25/10 |
| 10 | [Scimitar](https://darksouls3.wiki.fextralife.com/Scimitar) | Sharp | 2H R1 | 0.611 | 649 | 588 | 544 | 10/97/10/10/10 |

Weapon names link to the Fextralife DS3 wiki (location, requirements, pictures). "L1 dual" means two-handing the paired weapon and chaining L1; "2H R1" means two-handing and chaining R1.

Best weapon for fixed builds (defense 120):

| Build (Str/Dex/Int/Fth/Lck) | Best | DPS |
|---|---|---|
| Pure Str 66/10/10/10/10 | Heavy [Broadsword](https://darksouls3.wiki.fextralife.com/Broadsword) (2H R1) | 525 |
| Pure Dex 18/60/10/10/10 | Sharp [Sellsword Twinblades](https://darksouls3.wiki.fextralife.com/Sellsword_Twinblades) (L1) | 649 |
| Quality 40/40/10/10/10 | Refined [Sellsword Twinblades](https://darksouls3.wiki.fextralife.com/Sellsword_Twinblades) (L1) | 632 |
| Int 18/18/60/10/10 | Crystal [Sellsword Twinblades](https://darksouls3.wiki.fextralife.com/Sellsword_Twinblades) (L1) | 554 |
| Faith 18/18/10/60/10 | Lightning [Sellsword Twinblades](https://darksouls3.wiki.fextralife.com/Sellsword_Twinblades) (L1) | 554 |
| Int+Faith 16/16/40/40/10 | Chaos [Sellsword Twinblades](https://darksouls3.wiki.fextralife.com/Sellsword_Twinblades) (L1) | 588 |
| Luck 18/18/10/10/60 | [Anri's Straight Sword](https://darksouls3.wiki.fextralife.com/Anri%27s_Straight_Sword) (2H R1) | 479 |

Full tables: `results/dps_all_weapons.csv` (1662 weapon/infusion rows) and `results/dps_best_per_build.csv`.

## Files

| File | What it is |
|---|---|
| `data/ds3_frames_full.txt` | Raw output of `tools/ds3_frames.py ... full` |
| `data/tae_light_attack_frames.csv` | Every light-attack animation (1H R1, 2H R1, paired L1, R2 starts) in every player TAE: attack hitbox windows, R/L attack cancel frame, and the animation it imports events from |
| `data/weapon_motion_categories.csv` | Weapon → `wepmotionCategory` (base moveset TAE) and `spAtkCategory` (weapon-specific override TAE), read from `EquipParamWeapon` |
| `results/weapon_chains.csv` | Per weapon: resolved 1H R1, 2H R1 and dual L1 chain frames and the source animations |
| `results/dps_all_weapons.csv` | Per weapon and infusion: best move, timing, motion values, optimal stats, AR split, DPS at defense 80/120/160, DPS for 7 fixed builds |
| `results/dps_best_per_build.csv` | Top 10 per fixed build |
| `tools/ds3_frames.py` | Extractor (read-only, pure Python 3, no dependencies; uses `cryptography` if installed, otherwise a built-in AES) |
| `tools/compute_dps.py` | DPS model (Python 3 + numpy) |

All frame numbers are at 60 fps.

## Method

**Extraction.** `ds3_frames.py` decrypts the archive headers (`Data1-5.bhd`, `DLC1-2.bhd`) with the public RSA keys
used by UXM, finds `/chr/c0000.anibnd.dcx` (it lives in `Data3`), AES-decrypts and inflates it, and parses every
TAE3 file in it. From each animation it reads `AttackBehavior` events (type 1, hitbox windows) and
`ChrActionFlag` events (type 0) with flag 4 "Cancel - RH Attack" and flag 16 "Cancel - LH Attack". It also
decrypts the regulation (`Data0.bdt`) and reads `wepmotionCategory` (offset 227) and `spAtkCategory` (offset 234)
from `EquipParamWeapon`. Nothing is written into the game folder.

**Which animation a weapon uses.** For each attack ID the weapon's `spAtkCategory` TAE is checked first, then its
`wepmotionCategory` TAE. Animations that carry no events but import another animation (`ImportOtherAnim`) are
followed to the source.

**Animation IDs.** `30000/30010/30020` = 1H R1 chain, `34000/34010/34020` = 2H R1 chain,
`33000/33010/33020` = two-handed L1 of paired weapons and fists (dual attacks). For paired weapons the 2H R1 is an
import of the 1H R1 (single blade), which matches the community frame data for Gotthard.

**Attack duration.** Each chain step lasts from the start of the animation until the first frame of the
"Cancel - RH Attack" window (R1 chains) or "Cancel - LH Attack" window (L1 chains), i.e. the earliest frame the
next attack can start with a buffered input. DPS uses the mean of the three steps.

**Damage.** AR uses the standard DS3 formula from the DS3InventoryBuilder weapon data (base damage, scaling,
CalcCorrectGraph). Each hit is AR × motion value, per element, through the DS-series attack/defense curve against
a flat defense. Two-handing multiplies Str by 1.5.

**Stats.** SL120 Deprived, Vigor 27 / Attunement 10 / Endurance 20 / Vitality 15 fixed, remaining 87 points spread
over Str/Dex/Int/Fth/Lck on a 3-point grid, maximising DPS at defense 120 for each weapon and infusion separately.

## Validation

Weapon weights read from `EquipParamWeapon` match the known values (Dagger 1.5, Zweihander 10, etc.), and the
param row size (608 bytes) matches the Paramdex definition. Chain timings agree with the regulation 1.08
community frame data (startup + active + R1 cancel). For single-hit R1 chains the game data is 2 to 10 frames
longer per step, never shorter:

| Moveset (2H R1 1/2/3) | This data | Community sheet |
|---|---|---|
| Longsword | 42 / 48 / 38 | 38 / 44 / 34 |
| Scimitar | 38 / 42 / 38 | 32 / 32 / 34 |
| Chaos Blade | 40 / 48 / 44 | 36 / 44 / 40 |
| Estoc | 46 / 44 / 46 | 42 / 40 / 42 |
| Zweihander | 82 / 76 / 78 | 76 / 68 / 72 |
| Lucerne | 62 / 74 / 66 | 60 / 70 / 64 |
| Caestus L1 dual | 36 / 42 / 40 | 46 / 40 / 36 |

The offset is probably the difference between the cancel window opening and the first frame a buffered input
actually starts the next animation. It pushes all R1 chains in the same direction, so the ranking between them
should hold. The Caestus dual chain does not follow the same pattern (similar total, 118 vs 122 frames, different order); the sheet's
row may come from a different input sequence, and L1 chains in general would benefit from an in-game check.

## Not modelled

Stamina (sustained L1 spam on paired weapons drains fast), bleed / poison / frost buildup, weapon buffs, rings,
the "sweet spot" bonus (flag 42), counter hits, hyper armor, reach and tracking. Motion values come from the
community AtkParam motion-value sheet, not from this extraction. Ringed Knight Paired Greatswords, Giant Door
Shield and Dark Hand are left out (unclear motion values). A few chains could not be resolved because the
middle step has no RH cancel flag (Farron Greatsword 1H/2H R1); those rows are empty.

## Reproduce

```
python3 tools/ds3_frames.py "<...>/DARK SOULS III/Game" discover            # sanity check
python3 tools/ds3_frames.py "<...>/DARK SOULS III/Game" full data/ds3_frames_full.txt
git clone https://github.com/Phil25/DS3InventoryBuilder
python3 tools/compute_dps.py --frames data/ds3_frames_full.txt \
    --weapons DS3InventoryBuilder/DataGenerator/Raw --out results
```

## Credits

Archive keys and BHD5 layout: UXM Selective Unpacker (Nordgaren, TKGP). File formats (BHD5, DCX, BND4, TAE3,
PARAM): SoulsFormats (TKGP). TAE event meanings: DSAnimStudio DS3 template (Meowmaritus). Param layout: Paramdex
(soulsmods). Weapon damage and scaling data: DS3InventoryBuilder (Phil25), from the monrandira / pireax
spreadsheet. Motion values: DS3 Motion Values sheet. Reference frame data: DS3 frame data sheets linked from the
darksouls3.wikidot links page.

No game files are included in this repository.

## License

MIT, see `LICENSE`. Dark Souls III and its data belong to FromSoftware / Bandai Namco; no game files are included here.
