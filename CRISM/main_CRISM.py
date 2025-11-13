#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Owner: Michelle Vrapi
# Affiliation: Politecnico di Milano
# Last update: 13/11/2025

"""
CRISM – Master pipeline launcher

This script runs all CRISM pipeline steps in sequence,
in the order defined in SCRIPTS_ORDER.

Place this file inside the CRISM folder and run it with:
    python main_crism.py
"""

import subprocess
import sys
from pathlib import Path


# =====================================================================
# 1) DEFINE HERE THE EXECUTION ORDER OF THE PIPELINE SCRIPTS
#
# Replace the example names below with the REAL filenames of your .py
# scripts inside the CRISM folder, following the order defined in crism.py:
#   1. CRISM_RGB.py
#   2. CRISM_mesh_axis.py
#   3. CRISM_mesh.py
#   4. CRISM_data.py
#   5. CRISM_data_percentage
#   6. good_bad_spots.py
#   7. flag_mineral_composition.py
# =====================================================================

SCRIPTS_ORDER = [
    CRISM_RGB.py,
    CRISM_mesh_axis.py,
    CRISM_mesh.py,
    CRISM_data.py,
    CRISM_data_percentage,
    good_bad_spots.py,
    flag_mineral_composition.py
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
        print("    Edit main_crism.py and add the .py filenames in the correct order.")
        sys.exit(1)

    print("CRISM pipeline launcher\n")
    print("Execution order:")
    for i, name in enumerate(SCRIPTS_ORDER, start=1):
        print(f"  {i}. {name}")
    print()

    for name in SCRIPTS_ORDER:
        script_path = here / name
        if not script_path.exists():
            print(f"\n⚠️  Script not found: {script_path}")
            print("    Check that the filename in SCRIPTS_ORDER matches a file in the CRISM folder.")
            sys.exit(1)

        run_script(script_path)

    print("\n✅ CRISM pipeline completed successfully.")


if __name__ == "__main__":
    main()
