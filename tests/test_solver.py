from unittest.mock import patch, mock_open

import pytest
import pandas as pd
import solver


# ----------------------------------------------------------------------
# compute_weight
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "tenure, desire, comfort, expected",
    [
        # tenure <= 10
        (10, 4, 4, 4),
        (5, 1, 1, 2),
        (8, 3, 3, 0),

        # tenure > 11
        (12, 1, 1, 1),
        (15, 4, 3, 3),
        (20, 4, 4, 0),
    ],
)
def test_compute_weight(tenure, desire, comfort, expected):
    assert solver.compute_weight(tenure, desire, comfort) == expected


# ----------------------------------------------------------------------
# safe_sheet_name_from_faculty
# ----------------------------------------------------------------------
def test_strip_email():
    assert solver.safe_sheet_name_from_faculty("prof@school.edu") == "prof"


def test_replace_illegal_characters():
    assert solver.safe_sheet_name_from_faculty("a:b/c?d*e[f]") == "a_b_c_d_e_f_"


def test_empty_string():
    assert solver.safe_sheet_name_from_faculty("") == "Sheet"


def test_trim_to_31_chars():
    long_name = "x" * 100
    assert solver.safe_sheet_name_from_faculty(long_name) == ("x" * 31)


# ----------------------------------------------------------------------
# load_tenure_map
# ----------------------------------------------------------------------
def test_load_tenure_map_good_data():
    csv_content = "facultyKey,tenure\nabc,10\nxyz,20\n"

    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.open", mock_open(read_data=csv_content)):
        result = solver.load_tenure_map()

    assert result == {"abc": 10, "xyz": 20}


def test_load_tenure_map_invalid_rows():
    csv_content = "facultyKey,tenure\nabc,notanumber\n,5\n"

    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.open", mock_open(read_data=csv_content)):
        result = solver.load_tenure_map()

    assert not result  # no valid rows


def test_load_tenure_map_file_missing():
    with patch("pathlib.Path.exists", return_value=False):
        assert not solver.load_tenure_map()


# ----------------------------------------------------------------------
# process_csv_file
# ----------------------------------------------------------------------
def test_process_csv_file_basic():
    df = pd.DataFrame({
        "facultyId": ["f1"],
        "termLabel": ["Fall"],
        "termCode": [123],
        "classId": ["C101"],
        "classLabel": ["Math"],
        "rating": [3],
        "desireRating": [4],
    })

    with patch("pandas.read_csv", return_value=df), \
         patch.object(solver, "compute_weight", return_value=99):
        result = solver.process_csv_file(solver.Path("pref_f1_123.csv"), {"f1": 12})

    assert len(result) == 1
    row = result[0]
    assert row.faculty_id == "f1"
    assert row.weight == 99


# ----------------------------------------------------------------------
# collect_candidates
# ----------------------------------------------------------------------
def test_collect_candidates():
    fake_rows = [solver.AssignmentRow("a", "t", "1", "c", "label", 5)]

    with patch("solver.process_csv_file", return_value=fake_rows):
        result, wrote = solver.collect_candidates(["f1.csv"], {})
        assert result == fake_rows
        assert wrote is True


def test_collect_candidates_none_written():
    with patch("solver.process_csv_file", return_value=[]):
        result, wrote = solver.collect_candidates(["f1.csv"], {})
        assert not result
        assert wrote is False


# ----------------------------------------------------------------------
# apply_assignment
# ----------------------------------------------------------------------
def test_apply_assignment_basic():
    c1 = solver.AssignmentRow("f1", "Fall", "1", "C1", "Math", 5)
    c2 = solver.AssignmentRow("f1", "Fall", "1", "C1", "Math", 3)  # duplicate

    with patch("solver.append_to_excel", return_value=True) as mock_append:
        solver.apply_assignment([c1, c2], {})

    # Only one call, duplicate skipped
    mock_append.assert_called_once_with(c1, solver.OUTPUT_XLSX)


def test_apply_assignment_respects_load():
    rows = [
        solver.AssignmentRow("f1", "Fall", "1", f"C{i}", "Math", 5)
        for i in range(10)
    ]

    with patch("solver.append_to_excel", return_value=True) as mock_append:
        solver.apply_assignment(rows, {})

    assert mock_append.call_count == solver.MAX_CLASSES_PER_FACULTY


# ----------------------------------------------------------------------
# run_solver_for_all_prefs
# ----------------------------------------------------------------------
def test_run_solver_no_files_raises():
    with patch("glob.glob", return_value=[]):
        with pytest.raises(RuntimeError):
            solver.run_solver_for_all_prefs()


def test_run_solver_filters_term_code():
    fake_path = solver.DATA_DIR / "pref_f1_123.csv"

    fake_df = pd.DataFrame({
        "facultyId": ["f1"],
        "termLabel": ["Spring"],
        "termCode": ["123"],
        "classId": ["C101"],
        "classLabel": ["Math"],
        "rating": [4],
        "desireRating": [5],
    })

    with patch("glob.glob", return_value=[str(fake_path)]), \
         patch("pandas.read_csv", return_value=fake_df), \
         patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.open", mock_open()), \
         patch("pathlib.Path.unlink", return_value=None), \
         patch("solver.append_to_excel", return_value=True):
        out = solver.run_solver_for_all_prefs("123")

    # It still returns a Path object
    assert isinstance(out, solver.Path)


def test_run_solver_happy_path():
    fake_path = solver.DATA_DIR / "pref_f1_123.csv"
    fake_candidate = solver.AssignmentRow("f", "T", "1", "C", "L", 1)

    with patch("glob.glob", return_value=[str(fake_path)]), \
         patch("solver.collect_candidates", return_value=([fake_candidate], True)), \
         patch("solver.apply_assignment") as mock_apply, \
         patch("pathlib.Path.exists", return_value=False), \
         patch("pathlib.Path.unlink", return_value=None):

        out = solver.run_solver_for_all_prefs("123")

    # Make sure it returned a Path object
    assert isinstance(out, solver.Path)
    # Ensure assignments were applied
    mock_apply.assert_called_once_with([fake_candidate])
