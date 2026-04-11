import os
import glob
import sys
from pathlib import Path
from dataclasses import dataclass
import json
from json import JSONDecodeError
from openpyxl import load_workbook, Workbook

import pandas as pd

@dataclass
class AssignmentRow:
    faculty_id: str
    term_label: str
    term_code: str
    class_id: str
    class_label: str
    weight: int

# Links to where data will be stored
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / ("data")
OUTPUT_XLSX = DATA_DIR / "solution.xlsx"
TENURE_CSV = DATA_DIR / "tenure.csv"
MAX_CLASSES_PER_FACULTY = 4 # Do not give more than N classes to any given prof

def load_crosslist_canonical_map(term_code: str | None) -> dict[str, str]:
    # loading croslisted courses from *tiny.json files section crossListed
    # build a map from each classId to a groupId
    #if catches on fire, return empty map

    if not term_code:
        return {}

    path = DATA_DIR / f"{term_code}tiny.json"
    if not path.exists():
        return {}

    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (FileNotFoundError, OSError, JSONDecodeError):
        return {}

    cross = data.get("crossListed") or {}
    canonical: dict[str, str] = {}

    #expects:
    #crossListed: {
    #   DJ: ["29038", "29039"], as is crosslisted pair
    #   D28: ["29040", "29041"],
    #}
    for _, ids in cross.items():
        if not ids:
            continue
        #use the first id as the blueprint of what to expect
        canonical_id = ids[0]
        for cid in ids:
            canonical[cid] = canonical_id

    return canonical

def compute_weight(tenure: int, desire: int, comfort: int) -> int:


    # Find weight based on tenure, desire, and comfort ratings
    weight = 0 # Default


        # THE MEAT
    if tenure <= 10:
        if desire > 3 and comfort > 3:
            weight = 4
        elif desire < 2 and comfort < 2:
            weight = 2
    elif tenure > 11:
        if desire < 2 and comfort < 2:
            weight = 1
        elif desire > 3 and comfort <= 3: # pylint: disable=chained-comparison
            weight = 3

    return weight

def safe_sheet_name_from_faculty(faculty_id: str) -> str:


    # Turning facultyId into an Excel sheet name
    # Allows each sheet inside the workbook to be an individual professor for ease of access

    base = faculty_id or "Sheet"
    if "@" in base:
        base = base.split("@")[0]

    for ch in [":", "\\", "/", "?", "*", "[", "]"]:
        base = base.replace(ch, "_")

    base = base.strip() or "Sheet"


    # Making sure name stays under Excel's limits for sheets
    return base[:31]

def load_tenure_map() -> dict[str, int]:
    tenure_map: dict[str, int] = {}
    if not TENURE_CSV.exists():
        return tenure_map

    with TENURE_CSV.open("r", encoding="utf-8") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]


    # Expect header: facultyKey,tenure
    for line in lines[1:]:
        parts = line.split(",")
        if len(parts) < 2:
            continue
        faculty_key = parts[0].strip()
        try:
            tenure_val = int(parts[1].strip())
        except ValueError:
            continue
        if faculty_key:
            tenure_map[faculty_key] = tenure_val

    return tenure_map

def append_to_excel(row: AssignmentRow, file_path: Path = OUTPUT_XLSX) -> bool:
    headers = ["facultyId", "termLabel", "termCode", "classId", "classLabel", "weight"]
    sheet_name = safe_sheet_name_from_faculty(row.faculty_id)


    # Loads or creates workbook
    if os.path.exists(file_path):
        wb = load_workbook(file_path)
    else:
        wb = Workbook()
        if "Sheet" in wb.sheetnames and len(wb.sheetnames) == 1:
            wb.remove(wb["Sheet"])


    # Sheet in said workbook
    if sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
    else:
        ws = wb.create_sheet(sheet_name)


    # Append the headers
    if ws.max_row == 1 and all(cell.value is None for cell in ws[1]):
        ws.delete_rows(1, 1)
        ws.append(headers)


    # Check for existing entries
    existing_entries = set()
    for xrow in ws.iter_rows(min_row=2, values_only=True):
        if xrow and len(xrow) >= 5:
            existing_entries.add((xrow[0], xrow[1], xrow[2], xrow[3], xrow[4]))

    key = (row.faculty_id, row.term_label, row.term_code, row.class_id, row.class_label)
    if key in existing_entries:
        wb.save(file_path)
        return False

    ws.append([row.faculty_id, row.term_label, row.term_code, row.class_id, row.class_label, row.weight])
    wb.save(file_path)
    return True

def process_csv_file(csv_path: Path, tenure_map: dict[str, int]) -> list[AssignmentRow]:
    candidates = []
    stem = csv_path.stem
    without_prefix = stem[5:] if stem.startswith("pref_") else stem
    parts = without_prefix.split("_")
    faculty_key = "_".join(parts[:-1]) # Everything except last bit

    df = pd.read_csv(csv_path)

    # Map existing columns to solver inputs
    # Rating -> comfort, DesireRating -> desire
    comfort_col = "rating"
    desire_col = "desireRating"

    # Clean, ensure numbers
    df[comfort_col] = df[comfort_col].astype(int)
    df[desire_col] = df[desire_col].astype(int)

    # Placeholder tenure
    tenure_value = tenure_map.get(faculty_key, 10)
    df["tenure"] = int(tenure_value)

    selected_columns = [
        "facultyId",
        "termLabel",
        "termCode",
        "classId",
        "classLabel",
        "tenure",
        desire_col,
        comfort_col,
    ]
    for _, df_row in df[selected_columns].iterrows():
        faculty_id = df_row["facultyId"]
        term_label = df_row["termLabel"]
        row_term_code = str(df_row["termCode"])
        class_id = df_row["classId"]
        class_label = df_row["classLabel"]
        tenure = int(df_row["tenure"])
        desire = int(df_row[desire_col])
        comfort = int(df_row[comfort_col])

        weight = compute_weight(tenure, desire, comfort)
        candidates.append(AssignmentRow(
                faculty_id=faculty_id,
                term_label=term_label,
                term_code=row_term_code,
                class_id=class_id,
                class_label=class_label,
                weight=weight,
        ))
    return candidates

def collect_candidates(files: list[str], tenure_map: dict[str, int]) -> tuple[list[AssignmentRow], bool]:
    candidates = []
    wrote_any_rows = False

    for csv_path in files:
        candidates.extend(process_csv_file(Path(csv_path), tenure_map))
        if candidates:
            wrote_any_rows = True

    return candidates, wrote_any_rows

def apply_assignment(candidates: list[AssignmentRow], crosslist_map: dict[str, str]) -> None:
    if not candidates:
        return

    group_index: dict[tuple[str, str, str], dict[str, AssignmentRow]] = {}
    for c in candidates:
        group_cls = crosslist_map.get(c.class_id, c.class_id)
        key = (c.faculty_id, c.term_code, group_cls)
        bucket = group_index.setdefault(key, {})
        if c.class_id not in bucket:
            bucket[c.class_id] = c

    # Sort high weight first
    candidates.sort(key=lambda c: c.weight, reverse=True)

    faculty_load: dict[str, int] ={}
    assigned_classes: set[tuple[str, str]] = set()

    for c in candidates:
        f = c.faculty_id
        t = c.term_code
        cls = c.class_id
        group_cls = crosslist_map.get(cls, cls)
        key = (f, t, group_cls)

        # Skip if max load
        if faculty_load.get(f, 0) >= MAX_CLASSES_PER_FACULTY:
            continue

        #if any member of the crosslisted group is already assigned
        #treat it as taken
        if (t, group_cls) in assigned_classes:
            continue

        append_to_excel(
            c,
            OUTPUT_XLSX,
        )

        group_rows = group_index.get(key, {})
        for other_id, other_row in group_rows.items():
            if other_id == cls:
                continue
            append_to_excel(other_row, OUTPUT_XLSX)

        faculty_load[f] = faculty_load.get(f, 0) + 1
        assigned_classes.add((t, group_cls))

def run_solver_for_all_prefs(term_code: str | None = None, data_dir: Path = DATA_DIR) -> Path:
    # Scans all preference CSVs in folder 'data', computes weights, and writes solution.xlsx
    # Each faculty gets their own sheet with only their rows

    tenure_map = load_tenure_map()
    crosslist_map = load_crosslist_canonical_map(term_code)
    pattern = data_dir / "pref_*.csv"
    files = list(glob.glob(str(pattern)))

    if term_code:
        filtered_files = []
        for f in files:
            stem = Path(f).stem
            parts = stem.split("_")
            last_part = parts[-1] if parts else ""
            if last_part == term_code:
                filtered_files.append(f)
        files = filtered_files

    if not files:
        if term_code:
            raise RuntimeError(f"No Preference CSVs found for termCode {term_code}")
        # Linter doesn't want an else: statement here... oh well
        raise RuntimeError(f"No preference CSVs found matching {pattern}")

    # Clean workbook each time, less hassle
    if OUTPUT_XLSX.exists():
        OUTPUT_XLSX.unlink()

    candidates, wrote_any_rows = collect_candidates(files, tenure_map)

    apply_assignment(candidates, crosslist_map)

    if not wrote_any_rows:
        wb = load_workbook(OUTPUT_XLSX)
        if "Sheet" in wb.sheetnames and len(wb.sheetnames) == 1:
            ws = wb["Sheet"]
            ws["A1"] = (
                f"No matching preference rows found for termCode {term_code}"
                if term_code
                else "No matching preference rows found"
            )
            wb.save(OUTPUT_XLSX)

    return OUTPUT_XLSX

if __name__ == "__main__":
    term_code_arg = sys.argv[1] if len(sys.argv) > 1 else None
    out = run_solver_for_all_prefs(term_code_arg)
    if term_code_arg:
        print(f"Solved for termCode {term_code_arg}. Results written to {out}")
    else:
        print(f"Solved for all terms. Results written to {out}")
