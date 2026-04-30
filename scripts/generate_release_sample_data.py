import json
from pathlib import Path

import pandas as pd

from generate_synthetic_ocel import CONFORMANCE_RULES, generate_full_dataset


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data" / "sample"
DOCS_DIR = REPO_ROOT / "docs"


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    events = generate_full_dataset(num_events=10000, num_cases=400)
    df = pd.DataFrame(events)
    dataset_path = DATA_DIR / "expanded_timber_ocel_10k.csv"
    df.to_csv(dataset_path, index=False)

    rules_path = DOCS_DIR / "conformance_rules_documentation.json"
    rules_path.write_text(
        json.dumps(CONFORMANCE_RULES, indent=2),
        encoding="utf-8",
    )

    print(f"Wrote sample dataset to {dataset_path}")
    print(f"Wrote rule documentation to {rules_path}")


if __name__ == "__main__":
    main()
