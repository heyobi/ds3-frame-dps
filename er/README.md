# Elden Ring (work in progress)

Prototype of the same light-attack DPS pipeline for Elden Ring. Not finished; numbers are not final.

- `tools/er_extract.py`: pull files out of the encrypted archives (read-only)
- `er/krak`: tiny Rust wrapper around the oozextract crate to decompress Oodle Kraken DCX files
- `er/er_load.py`, `er/er_model.py`, `er/er_rank.py`: params + TAE loading, AR / chain model, first ranking
