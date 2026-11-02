#!/usr/bin/env python3
"""Dot plot of results/reach.md: every weapon's light-attack reach, one row per class -> results/reach.png"""
import re, sys, collections
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

src = sys.argv[1] if len(sys.argv) > 1 else "results/reach.md"
out = sys.argv[2] if len(sys.argv) > 2 else "results/reach.png"
by = collections.defaultdict(list)
for line in open(src):
    c = [x.strip() for x in line.strip().strip("|").split("|")]
    if len(c) == 8 and re.match(r"\d", c[3] or ""):
        v = [float(x) for x in (c[5], c[7]) if x]
        if v:
            by[c[1].replace(" (Paired)", "")].append((max(v), c[0]))
classes = sorted(by, key=lambda k: max(v for v, _ in by[k]))
INK, MUTED, DOT, HI, BG = "#1d1c1a", "#8a877f", "#c9b8ad", "#a8461f", "#ffffff"
fig, ax = plt.subplots(figsize=(10, 0.36 * len(classes) + 1.2), dpi=150)
fig.patch.set_facecolor(BG)
for i, k in enumerate(classes):
    vals = sorted(by[k])
    ax.scatter([v for v, _ in vals], [i] * len(vals), s=22, color=DOT, zorder=2, linewidths=0)
    v, n = vals[-1]
    ax.scatter([v], [i], s=34, color=HI, zorder=3, linewidths=0)
    ax.text(v + 0.03, i, n, va="center", fontsize=8, color=INK)
ax.set_yticks(range(len(classes)), classes, fontsize=8.5, color=INK)
ax.set_xlabel("Reach of the light attack: hand to far end of the hitbox (m). Longest in each class highlighted.", color=MUTED, fontsize=8.5)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color("#e3e1db")
ax.tick_params(axis="y", length=0)
ax.tick_params(axis="x", colors=MUTED, labelsize=8)
ax.grid(axis="x", color="#eeece7", linewidth=0.8)
ax.set_axisbelow(True)
ax.set_xlim(0.4, 3.3)
fig.tight_layout()
fig.savefig(out, facecolor=BG)
print(out)
