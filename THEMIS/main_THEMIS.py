#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Owner: Michelle Vrapi
# Affiliation: Politecnico di Milano
# Last update: 13/11/2025

"""
THEMIS – Master pipeline launcher

This script runs all THEMIS pipeline steps in sequence,
in the order defined in SCRIPTS_ORDER.

Place this file inside the THEMIS folder and run it with:
    python main_THEMIS.py
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS_ORDER = [
    inputs.py,
    GeoTIFF.py,
    png_generation.py,
    cov_diff_map.py,
    meshed_maps.py,
    histogram_barchart.py,
    csv_ML.py,
    themis_timeslot_flags_ops.py,
    summary_table.py,
    themis_ml_flags_only.py,
    operation_zones.py
]


# =====================================================================
# SUPPORT FUNCTIONS
# =====================================================================

def run_script(script_path: Path) -> None:
    """Run a Python script as a subprocess, stopping the pipeline if it fails."""
    print("\n" + "=" * 72)
    print(f"▶ RUNNING: {script_path.name}")
    print("=" * 72)

    # Use the same Python interpreter that is running this main script
    cmd = [sys.executable, str(script_path)]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ ERROR while executing {script_path.name}")
        print(f"   Exit code: {e.returncode}")
        sys.exit(e.returncode)


def main():
    here = Path(__file__).resolve().parent

    if not SCRIPTS_ORDER:
        print("⚠️  SCRIPTS_ORDER is empty.")
        print("    Edit main_THEMIS.py and add the .py filenames in the correct order.")
        sys.exit(1)

    print("THEMIS pipeline launcher\n")
    print("Execution order:")
    for i, name in enumerate(SCRIPTS_ORDER, start=1):
        print(f"  {i}. {name}")
    print()

    for name in SCRIPTS_ORDER:
        script_path = here / name
        if not script_path.exists():
            print(f"\n⚠️  Script not found: {script_path}")
            print("    Check that the filename in SCRIPTS_ORDER matches a file in the THEMIS folder.")
            sys.exit(1)

        run_script(script_path)

    print("\n✅ THEMIS pipeline completed successfully.")


if __name__ == "__main__":
    main()
