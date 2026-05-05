import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from statsmodels.tsa.statespace.sarimax import SARIMAX
from sklearn.metrics import mean_absolute_error, mean_squared_error

# ==========================================
# Step 1: Load cleaned Meter 2 dataset
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(BASE_DIR, "outputs", "meter2_clean.csv")

df = pd.read_csv(data_path, parse_dates=['datetime'])

# Set datetime as index
df = df.set_index('datetime')

print("Dataset Loaded Successfully")
print("Total rows:", len(df))

# ==========================================
# Step 2: Train-Test Split (80-20)
# ==========================================
train_size = int(len(df) * 0.8)

train = df.iloc[:train_size]
test = df.iloc[train_size:]

print("Training rows:", len(train))
print("Testing rows:", len(test))

# ==========================================
# Step 3: Define SARIMA Model
# (Daily seasonality → 30min data → 48 points per day)
# ==========================================

model = SARIMAX(
    train['energy'],
    order=(1, 1, 1),
    seasonal_order=(1, 1, 1, 48),
    enforce_stationarity=False,
    enforce_invertibility=False
)

model_fit = model.fit(disp=False)

print("SARIMA Model Trained")

# ==========================================
# Step 4: Forecast
# ==========================================
forecast = model_fit.forecast(steps=len(test))

# ==========================================
# Step 5: Evaluation Metrics
# ==========================================
mae = mean_absolute_error(test['energy'], forecast)
rmse = np.sqrt(mean_squared_error(test['energy'], forecast))

print("MAE:", round(mae, 4))
print("RMSE:", round(rmse, 4))

# ==========================================
# Step 6: Plot Actual vs Forecast
# ==========================================
plt.figure(figsize=(12,5))
plt.plot(test.index, test['energy'], label="Actual")
plt.plot(test.index, forecast, label="Forecast", linestyle='--')
plt.title("SARIMA Forecast - Meter 2")
plt.xlabel("Datetime")
plt.ylabel("Energy (kWh)")
plt.legend()
plt.tight_layout()

plot_path = os.path.join(BASE_DIR, "outputs", "meter2_forecast.png")
plt.savefig(plot_path)

plt.show()

print("Forecasting Complete.")