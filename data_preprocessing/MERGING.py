import pandas as pd
import os
import matplotlib.pyplot as plt

# ==========================================
# Step 1: Define project paths safely
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(BASE_DIR, "outputs")

meter1_path = os.path.join(output_dir, "meter1_clean.csv")
meter2_path = os.path.join(output_dir, "meter2_clean.csv")
meter3_path = os.path.join(output_dir, "meter3_clean.csv")

# ==========================================
# Step 2: Load cleaned datasets
# ==========================================
m1 = pd.read_csv(meter1_path, parse_dates=['datetime'])
m2 = pd.read_csv(meter2_path, parse_dates=['datetime'])
m3 = pd.read_csv(meter3_path, parse_dates=['datetime'])

# Rename energy columns to distinguish
m1 = m1.rename(columns={'energy': 'meter1'})
m2 = m2.rename(columns={'energy': 'meter2'})
m3 = m3.rename(columns={'energy': 'meter3'})

# ==========================================
# Step 3: Merge on datetime (inner join)
# ==========================================
merged = m1.merge(m2, on='datetime', how='inner')
merged = merged.merge(m3, on='datetime', how='inner')

# ==========================================
# Step 4: Create Total Load
# ==========================================
merged['total_load'] = merged['meter1'] + merged['meter2'] + merged['meter3']

# ==========================================
# Step 5: Sort chronologically
# ==========================================
merged = merged.sort_values('datetime').reset_index(drop=True)

# ==========================================
# Step 6: Save final dataset
# ==========================================
final_path = os.path.join(output_dir, "final_merged_dataset.csv")
merged.to_csv(final_path, index=False)

print("Merged dataset created successfully.")
print("Total rows:", len(merged))

# ==========================================
# Step 7: Plot total load
# ==========================================
plt.figure(figsize=(12,5))
plt.plot(merged['datetime'], merged['total_load'])
plt.title("Total Energy Consumption")
plt.xlabel("Datetime")
plt.ylabel("Total Load (kWh)")
plt.tight_layout()

plot_path = os.path.join(output_dir, "total_load_plot.png")
plt.savefig(plot_path)

plt.show()