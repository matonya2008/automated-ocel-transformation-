"""
Regenerate the miner-comparison radar chart (Fig6_Miner_Comparison.png)
with clean, non-overlapping radial labels.

Fixes applied vs. the original Revision-2 version:
- Fewer radial ticks (0.60, 0.70, 0.80, 0.90, 1.00) so labels do not overlap.
- Radial labels are placed at a 45° offset (between Precision and Fitness)
  where they sit in empty space away from the plotted data.
- Larger figure canvas (9 in) and generous padding so the legend and labels
  have room to breathe.
- Uses the shared MATLAB palette from pub_style.py for consistency.
"""

from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from pub_style import apply_pub_style, pub_savefig, PUB_DPI, MATLAB_COLORS

apply_pub_style()

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Data (same values used in the manuscript)
# ---------------------------------------------------------------------------
miners = ["Inductive Miner", "Heuristic Miner", "Alpha Miner"]
fitness = [0.967, 0.934, 0.812]
precision = [0.856, 0.912, 0.923]
generalization = [0.901, 0.856, 0.734]
simplicity = [0.789, 0.734, 0.912]

categories = ["Fitness", "Precision", "Generalization", "Simplicity"]
N = len(categories)
angles = [n / float(N) * 2 * np.pi for n in range(N)]
angles += angles[:1]  # close the loop

# MATLAB palette (blue, orange-red, gold)
colors = [MATLAB_COLORS[0], MATLAB_COLORS[1], MATLAB_COLORS[2]]
markers = ["o", "s", "^"]

# ---------------------------------------------------------------------------
# Build the radar chart
# ---------------------------------------------------------------------------
fig = plt.figure(figsize=(9.0, 9.0))
ax = fig.add_subplot(111, polar=True)

# Rotate so Fitness is at the top-right (45°) — this spreads the category
# labels evenly and leaves the lower-left quadrant relatively empty.
ax.set_theta_offset(np.pi / 4)
ax.set_theta_direction(-1)

for i, miner in enumerate(miners):
    values = [fitness[i], precision[i], generalization[i], simplicity[i]]
    values += values[:1]
    ax.plot(
        angles,
        values,
        marker=markers[i],
        markersize=6.5,
        markerfacecolor="white",
        markeredgewidth=1.2,
        linewidth=2.2,
        color=colors[i],
        label=miner,
    )
    ax.fill(angles, values, alpha=0.10, color=colors[i])

# Category labels (the four axes)
ax.set_xticks(angles[:-1])
ax.set_xticklabels(categories, fontsize=13, fontweight="bold")

# Radial limits and ticks
ax.set_ylim(0.55, 1.02)
radii = [0.60, 0.70, 0.80, 0.90, 1.00]

# Place radial labels at 22.5° (halfway between the first two axes) in the
# empty space so they never overlap the plotted polygons.
label_angle = np.degrees(angles[0] + np.pi / 8)
ax.set_rgrids(radii, labels=[f"{r:.2f}" for r in radii], angle=label_angle, fontsize=11)

# Grid styling
ax.grid(True, linestyle=":", alpha=0.35, linewidth=0.8)
ax.spines["polar"].set_linewidth(1.2)
ax.spines["polar"].set_color("#404040")

# Legend — place it in the lower-left (empty) quadrant using figure coords
# so it never sits on top of the data.
legend = ax.legend(
    loc="lower left",
    bbox_to_anchor=(-0.15, -0.15),
    frameon=True,
    fancybox=False,
    edgecolor="black",
    fontsize=11,
)
legend.get_frame().set_linewidth(1.0)

fig.tight_layout()
pub_savefig(fig, OUTPUT_DIR / "Fig6_Miner_Comparison.png")
plt.close(fig)
print(f"  wrote {OUTPUT_DIR / 'Fig6_Miner_Comparison.png'}")


if __name__ == "__main__":
    print("Regenerating miner-comparison radar chart at", PUB_DPI, "DPI...")
    # script already runs on import
    print("Done.")
