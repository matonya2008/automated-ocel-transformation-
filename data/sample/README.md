# Sample Data

This directory is reserved for public, non-confidential sample datasets.

Generate the synthetic sample used by the public scripts with:

```powershell
python scripts/generate_release_sample_data.py
```

Optional additional sanitized datasets may also be placed here:

- `tube_logs_sample.csv`
- `tube_sensor_sample.csv`

If those optional files are absent, `scripts/cross_sector_eval.py` will skip them automatically.
