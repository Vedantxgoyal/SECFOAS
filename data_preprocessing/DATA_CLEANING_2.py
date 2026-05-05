import pandas as pd
import numpy as np
import os

# ===============================
# Step 1: Load raw Meter 2 data
# ===============================
df = pd.read_csv(r"D:\Projects\SECFAOS\29559724_20251115_20250818.csv")

# ===============================
# Step 2: Remove fully empty rows
# ===============================
df = df.dropna(how='all')

# ===============================
# Step 3: Rename relevant columns
# ===============================
df = df.rename(columns={
    'SIP End Date and time': 'datetime',
    'kWh(I) Tot': 'energy_raw'
})

# ===============================
# Step 4: Convert datetime column
# ===============================
df['datetime'] = pd.to_datetime(df['datetime'], format='%d-%m-%Y %H:%M')

# ===============================
# Step 5: Extract numeric energy value
# ===============================
df['energy'] = df['energy_raw'].astype(str).str.extract(r'([\d.]+)').astype(float)

# ===============================
# Step 6: Keep only required columns
# ===============================
df = df[['datetime', 'energy']]

# ===============================
# Step 7: Sort chronologically
# ===============================
df = df.sort_values('datetime').reset_index(drop=True)

# ===============================
# Step 8: Set 30-minute frequency
# ===============================
df = df.set_index('datetime').asfreq('30min')

# ===============================
# Step 9: Forward fill missing values
# ===============================
df['energy'] = df['energy'].ffill()

# ===============================
# Step 10: Save cleaned file safely
# ===============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(BASE_DIR, "outputs")
os.makedirs(output_dir, exist_ok=True)

output_path = os.path.join(output_dir, "meter2_clean.csv")
df.to_csv(output_path)

print("Meter 2 cleaned successfully.")