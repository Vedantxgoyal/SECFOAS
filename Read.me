# SECFAOS — Smart Energy Consumption Forecasting & Optimisation System

> End-to-end residential smart meter pipeline: LSTM forecasting · LP optimisation · Device scheduling · React dashboard

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.136-green)
![React](https://img.shields.io/badge/React-18-61dafb)
![TensorFlow](https://img.shields.io/badge/TensorFlow-2.x-orange)
![PuLP](https://img.shields.io/badge/PuLP-CBC-yellow)

---

## Overview

SECFAOS is a production-grade smart energy management system built on real BSES Delhi smart meter data. It forecasts the next 24 hours of residential energy consumption using an LSTM neural network, then applies Linear Programming to automatically reschedule flexible loads away from expensive peak-tariff hours — reducing cost, peak demand, and carbon emissions simultaneously.

**Key Results:**

| Metric | Value |
|---|---|
| Meters | 11 real BSES Delhi meters |
| Total Records | 9,629 at 30-min intervals |
| LSTM MAE | 0.0576 (58% better than SARIMA) |
| Peak Reduction | 8.27% |
| Annual Cost Saving | Rs 10,378 per meter |
| Annual Carbon Saved | 905 kg CO₂ (≈ 43 trees) |
| Devices Scheduled | EV Charger · Water Heater · Washing Machine · AC |

---

## Architecture

```
SECFAOS/
├── api/                        # FastAPI backend
│   ├── main.py                 # CORS, router registration
│   ├── schemas.py              # Pydantic response models
│   └── routes/
│       └── pipeline.py         # /api/pipeline/run · /refresh · /meters
├── modules/                    # Core pipeline modules
│   ├── data_loader.py          # Multi-meter CSV ingestion + merge
│   ├── preprocessing.py        # ADF test · MinMaxScaler · train/test split
│   ├── forecasting.py          # Naive · SARIMA · LSTM grid search + persistence
│   ├── optimization.py         # Generic LP + device-level binary LP (PuLP/CBC)
│   ├── impact.py               # Cost · carbon · energy savings
│   ├── metrics.py              # Peak metrics · load factor · annual projection
│   ├── carbon_model.py         # CEA-aligned 24-hour carbon intensity profile
│   └── visualization.py        # 8 matplotlib output plots
├── frontend/                   # React + Vite + Tailwind + Recharts
│   └── src/
│       ├── pages/              # Overview · Forecast · Optimization · Devices · Models · EDA · Impact
│       ├── components/         # KPICard · GaugeRing · StatBar · Sidebar
│       ├── hooks/              # usePipeline.js
│       └── api/                # client.js
├── data/                       # 11 cleaned meter CSVs (meter1–meter11)
├── models/                     # Saved LSTM models (auto-generated on first run)
├── config.py                   # All system constants
├── main.py                     # CLI pipeline runner
├── scheduler.py                # APScheduler — 24-hour auto-run
├── run.py                      # Single command to start backend + frontend
└── dashboard.py                # Legacy Streamlit dashboard
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Forecasting | TensorFlow/Keras LSTM · statsmodels SARIMA |
| Optimisation | PuLP + CBC open-source LP solver |
| Backend API | FastAPI + Uvicorn |
| Frontend | React 18 + Vite + Tailwind + Recharts |
| Gauges | react-circular-progressbar |
| Scheduler | APScheduler |
| Data | pandas · numpy · scikit-learn |
| Visualisation | matplotlib · Plotly (Streamlit) |

---

## Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- pip

### 1. Clone and install Python dependencies

```bash
git clone https://github.com/yourusername/SECFAOS.git
cd SECFAOS
pip install -r requirements.txt
```

### 2. Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### 3. Add meter data

Place your cleaned meter CSV files in `data/`:

```
data/
├── meter1_clean.csv
├── meter2_clean.csv
...
└── meter11_clean.csv
```

Each CSV must have columns: `timestamp` (or `datetime`) and `energy` (normalised 0–1).

### 4. Run

```bash
python run.py
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- API docs: `http://localhost:8000/docs`

---

## Requirements

Create `requirements.txt` in project root:

```
fastapi==0.136.1
uvicorn==0.46.0
python-multipart==0.0.26
tensorflow>=2.10
statsmodels>=0.14
scikit-learn>=1.3
pandas>=2.0
numpy>=1.24
pulp>=2.7
matplotlib>=3.7
streamlit>=1.30
plotly>=5.18
apscheduler>=3.10
```

---

## Usage

### Run full pipeline (CLI)

```bash
python main.py
```

### Start live scheduler (24-hour auto-run)

```bash
python scheduler.py
```

### Force retrain LSTM

In `main.py` change:

```python
lstm_result = lstm_grid_search(train["energy"], test["energy"], scaler, force_retrain=True)
```

### Add new meter data

1. Drop new `meterN_clean.csv` into `data/`
2. Add filename to `METER_FILES` in `config.py`
3. Run with `force_retrain=True`

### Refresh dashboard without retraining

```
GET http://localhost:8000/api/pipeline/refresh
```

---

## Pipeline Flow

```
Raw CSV files (11 meters)
↓
data_loader.py — load · validate · concat · resample 30min
↓
preprocessing.py — ADF test · 80/20 split · MinMaxScaler
↓
forecasting.py — Naive · SARIMA(1,0,1)×(1,0,1,48) · LSTM grid search
↓
Auto-select best model by MAE on test set → LSTM (MAE 0.0576)
↓
Generate 48-slot forecast — 40% LSTM + 60% historical profile blend
↓
optimization.py — LP (PuLP/CBC) · 4 constraints · device binary LP
↓
impact.py · metrics.py · carbon_model.py — quantify savings
↓
FastAPI → React dashboard (7 pages · interactive charts · gauges)
```

---

## LP Optimisation

**Objective:** Minimise Σ (tariff[t] + λ × carbon[t]) × load[t] over 48 slots

**Constraints:**

1. Total demand within ±15% of forecast
2. No slot ever exceeds original forecast global maximum
3. Peak slots (18:00–22:00) never upshifted
4. Cheap slots (00:00–06:00, 10:00–16:00) allow 25% upshift

**Device LP:** Binary start variable per appliance — selects cheapest valid start slot within allowed window, never during peak hours.

---

## Carbon Model

Based on CEA CO₂ Baseline Database v18 (2023) — 0.82 kg CO₂/kWh national average.  
24-hour dispatch profile reflects Indian grid mix: solar midday dip (0.67–0.68), evening peak spike (0.92–0.93), coal baseload night (0.78–0.81).

---

## Dataset

Real BSES Rajdhani Power Ltd. smart meter data, Delhi, India.

- 11 meters across multiple periods (2023–2026)
- 30-minute interval readings
- Pre-normalised consumption index (0–1 scale)
- Combined: 9,629 records · std 0.1901 · mean 0.337

---

## Network Access (Expose Frontend on LAN)

To access the dashboard from other devices on your network, update `frontend/vite.config.js`:

```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: true,        // exposes on all network interfaces
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})
```

Then run:

```bash
cd frontend
npm run dev
```

You'll see:

```
  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.x.x:5173/
```

---

## Team

| Name | Roll No | Module |
|---|---|---|
| Vedant Goyal | 500119726 | System architecture · LP optimisation · Full-stack |
| Mudit Rana | 500120165 | Forecasting · EDA · LSTM training |
| Rishabh Matta | 500121425 | Model evaluation · Metrics · Visualisation |
| Dhiren Batra | 500119122 | Data pipeline · Device scheduling · Impact |

**Guide:** Dr. Subhranil Das, School of Computer Science, UPES Dehradun

---

## License

Academic project — UPES Dehradun, B.Tech CSE (Data Science), 2026.
