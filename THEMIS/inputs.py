import sys
!{sys.executable} -m pip install rasterio
import numpy, rasterio
print("NumPy:", numpy.__version__)
print("Rasterio:", rasterio.__version__)

from google.colab import drive
drive.mount('/content/drive')

# PUT HERE the folder where the XML files are located.
# Examples:
#   path = "/content"                       # if you upload them directly to Colab
#   path = "/content/drive/MyDrive/THEMIS"  # if they are stored on Drive
path = "/content/drive/MyDrive/winter_school/INTERSTELLAR_ALLIANCE/THEMIS/michelle version/data/all_data"

import glob, os
xml_paths = sorted(glob.glob(os.path.join(path, "*.xml")))
print(f"Trovati {len(xml_paths)} file XML")
for p in xml_paths[:10]:
    print(" -", os.path.basename(p))

import re
import xml.etree.ElementTree as ET

def extract_text_any(elem):
    """Clean text of an element (or None)."""
    if elem is None:
        return None
    txt = (elem.text or "").strip()
    return txt or None

def find_first_by_tag_name_anyns(root, wanted_names):
    """
    Find the FIRST element whose tag (ignoring namespace) is in wanted_names.
    wanted_names: list of possible names (case-insensitive).
    """
    wanted = {w.lower() for w in wanted_names}
    for elem in root.iter():
        # remove namespace if present: {ns}Tag -> Tag
        tag = elem.tag.split('}', 1)[-1].lower()
        if tag in wanted:
            return elem
    return None

def extract_lst_from_label(xml_file):
    """
    Extract an LST from a PDS4 THEMIS label.
    Try various common keys; if nothing is found, attempt a regex fallback on the entire XML.
    Returns a string like 'HH:MM:SS[.fff]' or None.
    """
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
    except Exception as e:
        return None

    # Observed/possible keys in THEMIS labels
    candidate_tags = [
        "local_true_solar_time",
        "start_local_true_solar_time",
        "stop_local_true_solar_time",
        "local_solar_time",  # in some legacy labels
    ]
    node = find_first_by_tag_name_anyns(root, candidate_tags)
    txt = extract_text_any(node)

    if not txt:
        # Fallback: regex on the entire XML text
        try:
            with open(xml_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except:
            content = ""
        # look for time patterns like 18:57:40.8 or 06:05:20
        m = re.search(r"\b(\d{1,2}:\d{2}:\d{2}(?:\.\d+)?)\b", content)
        txt = m.group(1) if m else None

    if not txt:
        return None

    # Normalize to HH:MM:SS(.fff) with leading zeros
    # Extract numbers; keep any decimal part of seconds
    m = re.match(r"^\s*(\d{1,2}):(\d{2}):(\d{2}(?:\.\d+)?)\s*$", txt)
    if not m:
        return txt.strip()
    hh = int(m.group(1))
    mm = m.group(2)
    ss = m.group(3)
    return f"{hh:02d}:{mm}:{ss}"

import pandas as pd
import os

rows = []
for p in xml_paths:
    file_id = os.path.splitext(os.path.basename(p))[0]
    lst = extract_lst_from_label(p)
    rows.append({"file_id": file_id, "LST": lst, "file_path": p})

df = pd.DataFrame(rows).sort_values(["LST", "file_id"], na_position="last").reset_index(drop=True)
df

out_csv = "/content/themis_lst_index.csv"
df.to_csv(out_csv, index=False)
print("CSV saved in:", out_csv)
