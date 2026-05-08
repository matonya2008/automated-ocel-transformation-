"""
Generate cross-sector sample datasets for the scalability evaluation.

These are synthetic stand-ins for the industrial tube-manufacturing logs
referenced in the manuscript. They share the same column schema as the
real evaluation data so that ``cross_sector_evaluation.py`` can run end-to-end
without requiring proprietary files.
"""

from pathlib import Path
import pandas as pd
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data" / "sample"

RNG = np.random.default_rng(42)


def _make_tube_logs(n_events: int = 5_000) -> pd.DataFrame:
    """Synthetic tube-manufacturing event log."""
    activities = [
        "CutTube", "WeldJoint", "InspectVision", "CoatSurface",
        "PackBox", "ShipOrder", "ReworkWeld", "HoldQA"
    ]
    case_ids = [f"TC_{i:05d}" for i in range(1, 501)]
    obj_types = ["Tube", "Batch", "Pallet"]
    attrs = [f"Diam:{RNG.integers(10, 50)}mm",
             f"Len:{RNG.integers(100, 500)}cm",
             f"Batch:{RNG.integers(1000, 9999)}"]

    rows = []
    for _ in range(n_events):
        rows.append({
            "Case ID": RNG.choice(case_ids),
            "Activity": RNG.choice(activities),
            "Timestamp": pd.Timestamp("2024-01-01") + pd.Timedelta(minutes=int(RNG.integers(0, 90*24*60))),
            "Object _type": RNG.choice(obj_types),
            "Attributes": RNG.choice(attrs),
        })
    return pd.DataFrame(rows)


def _make_tube_sensors(n_rows: int = 5_000) -> pd.DataFrame:
    """Synthetic tube-manufacturing sensor readings."""
    base_time = pd.Timestamp("2024-01-01")
    rows = []
    for i in range(n_rows):
        rows.append({
            "ts_hour_tz": base_time + pd.Timedelta(hours=i),
            "time_index": f"E{i+1:06d}",
            "S1_201": round(RNG.normal(22.5, 3.2), 3),
            "S2_201": round(RNG.normal(101.3, 5.1), 3),
            "S3_201": round(RNG.normal(45.0, 7.5), 3),
        })
    return pd.DataFrame(rows)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    logs_path = DATA_DIR / "tube_logs_sample.csv"
    _make_tube_logs().to_csv(logs_path, index=False)
    print(f"Wrote tube logs sample -> {logs_path}")

    sensor_path = DATA_DIR / "tube_sensor_sample.csv"
    _make_tube_sensors().to_csv(sensor_path, index=False)
    print(f"Wrote tube sensor sample -> {sensor_path}")


if __name__ == "__main__":
    main()
