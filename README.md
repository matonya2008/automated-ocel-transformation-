# Automated OCEL Transformation Graph Code

This repository is the code-availability package for the manuscript:

`Automated OCEL Transformation for Real-Time Conformance in Complex Manufacturing`

It contains only the Python code used to generate the manuscript graphs and supporting synthetic-data utilities. No datasets are committed to this repository.

## Included Python code

- `scripts/generate_synthetic_ocel.py`
  Generates a synthetic OCEL-style manufacturing dataset locally.
- `scripts/generate_release_sample_data.py`
  Creates a local sample dataset for running the public figure scripts.
- `scripts/run_role_classification_experiment.py`
  Produces the classifier-comparison figure from the local sample dataset.
- `scripts/cross_sector_eval.py`
  Produces the entropy-threshold / scalability figure.
- `scripts/generate_inductive_miner.py`
  Produces the DFG and Inductive Miner process-mining figures.
- `scripts/regenerate_ad_hoc_figures.py`
  Regenerates selected manuscript figures from locally prepared CSV inputs.
- `scripts/pub_style.py`
  Shared plotting and export style used by the figure scripts.

## Intentionally excluded

- Raw industrial logs
- Sample CSV files
- Aggregate result CSV files
- Generated figure outputs
- Internal notes and manuscript-support documentation

## Quick start

```powershell
pip install -r requirements.txt
python scripts/generate_release_sample_data.py
python scripts/run_role_classification_experiment.py
python scripts/cross_sector_eval.py
python scripts/generate_inductive_miner.py
```

Generated figures are written to `outputs/`.

`scripts/regenerate_ad_hoc_figures.py` expects locally available CSV inputs and is included for code transparency, not because those CSVs are published here.
