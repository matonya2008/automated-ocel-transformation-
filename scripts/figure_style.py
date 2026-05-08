"""
Shared publication-style helper (MATLAB-inspired).

Applied to every figure embedded in Main.tex so print-ready figures have:

- 600 DPI, tight bounding box, white background
- A muted, MATLAB-like palette (blue, orange-red, gold, purple, green, cyan)
- Clean, minimal axes with arrow tips on both x and y (``add_axis_arrows``)
- Circle markers on every line plot (`lines.marker = 'o'`) so line figures
  read as MATLAB's ``plot(x, y, '-o')`` style by default

Usage::

    from figure_style import apply_pub_style, pub_savefig, add_axis_arrows, \
        finalize_matlab_axes, MATLAB_COLORS

    apply_pub_style()
    fig, ax = plt.subplots()
    ax.plot(x, y)  # already gets circle markers and MATLAB blue
    finalize_matlab_axes(ax, xlabel='Time', ylabel='Accuracy')
    pub_savefig('myplot.png')
"""

from __future__ import annotations

from typing import Iterable, Optional, Sequence

import matplotlib as mpl
import matplotlib.pyplot as plt

PUB_DPI = 600

# ---------------------------------------------------------------------------
# MATLAB default colour order (R2014b+).
# Kept short (six colours) so plots read as "less coloured, cleaner".
# ---------------------------------------------------------------------------
MATLAB_COLORS: list[str] = [
    "#0072BD",  # MATLAB blue      (default line 1)
    "#D95319",  # MATLAB orange    (default line 2)
    "#EDB120",  # MATLAB gold      (default line 3)
    "#7E2F8E",  # MATLAB purple    (default line 4)
    "#77AC30",  # MATLAB green     (default line 5)
    "#4DBEEE",  # MATLAB cyan      (default line 6)
    "#A2142F",  # MATLAB maroon    (default line 7)
]

# ---------------------------------------------------------------------------
# rcParams
# ---------------------------------------------------------------------------
_PUB_RCPARAMS = {
    "figure.dpi": 150,
    "savefig.dpi": PUB_DPI,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.08,
    "savefig.facecolor": "white",
    "figure.facecolor": "white",
    "axes.facecolor": "white",

    "font.family": "serif",
    "font.size": 13,
    "axes.titlesize": 15,
    "axes.titleweight": "bold",
    "axes.labelsize": 14,
    "axes.labelweight": "normal",
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
    "legend.fontsize": 12,
    "legend.title_fontsize": 12.5,
    "legend.loc": "upper right",
    "legend.frameon": True,
    "legend.fancybox": False,
    "legend.edgecolor": "black",
    "legend.borderpad": 0.5,
    "legend.framealpha": 0.95,

    "axes.linewidth": 1.4,
    "axes.edgecolor": "black",
    "axes.spines.top": False,
    "axes.spines.right": False,

    # Circle markers on every line by default (MATLAB '-o' style)
    "lines.linewidth": 2.0,
    "lines.marker": "o",
    "lines.markersize": 5.5,
    "lines.markeredgewidth": 1.1,
    "lines.markerfacecolor": "white",

    "patch.linewidth": 0.9,

    "grid.alpha": 0.25,
    "grid.linestyle": ":",
    "grid.linewidth": 0.6,
    "grid.color": "#9E9E9E",

    # Tick marks — MATLAB style: tick lines pointing into the plot
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.major.size": 5.0,
    "ytick.major.size": 5.0,
    "xtick.major.width": 1.2,
    "ytick.major.width": 1.2,
    "xtick.minor.visible": False,
    "ytick.minor.visible": False,

    # Discrete plot colour cycle (MATLAB default)
    "axes.prop_cycle": mpl.cycler(color=MATLAB_COLORS),
}


def apply_pub_style(reset_first: bool = True) -> None:
    """Apply the shared publication style to the current matplotlib session."""
    if reset_first:
        mpl.rcdefaults()
    plt.rcParams.update(_PUB_RCPARAMS)


def _axes_supports_arrows(ax) -> bool:
    """Return True if this axes looks like a standard Cartesian plot where
    adding x/y arrow tips makes sense. Skip polar, 3D, log-log, and images/
    heatmaps (which typically render via ``imshow`` or have no spines)."""
    try:
        if ax.name in {"polar", "3d"}:
            return False
    except Exception:
        return False
    # Heatmaps (imshow) set spines invisible or fill the frame; skip them.
    if any(isinstance(ch, mpl.image.AxesImage) for ch in ax.get_children()):
        return False
    # Axes with both spines removed (invisible frame) are not meaningful.
    if (
        not ax.spines["left"].get_visible()
        and not ax.spines["bottom"].get_visible()
    ):
        return False
    # Legend-only axes / colourbars have no data.
    if not ax.has_data():
        return False
    return True


def auto_arrow_all_axes(fig) -> None:
    """Walk every axes in ``fig`` and add MATLAB-style arrow tips where
    appropriate. Idempotent: safe to call once before saving."""
    for ax in fig.get_axes():
        if _axes_supports_arrows(ax):
            try:
                add_axis_arrows(ax)
            except Exception:
                pass


def pub_savefig(
    fig_or_path,
    path: Optional[str] = None,
    *,
    arrows: bool = False,
    **kwargs,
) -> None:
    """Save a figure at 600 DPI with consistent padding.

    Accepts either ``pub_savefig("name.png")`` (uses current figure) or
    ``pub_savefig(fig, "name.png")``.

    When ``arrows=True`` (default), MATLAB-style arrow tips are added to
    every Cartesian axes in the figure immediately before saving."""
    if path is None:
        path = fig_or_path
        target = plt.gcf()
    else:
        target = fig_or_path
    if arrows:
        auto_arrow_all_axes(target)
    kwargs.setdefault("dpi", PUB_DPI)
    kwargs.setdefault("bbox_inches", "tight")
    kwargs.setdefault("pad_inches", 0.08)
    kwargs.setdefault("facecolor", "white")
    target.savefig(path, **kwargs)


def add_axis_arrows(
    ax,
    arrow_length: float = 0.02,
    color: str = "black",
    linewidth: float = 1.4,
) -> None:
    """Draw MATLAB-style arrow heads at the right end of the x-axis and at
    the top end of the y-axis of ``ax``.

    The arrows are rendered as tiny annotations in axes-fraction coordinates
    so they stay aligned with the spines even after ``tight_layout``. Call
    this AFTER all data is plotted and axis limits/labels are set."""
    # X-axis arrow (tip at right end of bottom spine)
    ax.annotate(
        "",
        xy=(1.0 + arrow_length, 0.0),
        xytext=(1.0, 0.0),
        xycoords=("axes fraction", "axes fraction"),
        arrowprops=dict(
            arrowstyle="-|>",
            color=color,
            lw=linewidth,
            mutation_scale=16,
            shrinkA=0,
            shrinkB=0,
        ),
        annotation_clip=False,
    )
    # Y-axis arrow (tip at top of left spine)
    ax.annotate(
        "",
        xy=(0.0, 1.0 + arrow_length),
        xytext=(0.0, 1.0),
        xycoords=("axes fraction", "axes fraction"),
        arrowprops=dict(
            arrowstyle="-|>",
            color=color,
            lw=linewidth,
            mutation_scale=16,
            shrinkA=0,
            shrinkB=0,
        ),
        annotation_clip=False,
    )


def finalize_matlab_axes(
    ax,
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
    title: Optional[str] = None,
    arrows: bool = False,
    grid: bool = True,
    legend: bool = False,
) -> None:
    """One-call helper to finish a MATLAB-style axis.

    - Optionally applies labels and title.
    - Turns on a subtle dotted grid.
    - Draws arrow tips on both spines (``add_axis_arrows``).
    - Keeps the left and bottom spines visible (top/right hidden from
      ``apply_pub_style``).
    """
    if xlabel is not None:
        ax.set_xlabel(xlabel)
    if ylabel is not None:
        ax.set_ylabel(ylabel)
    if title is not None:
        ax.set_title(title)
    if grid:
        ax.grid(True, which="major", axis="both")
    ax.spines["left"].set_color("black")
    ax.spines["bottom"].set_color("black")
    if arrows:
        add_axis_arrows(ax)
    if legend:
        leg = ax.legend(loc="upper right", frameon=True,
                        fancybox=False, edgecolor="black")
        leg.get_frame().set_linewidth(0.9)


def matlab_cycle(colors: Optional[Sequence[str]] = None) -> Iterable[str]:
    """Yield a MATLAB colour cycle indefinitely."""
    palette = list(colors or MATLAB_COLORS)
    i = 0
    while True:
        yield palette[i % len(palette)]
        i += 1
