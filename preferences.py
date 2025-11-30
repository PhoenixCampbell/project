import glob
import sys
import pandas as pd

def generate_file_content(name):
    # ---- Read one or more CSV files ----
    # If using a folder of CSVs:
    if name == "ALL":
        files = glob.glob("data/*.csv")  # or replace with your own pattern
    else:
        filename_template = f"pref_{name.lower().replace(' ', '_')}_dsu_edu_*.csv"
        files = glob.glob(f"data/{filename_template}")

    # ---- Read CSVs and keep all rows ----
    dfs = []
    for f in files:
        df_temp = pd.read_csv(f)
        dfs.append(df_temp)

    df = pd.concat(dfs, ignore_index=True)

    # ---- Extract facultyName from facultyId ----
    df["facultyName"] = (
        df["facultyId"]
        .str.split("@").str[0]     # before @
        .str.replace(".", " ", regex=False)     # replace '.' with space
        .str.title()               # title case
    )

    # ---- Split termLabel into parts like "Spring 2025" ----
    df[['termName', 'termYear']] = df['termLabel'].str.split(' ', expand=True)
    df['termYear'] = df['termYear'].astype(int)

    # ---- Map terms to numeric order ----
    term_order = {"Spring": 1, "Summer": 2, "Fall": 3}
    df['termOrder'] = df['termName'].map(term_order)

    # ---- Final Sort ----
    # 1. facultyId (ascending)
    # 2. termYear (descending)
    # 3. termOrder (desc: Fall > Summer > Spring)
    # 4. desireRating (descending)
    df = df.sort_values(
        by=["facultyId", "termYear", "termOrder", "desireRating"],
        ascending=[True, True, False, False]
    ).reset_index(drop=True)

    # ---- Reorder columns for final output ----
    ordered_cols = [
        "timestamp", "facultyName", "facultyId", "termCode", "termLabel",
        "classId", "classLabel", "rating", "desireRating"
    ]
    df = df[ordered_cols]

    return df

if __name__ == "__main__":
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    pd.set_option('display.max_colwidth', None)

    if len(sys.argv) < 2:
        print("No name provided", file=sys.stderr)
        sys.exit(1)
    instructor_name = sys.argv[1]
    content = generate_file_content(instructor_name)
    print(content)
