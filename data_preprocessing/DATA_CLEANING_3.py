import pandas as pd
import numpy as np
import os

# ===============================
# Step 1: Load Excel file
# ===============================
df = pd.read_excel(r"D:\Projects\SECFAOS\41433960.xls")

# ===============================
# Step 2: Clean column names
# ===============================
df.columns = df.columns.str.strip()

# ===============================
# Step 3: Convert datetime column
# ===============================
df['datetime'] = pd.to_datetime(
    df['Load Survey Time'],
    format='%d-%m-%Y %H:%M',
    errors='coerce'
)

# Drop rows where datetime conversion failed
df = df.dropna(subset=['datetime'])

# ===============================
# Step 4: Extract Active Energy
# ===============================
df = df.rename(columns={'Active Energy (kWh)': 'energy'})

df['energy'] = pd.to_numeric(df['energy'], errors='coerce')

# ===============================
# Step 5: Keep only required columns
# ===============================
df = df[['datetime', 'energy']]

# ===============================
# Step 6: Sort chronologically
# ===============================
df = df.sort_values('datetime').reset_index(drop=True)

# ===============================
# Step 7: Enforce 30-minute frequency
# ===============================
df = df.set_index('datetime').asfreq('30min')

# ===============================
# Step 8: Forward fill missing values
# ===============================
df['energy'] = df['energy'].ffill()

# ===============================
# Step 9: Save cleaned file safely
# ===============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(BASE_DIR, "outputs")
os.makedirs(output_dir, exist_ok=True)

output_path = os.path.join(output_dir, "meter3_clean.csv")
df.to_csv(output_path)

print("Meter 3 cleaned successfully.")