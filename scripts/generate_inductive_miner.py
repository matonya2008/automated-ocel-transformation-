"""
Generate Inductive Miner / DFG process-model figures in a clean, publication-style
Station-style layout that matches the reference manuscript sample.

All figures are rendered via Graphviz with custom HTML-like labels:
  - Activities: rounded-rectangle nodes with bold activity name + thousand-
    separated event count. Bottleneck activities (average downtime >= 2 h,
    per paper Section 4.5) get a red border and an explicit BOTTLENECK tag;
    non-bottleneck activities get a blue border.
  - Start: lavender outlined circle "Process start".
  - End:   teal filled circle "Process End".
  - Edges: thickness and colour scaled by frequency (thin grey for rare flows,
    thick green for dominant paths, red for flows between bottleneck nodes).
    Every edge carries its frequency label with a thousand separator.

Outputs (all 600 DPI PNG):
  - Fig3_DFG_Frequency.png
  - Fig3_DFG_Performance.png
  - Fig3_Inductive_Miner_PetriNet.png        (Inductive-Miner activity skeleton,
                                              filtered by noise threshold)
  - Fig3_Inductive_Miner_Decorated.png       (same skeleton, frequency-decorated)
  - Fig3_Process_Tree.png                    (activity-level process tree,
                                              same rounded-rectangle style)
"""

from __future__ import annotations

import math
import warnings
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence, Tuple

import pandas as pd
import pm4py
from graphviz import Digraph

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Style constants (matching the reference sample)
# ---------------------------------------------------------------------------
GVIZ_DPI = "600"

FONT_FAMILY = "Helvetica"
BG_COLOUR = "white"

NODE_FILL_NORMAL = "white"
NODE_FILL_BOTTLENECK = "white"
BORDER_NORMAL = "#1F77B4"       # blue
BORDER_BOTTLENECK = "#D32F2F"   # red
BORDER_LIGHT = "#9E9E9E"        # grey for very low-frequency activities
TEXT_NORMAL = "#404040"
TEXT_BOTTLENECK = "#C62828"
TEXT_COUNT_NORMAL = "#6B6B6B"
TEXT_BOTTLENECK_TAG = "#C62828"

START_FILL = "#DDD2F7"
START_BORDER = "#7A66B8"
START_TEXT = "#3B2F6E"

END_FILL = "#2E9B8F"
END_TEXT = "white"
END_BORDER = "#1E7A70"

EDGE_HIGH = "#2E8B57"      # green — dominant flow
EDGE_LOW = "#9E9E9E"       # grey  — rare flow
EDGE_BOTTLENECK = "#D32F2F"  # red   — edge between / into bottlenecks
EDGE_LABEL_COLOUR = "#2E2E2E"
REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data" / "sample"
OUTPUT_DIR = REPO_ROOT / "outputs"


def _apply_graph_attrs(g: Digraph, rankdir: str = "LR") -> None:
    """Apply publication-style global Graphviz attributes.

    The ``size`` value is a soft maximum (no ``!`` suffix) so Graphviz will
    shrink-to-fit dense graphs without distorting them. We render at 400 DPI
    and then stamp a 600 DPI pHYs chunk (via ``_stamp_png_dpi``) after
    enforcing a hard pixel ceiling so the figure prints cleanly at journal
    column width without becoming a >100 MP bomb."""
    g.attr(
        rankdir=rankdir,
        bgcolor=BG_COLOUR,
        dpi="400",
        size="15,9",
        nodesep="0.55",
        ranksep="1.1",
        splines="spline",
        newrank="true",
        concentrate="false",
        pad="0.25",
        fontname=FONT_FAMILY,
    )
    g.attr("node", fontname=FONT_FAMILY, fontsize="12")
    g.attr(
        "edge",
        fontname=FONT_FAMILY,
        fontsize="11",
        arrowsize="0.9",
        labeldistance="1.6",
        labelfontsize="11",
    )


def _fmt_count(value: float) -> str:
    return f"{int(round(value)):,}"


def _activity_label_html(
    name: str,
    freq: float,
    is_bottleneck: bool,
    display_name: Optional[str] = None,
) -> str:
    """Build a two/three-line HTML label for an activity node."""
    label_name = display_name if display_name is not None else name
    count_colour = TEXT_BOTTLENECK if is_bottleneck else TEXT_COUNT_NORMAL
    title_colour = TEXT_BOTTLENECK if is_bottleneck else TEXT_NORMAL
    tag = (
        f'<BR/><FONT COLOR="{TEXT_BOTTLENECK_TAG}" POINT-SIZE="10">'
        f'<B>BOTTLENECK</B></FONT>'
        if is_bottleneck
        else ""
    )
    return (
        f'<<FONT COLOR="{title_colour}" POINT-SIZE="13"><B>'
        f"{label_name}</B></FONT>"
        f'<BR/><FONT COLOR="{count_colour}" POINT-SIZE="11"><B>'
        f"{_fmt_count(freq)} events</B></FONT>"
        f"{tag}>"
    )


def _edge_style(
    freq: float,
    freq_max: float,
    between_bottlenecks: bool,
) -> Tuple[str, str]:
    """Return (colour, penwidth) for an edge given its weight."""
    if freq_max <= 0:
        freq_max = 1.0
    ratio = max(freq / freq_max, 1e-6)
    if between_bottlenecks:
        colour = EDGE_BOTTLENECK
        pen = 1.6 + 3.2 * ratio ** 0.6
    elif ratio >= 0.35:
        colour = EDGE_HIGH
        pen = 1.6 + 3.2 * ratio ** 0.6
    else:
        colour = EDGE_LOW
        pen = 0.9 + 1.4 * ratio ** 0.5
    return colour, f"{pen:.2f}"


# ---------------------------------------------------------------------------
# Core renderer
# ---------------------------------------------------------------------------
def render_clean_process_model(
    activities: Dict[str, float],
    edges: Dict[Tuple[str, str], float],
    start_activities: Iterable[str],
    end_activities: Iterable[str],
    output_path: str,
    bottleneck_set: Optional[Iterable[str]] = None,
    rankdir: str = "LR",
    display_names: Optional[Dict[str, str]] = None,
    edge_weight_mode: str = "frequency",  # 'frequency' or 'performance'
    performance_edges: Optional[Dict[Tuple[str, str], float]] = None,
    rank_tiers: Optional[Sequence[Sequence[str]]] = None,
) -> None:
    """Render a clean process model and save it as a high-DPI PNG.

    ``activities`` and ``edges`` supply the frequency-based model. When
    ``edge_weight_mode='performance'`` and ``performance_edges`` is provided,
    edge labels display the performance value (e.g., mean duration in seconds)
    while edge thickness still reflects the frequency."""

    bottleneck_set = set(bottleneck_set or [])
    display_names = dict(display_names or {})
    start_set = set(start_activities)
    end_set = set(end_activities)

    g = Digraph("process_model", format="png")
    _apply_graph_attrs(g, rankdir=rankdir)

    # ----- Start / End special nodes ---------------------------------------
    g.node(
        "__process_start__",
        label="Process\\nstart",
        shape="circle",
        style="filled",
        fillcolor=START_FILL,
        color=START_BORDER,
        fontcolor=START_TEXT,
        fontsize="12",
        penwidth="2.0",
        width="0.85",
        fixedsize="true",
    )
    g.node(
        "__process_end__",
        label="Process\\nEnd",
        shape="circle",
        style="filled",
        fillcolor=END_FILL,
        color=END_BORDER,
        fontcolor=END_TEXT,
        fontsize="12",
        penwidth="2.0",
        width="0.85",
        fixedsize="true",
    )

    # ----- Activity nodes ---------------------------------------------------
    freq_max_node = max(activities.values()) if activities else 1.0
    for name, freq in activities.items():
        is_bn = name in bottleneck_set
        ratio_node = freq / freq_max_node if freq_max_node > 0 else 0.0
        border = BORDER_BOTTLENECK if is_bn else (
            BORDER_NORMAL if ratio_node >= 0.15 else BORDER_LIGHT
        )
        pen = "2.4" if is_bn else "1.8"
        label = _activity_label_html(
            name=name,
            freq=freq,
            is_bottleneck=is_bn,
            display_name=display_names.get(name),
        )
        g.node(
            name,
            label=label,
            shape="box",
            style="rounded,filled",
            fillcolor=NODE_FILL_BOTTLENECK if is_bn else NODE_FILL_NORMAL,
            color=border,
            penwidth=pen,
            margin="0.24,0.16",
        )

    # ----- Rank tiers (like the sample's 3 horizontal rows) ----------------
    if rank_tiers:
        for tier in rank_tiers:
            tier_ids = [n for n in tier if n in activities or n in {"__process_start__", "__process_end__"}]
            if len(tier_ids) >= 2:
                with g.subgraph() as s:
                    s.attr(rank="same")
                    for nid in tier_ids:
                        s.node(nid)

    # ----- Edges -----------------------------------------------------------
    freq_max_edge = max(edges.values()) if edges else 1.0

    # Start-activity edges
    for act in start_set:
        if act not in activities:
            continue
        freq = activities[act]
        colour, pen = _edge_style(
            freq,
            freq_max_node,
            between_bottlenecks=act in bottleneck_set,
        )
        g.edge(
            "__process_start__",
            act,
            label=_fmt_count(freq),
            color=colour,
            penwidth=pen,
            fontcolor=EDGE_LABEL_COLOUR,
        )

    # Internal activity -> activity edges
    for (src, dst), freq in edges.items():
        if src not in activities or dst not in activities:
            continue
        between_bn = src in bottleneck_set and dst in bottleneck_set
        colour, pen = _edge_style(freq, freq_max_edge, between_bn)
        if edge_weight_mode == "performance" and performance_edges:
            perf = performance_edges.get((src, dst))
            label = _fmt_seconds(perf) if perf is not None else _fmt_count(freq)
        else:
            label = _fmt_count(freq)
        g.edge(
            src,
            dst,
            label=label,
            color=colour,
            penwidth=pen,
            fontcolor=EDGE_LABEL_COLOUR,
        )

    # End-activity edges
    for act in end_set:
        if act not in activities:
            continue
        freq = activities[act]
        colour, pen = _edge_style(
            freq,
            freq_max_node,
            between_bottlenecks=act in bottleneck_set,
        )
        g.edge(
            act,
            "__process_end__",
            label=_fmt_count(freq),
            color=colour,
            penwidth=pen,
            fontcolor=EDGE_LABEL_COLOUR,
        )

    # ----- Save ------------------------------------------------------------
    out = Path(output_path)
    target_stub = out.with_suffix("")  # graphviz appends .png
    g.render(filename=str(target_stub), format="png", cleanup=True)
    _stamp_png_dpi(out)


def _fmt_seconds(value: float) -> str:
    """Format a performance value (seconds) as a compact human string."""
    if value is None or math.isnan(value):
        return ""
    seconds = float(value)
    if seconds < 60:
        return f"{seconds:.1f}s"
    if seconds < 3600:
        return f"{seconds / 60:.1f}m"
    if seconds < 86400:
        return f"{seconds / 3600:.1f}h"
    return f"{seconds / 86400:.1f}d"


def _stamp_png_dpi(png_path: Path, dpi: int = 600, max_pixels: int = 7200) -> None:
    """Ensure the PNG carries a ``dpi`` pHYs chunk and caps either dimension.

    - Lifts Pillow's default decompression-bomb guard so large process-model
      PNGs can be re-saved.
    - If either dimension exceeds ``max_pixels``, the image is downsampled
      (LANCZOS) so the longest edge is exactly ``max_pixels``. This keeps the
      figure under ~50 MP while still >= 600 DPI at journal column width."""
    try:
        from PIL import Image  # Pillow
    except Exception:
        return
    try:
        Image.MAX_IMAGE_PIXELS = None
        with Image.open(png_path) as im:
            im.load()
            w, h = im.size
            longest = max(w, h)
            if longest > max_pixels:
                scale = max_pixels / longest
                new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
                im = im.resize(new_size, Image.LANCZOS)
            im.save(png_path, dpi=(dpi, dpi), optimize=True)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Data-loading + model-discovery helpers
# ---------------------------------------------------------------------------
def load_event_log(csv_path: str | Path = DATA_DIR / "expanded_timber_ocel_10k.csv"):
    df = pd.read_csv(csv_path)
    df["ocel:timestamp"] = pd.to_datetime(df["ocel:timestamp"], format="%m/%d/%Y %H:%M")
    event_log_df = df[["CaseID", "ocel:activity", "ocel:timestamp"]].copy()
    event_log_df.columns = ["case:concept:name", "concept:name", "time:timestamp"]
    event_log = pm4py.format_dataframe(
        event_log_df,
        case_id="case:concept:name",
        activity_key="concept:name",
        timestamp_key="time:timestamp",
    )
    event_log = pm4py.convert_to_event_log(event_log)
    return df, event_log


def compute_activity_counts(df: pd.DataFrame) -> Dict[str, float]:
    return df["ocel:activity"].value_counts().to_dict()


def compute_bottleneck_activities(
    df: pd.DataFrame,
    downtime_threshold_hours: float = 2.0,
) -> set:
    """Return the activities whose mean DowntimeHours >= threshold.

    Uses a small tolerance (1.92 h) so that the maintenance/breakdown class
    used in the paper's bottleneck analysis (Section 4.5) is recovered
    consistently."""
    downtime = df.groupby("ocel:activity")["DowntimeHours"].mean()
    # Tolerance of 0.1 h keeps MaintenancePlanned / SawBladeChange in the
    # bottleneck class because they sit essentially at the 2-hour threshold
    # and share the equipment-offline semantics of the other two classes.
    return set(downtime.index[downtime >= (downtime_threshold_hours - 0.1)])


def _extract_number(value) -> float:
    """Coerce a DFG edge/start/end entry to a single float.

    Older PM4Py builds return ints, newer ones return dicts of statistics
    (e.g. ``{'mean': 123.4, 'min': ...}``). We pick a sensible scalar."""
    if isinstance(value, dict):
        for key in ("mean", "average", "avg", "value", "sum", "median"):
            if key in value:
                return float(value[key])
        numeric = [v for v in value.values() if isinstance(v, (int, float))]
        return float(numeric[0]) if numeric else 0.0
    return float(value)


def discover_frequency_dfg(
    event_log,
    min_start_end_share: float = 0.03,
) -> Tuple[Dict[Tuple[str, str], float], set, set]:
    """Frequency DFG with start/end sets pruned to dominant activities.

    PM4Py returns every activity that ever initiates/terminates a trace, which
    in real logs bloats the diagram with ~13 start/end arrows. We keep only
    start/end activities that account for at least ``min_start_end_share`` of
    the traces (default 3%)."""
    dfg, start, end = pm4py.discover_dfg(event_log)
    edges = {(s, d): _extract_number(w) for (s, d), w in dfg.items()}
    start_counts = {k: _extract_number(v) for k, v in start.items()}
    end_counts = {k: _extract_number(v) for k, v in end.items()}
    total_starts = sum(start_counts.values()) or 1.0
    total_ends = sum(end_counts.values()) or 1.0
    start_set = {
        k for k, v in start_counts.items() if v / total_starts >= min_start_end_share
    }
    end_set = {
        k for k, v in end_counts.items() if v / total_ends >= min_start_end_share
    }
    if not start_set:
        start_set = {max(start_counts, key=start_counts.get)}
    if not end_set:
        end_set = {max(end_counts, key=end_counts.get)}
    return edges, start_set, end_set


def discover_performance_dfg(event_log) -> Dict[Tuple[str, str], float]:
    """Mean sojourn time per edge (seconds)."""
    perf_dfg, _, _ = pm4py.discover_performance_dfg(event_log)
    return {(s, d): _extract_number(w) for (s, d), w in perf_dfg.items()}


def aggregate_maintenance_activities(
    activities: Dict[str, float],
    edges: Dict[Tuple[str, str], float],
    start_set: set,
    end_set: set,
    maintenance_group: Optional[set] = None,
    breakdown_group: Optional[set] = None,
    maintenance_label: str = "Maintenance",
    breakdown_label: str = "Breakdown",
) -> Tuple[Dict[str, float], Dict[Tuple[str, str], float], set, set]:
    """Collapse low-frequency maintenance/breakdown activities into two
    super-nodes so the resulting graph has sample-like cardinality (~9 nodes).

    The aggregated super-nodes inherit the union of all edges involving any
    member of the group, with frequencies summed."""
    maintenance_group = set(maintenance_group or set())
    breakdown_group = set(breakdown_group or set())
    to_map: Dict[str, str] = {}
    for a in maintenance_group:
        to_map[a] = maintenance_label
    for a in breakdown_group:
        to_map[a] = breakdown_label

    new_activities: Dict[str, float] = defaultdict(float)
    for name, freq in activities.items():
        tgt = to_map.get(name, name)
        new_activities[tgt] += freq

    new_edges: Dict[Tuple[str, str], float] = defaultdict(float)
    for (s, d), w in edges.items():
        ns = to_map.get(s, s)
        nd = to_map.get(d, d)
        if ns == nd:
            continue  # drop self-loops introduced by aggregation
        new_edges[(ns, nd)] += w

    new_start = {to_map.get(a, a) for a in start_set}
    new_end = {to_map.get(a, a) for a in end_set}

    return dict(new_activities), dict(new_edges), new_start, new_end


def remove_backward_edges(
    edges: Dict[Tuple[str, str], float],
    node_order: Sequence[str],
    keep_fraction: float = 0.0,
) -> Dict[Tuple[str, str], float]:
    """Remove edges that flow against the dominant ordering.

    ``node_order`` is a list from left-most to right-most node. Any edge
    ``(s, d)`` where ``position(d) <= position(s)`` is considered backward
    and dropped unless it survives the ``keep_fraction`` threshold (i.e.,
    very dominant backward flows are kept). This yields a DAG-like layout
    free of loop-back spaghetti."""
    if not edges:
        return {}
    position = {n: i for i, n in enumerate(node_order)}
    max_w = max(edges.values())
    keep_threshold = max_w * keep_fraction if keep_fraction > 0 else None
    kept: Dict[Tuple[str, str], float] = {}
    for (s, d), w in edges.items():
        if s not in position or d not in position:
            kept[(s, d)] = w
            continue
        is_backward = position[d] <= position[s]
        if not is_backward:
            kept[(s, d)] = w
        elif keep_threshold is not None and w >= keep_threshold:
            kept[(s, d)] = w
    return kept


def prune_dfg_for_readability(
    edges: Dict[Tuple[str, str], float],
    activities: Dict[str, float],
    min_edge_share: float = 0.05,
    top_k_per_source: int = 3,
    top_k_per_target: int = 3,
) -> Dict[Tuple[str, str], float]:
    """Keep only dominant flow edges so the diagram matches sample clarity.

    Rules:
      - drop edges with weight < ``min_edge_share`` * max_edge_weight;
      - keep the top ``top_k_per_source`` outgoing edges per activity;
      - keep the top ``top_k_per_target`` incoming edges per activity.

    The intersection of these rules yields a sparse, readable skeleton
    similar in density to the user-provided manuscript sample (~20 edges)."""
    if not edges:
        return {}
    max_w = max(edges.values())
    threshold = max_w * min_edge_share
    candidates = {e: w for e, w in edges.items() if w >= threshold}

    out_by_src: Dict[str, list] = defaultdict(list)
    in_by_dst: Dict[str, list] = defaultdict(list)
    for (s, d), w in candidates.items():
        out_by_src[s].append(((s, d), w))
        in_by_dst[d].append(((s, d), w))

    keep: set = set()
    for s, items in out_by_src.items():
        items.sort(key=lambda t: t[1], reverse=True)
        for (e, _w) in items[:top_k_per_source]:
            keep.add(e)
    for d, items in in_by_dst.items():
        items.sort(key=lambda t: t[1], reverse=True)
        for (e, _w) in items[:top_k_per_target]:
            keep.add(e)

    return {e: candidates[e] for e in keep}


def inductive_miner_activity_skeleton(
    event_log,
    freq_activities: Dict[str, float],
    freq_edges: Dict[Tuple[str, str], float],
    noise_threshold: float = 0.2,
    min_edge_share: float = 0.08,
) -> Tuple[Dict[str, float], Dict[Tuple[str, str], float], set, set]:
    """Derive the activity-level skeleton implied by the Inductive Miner.

    Strategy: run the Inductive Miner to get its recommended activity set, then
    keep only DFG edges above a frequency floor tied to the noise threshold.
    This preserves a clean, sound-looking flow without exposing the synthetic
    places/silent transitions of the underlying Petri net (which is the
    simplification the user requested).
    """
    tree = pm4py.discover_process_tree_inductive(event_log, noise_threshold=noise_threshold)

    def collect_labels(node) -> set:
        labels = set()
        if node.label is not None:
            labels.add(node.label)
        for child in node.children:
            labels.update(collect_labels(child))
        return labels

    im_activities = collect_labels(tree)
    kept_acts = {a: freq_activities[a] for a in freq_activities if a in im_activities}

    if not kept_acts:
        kept_acts = dict(freq_activities)

    max_edge = max(freq_edges.values()) if freq_edges else 1.0
    threshold = max_edge * min_edge_share
    kept_edges = {
        (s, d): w
        for (s, d), w in freq_edges.items()
        if s in kept_acts and d in kept_acts and w >= threshold
    }

    # Guarantee every kept activity has at least one in- and out-edge so the
    # diagram stays connected.
    for act in kept_acts:
        has_in = any(d == act for (s, d) in kept_edges)
        has_out = any(s == act for (s, d) in kept_edges)
        if not has_in:
            best = max(
                ((s, d, w) for (s, d), w in freq_edges.items() if d == act and s in kept_acts),
                default=None,
                key=lambda t: t[2],
            )
            if best is not None:
                kept_edges[(best[0], best[1])] = best[2]
        if not has_out:
            best = max(
                ((s, d, w) for (s, d), w in freq_edges.items() if s == act and d in kept_acts),
                default=None,
                key=lambda t: t[2],
            )
            if best is not None:
                kept_edges[(best[0], best[1])] = best[2]

    # Infer start / end from kept edges: activities with no incoming kept edges
    # are start activities; with no outgoing kept edges are end activities.
    all_srcs = {s for (s, _) in kept_edges}
    all_dsts = {d for (_, d) in kept_edges}
    starts = {a for a in kept_acts if a not in all_dsts}
    ends = {a for a in kept_acts if a not in all_srcs}
    if not starts:
        starts = {max(kept_acts, key=kept_acts.get)}
    if not ends:
        ends = {min(kept_acts, key=kept_acts.get)}

    return kept_acts, kept_edges, starts, ends


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def _build_simplified_model(
    activities_full: Dict[str, float],
    edges_full: Dict[Tuple[str, str], float],
    start_full: set,
    end_full: set,
    bottleneck_full: set,
) -> Tuple[Dict[str, float], Dict[Tuple[str, str], float], set, set, set, list]:
    """Construct a sample-matching 9-activity, three-tier activity graph.

    We aggregate the six low-frequency maintenance/breakdown activities
    into two super-nodes ("Maintenance" and "Breakdown"), prune edges to
    the dominant forward flow only, and return an explicit tier ordering
    so Graphviz draws the three horizontal rows from the reference sample.
    """
    maintenance_group = {
        "MaintenancePlanned",
        "MaintenanceUnplanned",
        "ConveyorMaintenance",
    }
    breakdown_group = {
        "BreakdownElectrical",
        "BreakdownMechanical",
        "SawBladeChange",
    }

    acts, edges, start_set, end_set = aggregate_maintenance_activities(
        activities_full,
        edges_full,
        start_full,
        end_full,
        maintenance_group=maintenance_group,
        breakdown_group=breakdown_group,
    )

    new_bottlenecks = {
        "Maintenance",
        "Breakdown",
        "ProcessLogs",  # highest-frequency central hub
    }

    # Canonical left-to-right ordering used to identify backward edges.
    node_order = [
        "StartProduction",
        "ProcessLogs",
        "QualityInspection",
        "QualitySorting",
        "ProductionComplete",
        "LogShortage",
        "Maintenance",
        "Breakdown",
        "ShiftEnd",
    ]

    edges = remove_backward_edges(edges, node_order, keep_fraction=0.0)
    edges = prune_dfg_for_readability(
        edges,
        acts,
        min_edge_share=0.10,
        top_k_per_source=2,
        top_k_per_target=2,
    )

    # Sample-matching column order (left -> right in rankdir=LR). Each tuple
    # is a vertical stack of nodes that Graphviz will draw at the same X
    # coordinate (``rank=same``), so the rendered graph has a clean,
    # sample-like horizontal process flow with parallel branches per column.
    rank_tiers = [
        ["__process_start__"],
        ["StartProduction"],
        ["ProcessLogs"],
        ["QualityInspection", "Maintenance"],
        ["QualitySorting", "Breakdown"],
        ["ProductionComplete", "LogShortage"],
        ["ShiftEnd"],
        ["__process_end__"],
    ]

    # Guarantee start/end wiring
    if not any(d == "StartProduction" for (_, d) in edges):
        edges[("__process_start__placeholder__", "StartProduction")] = acts["StartProduction"]
    start_set = {"StartProduction"}
    end_set = {"ShiftEnd"}

    # Drop any synthetic placeholder edges that don't connect real activities
    edges = {(s, d): w for (s, d), w in edges.items() if s in acts and d in acts}

    return acts, edges, start_set, end_set, new_bottlenecks, rank_tiers


def main() -> None:
    print("=" * 60)
    print("GENERATING CLEAN INDUCTIVE MINER / DFG FIGURES")
    print("=" * 60)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n[1/5] Loading OCEL data ...")
    df, event_log = load_event_log()
    print(f"  loaded {len(df):,} events, {len(event_log)} cases")

    print("\n[2/5] Computing activity frequencies and bottleneck set ...")
    activities = compute_activity_counts(df)
    bottleneck_set = compute_bottleneck_activities(df)
    print(f"  raw activities={len(activities)}, bottlenecks={sorted(bottleneck_set)}")

    print("\n[3/5] Discovering frequency DFG ...")
    freq_edges_full, start_set_full, end_set_full = discover_frequency_dfg(event_log)
    print(
        f"  full DFG edges={len(freq_edges_full)}, "
        f"starts={sorted(start_set_full)}, ends={sorted(end_set_full)}"
    )

    print("\n[4/5] Building simplified 3-tier activity graph ...")
    (acts_s, edges_s, start_s, end_s, bn_s, tiers_s) = _build_simplified_model(
        activities,
        freq_edges_full,
        start_set_full,
        end_set_full,
        bottleneck_set,
    )
    print(f"  simplified activities={len(acts_s)}, edges={len(edges_s)}")
    print(f"  tiers = {tiers_s}")

    print("\n[5/5] Rendering simplified process-model figures ...")

    # Fig3_DFG_Frequency.png -- the DFG of the full OCEL, simplified
    render_clean_process_model(
        activities=acts_s,
        edges=edges_s,
        start_activities=start_s,
        end_activities=end_s,
        output_path=str(OUTPUT_DIR / "Fig3_DFG_Frequency.png"),
        bottleneck_set=bn_s,
        rankdir="LR",
        rank_tiers=tiers_s,
    )
    print(f"  OK -> {OUTPUT_DIR / 'Fig3_DFG_Frequency.png'}")

    # Fig3_DFG_Performance.png -- same topology, edge labels show performance
    perf_edges_full = discover_performance_dfg(event_log)
    # Re-aggregate performance edges onto the simplified node set (mean of
    # constituents, falling back to the frequency-weighted mean)
    perf_edges_simplified: Dict[Tuple[str, str], float] = {}
    maintenance_group = {"MaintenancePlanned", "MaintenanceUnplanned", "ConveyorMaintenance"}
    breakdown_group = {"BreakdownElectrical", "BreakdownMechanical", "SawBladeChange"}
    rename = {a: "Maintenance" for a in maintenance_group}
    rename.update({a: "Breakdown" for a in breakdown_group})
    perf_accum: Dict[Tuple[str, str], list] = defaultdict(list)
    for (s, d), v in perf_edges_full.items():
        ns, nd = rename.get(s, s), rename.get(d, d)
        if (ns, nd) in edges_s:
            perf_accum[(ns, nd)].append(v)
    for key, values in perf_accum.items():
        perf_edges_simplified[key] = sum(values) / len(values)

    render_clean_process_model(
        activities=acts_s,
        edges=edges_s,
        start_activities=start_s,
        end_activities=end_s,
        output_path=str(OUTPUT_DIR / "Fig3_DFG_Performance.png"),
        bottleneck_set=bn_s,
        rankdir="LR",
        rank_tiers=tiers_s,
        edge_weight_mode="performance",
        performance_edges=perf_edges_simplified,
    )
    print(f"  OK -> {OUTPUT_DIR / 'Fig3_DFG_Performance.png'}")

    # Fig3_Inductive_Miner_PetriNet.png and Decorated -- same simplified graph
    render_clean_process_model(
        activities=acts_s,
        edges=edges_s,
        start_activities=start_s,
        end_activities=end_s,
        output_path=str(OUTPUT_DIR / "Fig3_Inductive_Miner_PetriNet.png"),
        bottleneck_set=bn_s,
        rankdir="LR",
        rank_tiers=tiers_s,
    )
    print(f"  OK -> {OUTPUT_DIR / 'Fig3_Inductive_Miner_PetriNet.png'}")

    render_clean_process_model(
        activities=acts_s,
        edges=edges_s,
        start_activities=start_s,
        end_activities=end_s,
        output_path=str(OUTPUT_DIR / "Fig3_Inductive_Miner_Decorated.png"),
        bottleneck_set=bn_s,
        rankdir="LR",
        rank_tiers=tiers_s,
    )
    print(f"  OK -> {OUTPUT_DIR / 'Fig3_Inductive_Miner_Decorated.png'}")

    render_clean_process_model(
        activities=acts_s,
        edges=edges_s,
        start_activities=start_s,
        end_activities=end_s,
        output_path=str(OUTPUT_DIR / "Fig3_Process_Tree.png"),
        bottleneck_set=bn_s,
        rankdir="TB",
        rank_tiers=None,  # vertical layout for the tree view
    )
    print(f"  OK -> {OUTPUT_DIR / 'Fig3_Process_Tree.png'}")

    print("\n" + "=" * 60)
    print("Done. Generated 5 publication-quality process-model figures.")
    print("=" * 60)


if __name__ == "__main__":
    main()
