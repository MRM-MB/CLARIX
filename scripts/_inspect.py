"""Quick schema inspector for the Danfoss hackathon workbook."""
import pandas as pd
from pathlib import Path

XL = Path("data/hackathon_dataset.xlsx")
xl = pd.ExcelFile(XL)
print("SHEETS:", xl.sheet_names)
for s in xl.sheet_names:
    df = pd.read_excel(xl, s, nrows=3)
    print(f"\n=== {s}  ({df.shape[1]} cols) ===")
    print("cols:", list(df.columns))
    print(df.head(2).to_string(max_cols=12))
