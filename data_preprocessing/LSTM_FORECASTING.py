import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense

# ==========================================
# Step 1: Load cleaned Meter 2 dataset
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(BASE_DIR, "outputs", "meter2_clean.csv")

df = pd.read_csv(data_path, parse_dates=['datetime'])
df = df.set_index('datetime')
df = df.asfreq('30min')

data = df['energy'].values.reshape(-1,1)

# ==========================================
# Step 2: Normalize data
# ==========================================
scaler = MinMaxScaler()
data_scaled = scaler.fit_transform(data)

# ==========================================
# Step 3: Create sequences (48 time steps = 1 day)
# ==========================================
sequence_length = 48

X = []
y = []

for i in range(sequence_length, len(data_scaled)):
    X.append(data_scaled[i-sequence_length:i])
    y.append(data_scaled[i])

X = np.array(X)
y = np.array(y)

# ==========================================
# Step 4: Train-Test Split
# ==========================================
train_size = int(len(X) * 0.8)

X_train, X_test = X[:train_size], X[train_size:]
y_train, y_test = y[:train_size], y[train_size:]

# ==========================================
# Step 5: Build LSTM Model
# ==========================================
model = Sequential()
model.add(LSTM(50, activation='relu', input_shape=(X_train.shape[1], 1)))
model.add(Dense(1))

model.compile(optimizer='adam', loss='mse')

print("Training LSTM model...")
model.fit(X_train, y_train, epochs=20, batch_size=32, verbose=1)

# ==========================================
# Step 6: Predictions
# ==========================================
predictions = model.predict(X_test)

# Inverse scale
predictions = scaler.inverse_transform(predictions)
y_test_actual = scaler.inverse_transform(y_test)

# ==========================================
# Step 7: Evaluation
# ==========================================
mae = mean_absolute_error(y_test_actual, predictions)
rmse = np.sqrt(mean_squared_error(y_test_actual, predictions))

print("LSTM MAE:", round(mae,4))
print("LSTM RMSE:", round(rmse,4))

# ==========================================
# Step 8: Plot Results
# ==========================================
plt.figure(figsize=(12,5))
plt.plot(y_test_actual, label="Actual")
plt.plot(predictions, label="LSTM Forecast")
plt.title("LSTM Forecast - Meter 2")
plt.legend()
plt.tight_layout()

plot_path = os.path.join(BASE_DIR, "outputs", "meter2_lstm_forecast.png")
plt.savefig(plot_path)

plt.show()

print("LSTM Forecasting Complete.")