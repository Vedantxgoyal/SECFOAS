# diagnose2.py
from modules.data_loader import load_data
import pandas as pd

df = load_data()
print("=== ALL COMPLETE SUNDAYS IN DATASET ===")
for date, group in df.groupby(df.index.date):
    if pd.Timestamp(date).dayofweek == 6 and len(group) == 48:
        print(f"{date}  mean={group['energy'].mean():.4f}  "
              f"std={group['energy'].std():.4f}  max={group['energy'].max():.4f}")