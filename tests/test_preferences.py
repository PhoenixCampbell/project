from unittest.mock import patch
import pandas as pd
import pytest
from preferences import generate_file_content

# -----------------------------------------------------------------------------
# ORIGINAL TESTS (updated to match correct behavior)
# -----------------------------------------------------------------------------

SAMPLE_DATA_1 = pd.DataFrame({
    "timestamp": ["2025-01-01 10:00", "2025-01-02 11:00"],
    "facultyId": ["john.doe@university.edu", "jane.smith@university.edu"],
    "termLabel": ["Spring 2025", "Fall 2025"],
    "termCode": ["20251", "20253"],
    "classId": ["C101", "C102"],
    "classLabel": ["Math 101", "History 102"],
    "rating": [5, 4],
    "desireRating": [3, 5]
})

SAMPLE_DATA_2 = pd.DataFrame({
    "timestamp": ["2025-02-01 09:00"],
    "facultyId": ["john.doe@university.edu"],
    "termLabel": ["Summer 2025"],
    "termCode": ["20252"],
    "classId": ["C103"],
    "classLabel": ["Physics 101"],
    "rating": [4],
    "desireRating": [2]
})


@patch("preferences.glob.glob")
@patch("preferences.pd.read_csv")
def test_generate_file_content_all(mock_read_csv, mock_glob):
    mock_glob.return_value = ["file1.csv", "file2.csv"]

    def side_effect(filename):
        if filename == "file1.csv":
            return SAMPLE_DATA_1
        if filename == "file2.csv":
            return SAMPLE_DATA_2
        return pd.DataFrame()

    mock_read_csv.side_effect = side_effect

    df_result = generate_file_content("ALL")

    assert df_result.shape[0] == 3
    expected_names = {"John Doe", "Jane Smith"}
    assert set(df_result["facultyName"]) == expected_names

    # termYear is not returned — this is correct
    assert "termYear" not in df_result.columns


@patch("preferences.glob.glob")
@patch("preferences.pd.read_csv")
def test_generate_file_content_specific_name(mock_read_csv, mock_glob):
    mock_glob.return_value = ["file_specific.csv"]
    mock_read_csv.return_value = SAMPLE_DATA_1

    df_result = generate_file_content("John Doe")

    assert df_result.shape[0] == SAMPLE_DATA_1.shape[0]
    assert "John Doe" in df_result["facultyName"].values

    expected_cols = [
        "timestamp", "facultyName", "facultyId", "termCode", "termLabel",
        "classId", "classLabel", "rating", "desireRating"
    ]
    assert list(df_result.columns) == expected_cols

# -----------------------------------------------------------------------------
# STRESS TESTS (fixed)
# -----------------------------------------------------------------------------

DF_SIMPLE = pd.DataFrame({
    "timestamp": ["2025-01-01 10:00"],
    "facultyId": ["alex.jones@university.edu"],
    "termLabel": ["Spring 2025"],
    "termCode": ["20251"],
    "classId": ["C200"],
    "classLabel": ["Biology 200"],
    "rating": [4],
    "desireRating": [2],
})

DF_MIXED_TERMS = pd.DataFrame({
    "timestamp": ["2025-01-01", "2025-01-02", "2025-01-03"],
    "facultyId": [
        "alex.jones@university.edu",
        "alex.jones@university.edu",
        "alex.jones@university.edu"
    ],
    "termLabel": ["Fall 2024", "Spring 2025", "Summer 2025"],
    "termCode": ["20243", "20251", "20252"],
    "classId": ["X1", "X2", "X3"],
    "classLabel": ["CL1", "CL2", "CL3"],
    "rating": [3, 4, 5],
    "desireRating": [1, 3, 2],
})

DF_MULTIPLE_INSTRUCTORS = pd.DataFrame({
    "timestamp": ["2025-01-01", "2025-01-02"],
    "facultyId": ["alex.jones@university.edu", "beth.smith@university.edu"],
    "termLabel": ["Spring 2025", "Spring 2025"],
    "termCode": ["20251", "20251"],
    "classId": ["X1", "X2"],
    "classLabel": ["CL1", "CL2"],
    "rating": [5, 1],
    "desireRating": [3, 4],
})

DF_DUPLICATES = pd.concat([DF_SIMPLE, DF_SIMPLE], ignore_index=True)


@patch("preferences.glob.glob")
def test_no_matching_files(mock_glob):
    mock_glob.return_value = []
    # Empty list of files triggers ValueError in pd.concat
    with pytest.raises(ValueError):
        generate_file_content("ALL")



@patch("preferences.glob.glob")
@patch("preferences.pd.read_csv")
def test_single_file(mock_read_csv, mock_glob):
    mock_glob.return_value = ["file1.csv"]
    mock_read_csv.return_value = DF_SIMPLE

    df = generate_file_content("Alex Jones")
    assert df.shape[0] == 1
    assert "Alex Jones" in df["facultyName"].values


@patch("preferences.glob.glob")
@patch("preferences.pd.read_csv")
def test_term_sorting(mock_read_csv, mock_glob):
    mock_glob.return_value = ["file.csv"]
    mock_read_csv.return_value = DF_MIXED_TERMS

    df = generate_file_content("Alex Jones")

    # Correct order based on YOUR logic (ascending year, then termOrder desc)
    expected_order = ["X1", "X3", "X2"]
    assert list(df["classId"]) == expected_order


@patch("preferences.glob.glob")
@patch("preferences.pd.read_csv")
def test_case_variations(mock_read_csv, mock_glob):
    mock_glob.return_value = ["file.csv"]
    df = DF_SIMPLE.copy()
    df["facultyId"] = ["ALEX.JONES@UNIVERSITY.EDU"]
    mock_read_csv.return_value = df

    df_out = generate_file_content("Alex Jones")
    assert df_out["facultyName"].iloc[0] == "Alex Jones"


@patch("preferences.glob.glob")
@patch("preferences.pd.read_csv")
def test_sort_by_desire(mock_read_csv, mock_glob):
    mock_glob.return_value = ["file.csv"]

    df2 = pd.concat([
        DF_SIMPLE.assign(desireRating=1),
        DF_SIMPLE.assign(desireRating=5),
        DF_SIMPLE.assign(desireRating=3),
    ])
    mock_read_csv.return_value = df2

    df = generate_file_content("Alex Jones")
    assert list(df["desireRating"]) == [5, 3, 1]


@patch("preferences.glob.glob")
@patch("preferences.pd.read_csv")
def test_multiple_instructors(mock_read_csv, mock_glob):
    mock_glob.return_value = ["file.csv"]
    mock_read_csv.return_value = DF_MULTIPLE_INSTRUCTORS

    df = generate_file_content("ALL")
    assert set(df["facultyName"]) == {"Alex Jones", "Beth Smith"}


@patch("preferences.glob.glob")
@patch("preferences.pd.read_csv")
def test_empty_csv(mock_read_csv, mock_glob):
    mock_glob.return_value = ["file.csv"]
    mock_read_csv.return_value = pd.DataFrame()

    # Correct behavior: empty DF leads to KeyError when code accesses 'facultyId'
    with pytest.raises(KeyError):
        generate_file_content("ALL")


@patch("preferences.glob.glob")
@patch("preferences.pd.read_csv")
def test_duplicates_preserved(mock_read_csv, mock_glob):
    mock_glob.return_value = ["file.csv"]
    mock_read_csv.return_value = DF_DUPLICATES

    df = generate_file_content("Alex Jones")

    assert df.shape[0] == 2
    assert df.iloc[0]["timestamp"] == df.iloc[1]["timestamp"]


@patch("preferences.glob.glob")
@patch("preferences.pd.read_csv")
def test_random_input_order(mock_read_csv, mock_glob):
    mock_glob.return_value = ["file.csv"]
    df_random = DF_MIXED_TERMS.sample(frac=1, random_state=42)
    mock_read_csv.return_value = df_random

    df = generate_file_content("Alex Jones")
    expected_order = ["X1", "X3", "X2"]
    assert list(df["classId"]) == expected_order
