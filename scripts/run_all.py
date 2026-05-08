"""
End-to-end reproducibility runner for the code-availability package.

Running this script in order:
  1. Generates all sample datasets (timber + cross-sector stand-ins).
  2. Runs the classifier-comparison experiment (Stage 1).
  3. Runs the cross-sector scalability evaluation (Stage 1 extension).
  4. Generates the process-mining figures (Stage 2).
  5. Regenerates the analytical figures from CSV inputs (Revision 3).

All random seeds are fixed (42) so the outputs are deterministic.
Generated figures are written to ``outputs/``.
"""

import sys
from pathlib import Path

# Ensure scripts/ is importable
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import generate_release_sample_data
import role_classification
import cross_sector_evaluation
import generate_inductive_miner
import regenerate_figures


def main() -> None:
    print("=" * 70)
    print("AUTOMATED OCEL TRANSFORMATION — Code Availability Reproduction")
    print("=" * 70)

    print("\n[1/5] Generating sample datasets ...")
    generate_release_sample_data.main()

    print("\n[2/5] Stage 1: Role-classifier comparison ...")
    role_classification.run_experiment()

    print("\n[3/5] Stage 1b: Cross-sector scalability ...")
    cross_sector_evaluation.run_cross_sector_validation()

    print("\n[4/5] Stage 2: Process-mining figure generation ...")
    generate_inductive_miner.main()

    print("\n[5/5] Revision-3: Analytical figure regeneration ...")
    regenerate_figures.main()

    print("\n" + "=" * 70)
    print("All done. Outputs are in the outputs/ directory.")
    print("=" * 70)


if __name__ == "__main__":
    main()
