# Automated OCEL Transformation — Code Availability

This repository contains the Python implementation of the three-stage pipeline described in:

**"Automated OCEL Transformation for Real-Time Conformance in Complex Manufacturing"**

The code is released for verification and academic reproduction purposes. All synthetic data, aggregate results and generated figures are produced at runtime by the scripts below.

---

## System Prerequisites

1. **Python** ≥ 3.10
2. **Graphviz** binaries (C engine) must be installed on your system:
   - **Windows**: https://graphviz.org/download/ (add `bin\` to PATH)
   - **macOS**: `brew install graphviz`
   - **Linux**: `sudo apt-get install graphviz`
3. A working C compiler may be required for `xgboost` wheels.

---

## Quick Start

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the full pipeline (deterministic, ~3–5 min)
python scripts/run_all.py
```

Generated figures and CSVs are written to `outputs/`; synthetic sample data is written to `data/sample/`.

---

## Script Overview

| Script | Purpose |
|--------|---------|
| `scripts/run_all.py` | Master runner — executes the full pipeline in order with fixed random seeds |
| `scripts/generate_synthetic_ocel.py` | Timber-manufacturing simulator with 13 conformance rules |
| `scripts/generate_release_sample_data.py` | Creates the 10 k-event timber sample and cross-sector stand-ins |
| `scripts/generate_cross_sector_samples.py` | Generates tube-manufacturing synthetic stand-ins |
| `scripts/role_classification.py` | Stage 1 — trains GA-XGBoost / SVM / DNN / RF and produces classifier comparison figure |
| `scripts/cross_sector_evaluation.py` | Stage 1b — evaluates entropy-threshold active learning across three sector configs |
| `scripts/generate_inductive_miner.py` | Stage 2 — discovers DFG / Inductive-Miner models and renders process-model figures |
| `scripts/regenerate_figures.py` | Rebuilds analytical figures from aggregate CSVs at 600 DPI (Revision 3) |
| `scripts/regenerate_miner_comparison.py` | Rebuilds the miner-comparison figure |
| `scripts/figure_style.py` | Shared matplotlib style module (600 DPI, MATLAB palette, serif 13 pt) |

---

## Reproducibility Notes

- **Determinism**: Every script sets `random_state=42` (scikit-learn / XGBoost) or `np.random.default_rng(42)` / `random.seed(42)`. Running the pipeline twice on the same machine produces identical outputs.
- **Cross-sector stand-ins**: The tube-manufacturing logs and sensor files are synthetic stand-ins that preserve the original column schema so that `cross_sector_evaluation.py` can run end-to-end without proprietary industrial files.
- **Runtime outputs**: The `data/` and `outputs/` folders are created automatically if they do not exist.

---

## Folder Layout

```
├── scripts/
│   ├── run_all.py
│   ├── figure_style.py
│   ├── generate_synthetic_ocel.py
│   ├── generate_release_sample_data.py
│   ├── generate_cross_sector_samples.py
│   ├── role_classification.py
│   ├── cross_sector_evaluation.py
│   ├── generate_inductive_miner.py
│   ├── regenerate_figures.py
│   └── regenerate_miner_comparison.py
├── requirements.txt
├── LICENSE
└── README.md
```

---

## License

See `LICENSE` for terms. The code is released for verification and academic
reproduction purposes subject to the industrial confidentiality agreement
governing the underlying dataset.
