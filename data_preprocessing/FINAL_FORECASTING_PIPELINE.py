import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from statsmodels.tsa.statespace.sarimax import SARIMAX
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense

# ==========================================================
# CONFIGURATION
# ==========================================================
NORMAL_TARIFF = 8          # ₹ per kWh
PEAK_TARIFF = 12           # ₹ per kWh (peak hours)
CARBON_FACTOR = 0.82       # kg CO2 per kWh
SEASONAL_PERIOD = 48       # 30-min intervals/day

# ==========================================================
# LOAD DATA
# ==========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(BASE_DIR, "outputs", "meter2_clean.csv")

df = pd.read_csv(data_path, parse_dates=['datetime'])
df = df.set_index('datetime')
df = df.asfreq('30min')

print("Dataset Loaded:", len(df), "rows")

# ==========================================================
# TRAIN TEST SPLIT
# ==========================================================
train_size = int(len(df)*0.8)
train = df.iloc[:train_size]
test = df.iloc[train_size:]

# ==========================================================
# SARIMA
# ==========================================================
sarima = SARIMAX(
    train['energy'],
    order=(1,1,1),
    seasonal_order=(1,1,1,SEASONAL_PERIOD),
    enforce_stationarity=False,
    enforce_invertibility=False
)

sarima_fit = sarima.fit(disp=False)
sarima_forecast = sarima_fit.forecast(steps=len(test))

sarima_mae = mean_absolute_error(test['energy'], sarima_forecast)
sarima_rmse = np.sqrt(mean_squared_error(test['energy'], sarima_forecast))

print("\nSARIMA MAE:", round(sarima_mae,4))
print("SARIMA RMSE:", round(sarima_rmse,4))

# ==========================================================
# LSTM
# ==========================================================
data = df['energy'].values.reshape(-1,1)

scaler = MinMaxScaler()
data_scaled = scaler.fit_transform(data)

sequence_length = SEASONAL_PERIOD

X, y = [], []
for i in range(sequence_length, len(data_scaled)):
    X.append(data_scaled[i-sequence_length:i])
    y.append(data_scaled[i])

X = np.array(X)
y = np.array(y)

train_size_lstm = train_size - sequence_length

X_train = X[:train_size_lstm]
X_test = X[train_size_lstm:]

y_train = y[:train_size_lstm]
y_test = y[train_size_lstm:]

model = Sequential()
model.add(LSTM(64, return_sequences=True, input_shape=(sequence_length,1)))
model.add(LSTM(32))
model.add(Dense(16, activation='relu'))
model.add(Dense(1))

model.compile(optimizer='adam', loss='mse')

print("\nTraining LSTM...")
model.fit(X_train, y_train, epochs=30, batch_size=32, verbose=0)

lstm_pred = model.predict(X_test)
lstm_pred = scaler.inverse_transform(lstm_pred)
y_test_actual = scaler.inverse_transform(y_test)

lstm_mae = mean_absolute_error(y_test_actual, lstm_pred)
lstm_rmse = np.sqrt(mean_squared_error(y_test_actual, lstm_pred))

print("LSTM MAE:", round(lstm_mae,4))
print("LSTM RMSE:", round(lstm_rmse,4))

# ==========================================================
# 24-HOUR FUTURE FORECAST
# ==========================================================
future_steps = SEASONAL_PERIOD
last_sequence = data_scaled[-sequence_length:]

future_predictions = []
current_seq = last_sequence.copy()

for _ in range(future_steps):
    pred = model.predict(current_seq.reshape(1,sequence_length,1), verbose=0)
    future_predictions.append(pred[0][0])
    current_seq = np.append(current_seq[1:], pred).reshape(sequence_length,1)

future_predictions = scaler.inverse_transform(
    np.array(future_predictions).reshape(-1,1)
)

last_datetime = df.index[-1]
future_dates = pd.date_range(
    start=last_datetime + pd.Timedelta(minutes=30),
    periods=future_steps,
    freq='30min'
)

future_df = pd.DataFrame({
    'datetime': future_dates,
    'forecast_energy': future_predictions.flatten()
})

# ==========================================================
# PEAK DETECTION
# ==========================================================
threshold = future_df['forecast_energy'].quantile(0.90)
future_df['is_peak'] = future_df['forecast_energy'] > threshold

# ==========================================================
# OPTIMIZATION (REAL REDUCTION + SHIFT)
# ==========================================================
optimized = future_df['forecast_energy'].astype(float).copy()

for i in range(len(future_df)):
    if future_df.loc[i,'is_peak']:
        total_reduction = 0.2 * optimized[i]   # 20% reduction
        shift_amount = 0.1 * optimized[i]     # shift 10%
        save_amount = total_reduction - shift_amount  # 10% permanently saved
        
        optimized[i] -= total_reduction
        
        if i+1 < len(future_df):
            optimized[i+1] += shift_amount

future_df['optimized_load'] = optimized

# ==========================================================
# COST & CARBON CALCULATION
# ==========================================================
cost_before = 0
cost_after = 0

for i in range(len(future_df)):
    if future_df.loc[i,'is_peak']:
        cost_before += future_df.loc[i,'forecast_energy'] * PEAK_TARIFF
        cost_after += future_df.loc[i,'optimized_load'] * PEAK_TARIFF
    else:
        cost_before += future_df.loc[i,'forecast_energy'] * NORMAL_TARIFF
        cost_after += future_df.loc[i,'optimized_load'] * NORMAL_TARIFF

energy_before = future_df['forecast_energy'].sum()
energy_after = future_df['optimized_load'].sum()

carbon_before = energy_before * CARBON_FACTOR
carbon_after = energy_after * CARBON_FACTOR

print("\n----- FINAL IMPACT ANALYSIS -----")
print("Energy Before (kWh):", round(energy_before,2))
print("Energy After (kWh):", round(energy_after,2))
print("Energy Saved (kWh):", round(energy_before - energy_after,2))

print("\nCost Before (₹):", round(cost_before,2))
print("Cost After (₹):", round(cost_after,2))
print("Cost Savings (₹):", round(cost_before - cost_after,2))

print("\nCarbon Before (kg CO2):", round(carbon_before,2))
print("Carbon After (kg CO2):", round(carbon_after,2))
print("Carbon Reduction (kg CO2):", round(carbon_before - carbon_after,2))

# ==========================================================
# VISUALIZATION
# ==========================================================
plt.figure(figsize=(12,5))
plt.plot(future_df['datetime'], future_df['forecast_energy'], label="Forecast")
plt.plot(future_df['datetime'], future_df['optimized_load'], label="Optimized")
plt.legend()
plt.title("24-Hour Forecast with Real Optimization")
plt.tight_layout()
plt.show()

print("\nSYSTEM COMPLETE.")
