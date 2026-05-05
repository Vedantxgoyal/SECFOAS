# ==========================================================
# SECFAOS — STREAMLIT DASHBOARD  (fully fixed)
# Run: streamlit run dashboard.py
# ==========================================================

import os
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"]  = "3"

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import timedelta

st.set_page_config(
    page_title="SECFAOS — Smart Energy Optimization",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    div[data-testid="stMetric"] {
        background: #1e2130;
        border-radius: 10px;
        padding: 16px;
        border: 1px solid #2d3748;
    }
    .stAlert { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ── Palette ───────────────────────────────────────────────
C_ORANGE = "#e07b39"
C_BLUE   = "#3a86ff"
C_GREEN  = "#4caf82"
C_RED    = "#ef4444"
C_BG     = "#1e2130"
C_GRID   = "rgba(255,255,255,0.06)"

# ── Base layout — NO xaxis/yaxis here to avoid conflicts ──
def _layout(**kwargs):
    base = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0", size=12),
        margin=dict(l=40, r=20, t=50, b=40),
        legend=dict(orientation="h", y=1.08),
    )
    base.update(kwargs)
    return base


# ==========================================================
# PIPELINE HELPERS (duplicated from main.py — no import needed)
# ==========================================================

def _hist_profile(df, forecast_index, seasonal_period):
    forecast_dow  = forecast_index[0].dayofweek
    same_dow_days = []
    for date, group in df.groupby(df.index.date):
        if pd.Timestamp(date).dayofweek == forecast_dow and len(group) == seasonal_period:
            same_dow_days.append(group["energy"].values)
    if len(same_dow_days) >= 2:
        return np.mean(same_dow_days[-4:], axis=0)
    for date, group in reversed(list(df.groupby(df.index.date))):
        if len(group) == seasonal_period:
            return group["energy"].values
    overall = df.groupby(df.index.time)["energy"].mean()
    return np.array([overall.get(ts.time(), df["energy"].mean()) for ts in forecast_index])


def _lstm_forecast(df, result, scaler, seasonal_period):
    seq_len      = result["config"]["seq_len"]
    direct_model = result.get("direct_model")
    forecast_start = df.index[-1] + timedelta(minutes=30)
    future_index   = pd.date_range(start=forecast_start, periods=seasonal_period, freq="30min")
    hist_profile   = _hist_profile(df, future_index, seasonal_period)
    forecast_dow   = future_index[0].dayofweek
    seed_values    = None
    for date, group in reversed(list(df.groupby(df.index.date))):
        if pd.Timestamp(date).dayofweek == forecast_dow and len(group) == seasonal_period:
            seed_values = group["energy"].values[-seq_len:]
            break
    if seed_values is None:
        seed_values = df["energy"].values[-seq_len:]
    seed_scaled = scaler.transform(seed_values.reshape(-1, 1))
    X_input     = seed_scaled.reshape(1, seq_len, 1).astype(np.float32)
    pred_scaled = direct_model(X_input, training=False).numpy()
    preds_lstm  = scaler.inverse_transform(pred_scaled.reshape(-1, 1)).flatten()
    preds_lstm  = np.clip(preds_lstm, 0, None)
    blended     = 0.40 * preds_lstm + 0.60 * hist_profile
    return pd.DataFrame({"forecast_energy": np.clip(blended, 0, None)}, index=future_index)


# ==========================================================
# CACHED PIPELINE
# ==========================================================

@st.cache_resource(show_spinner=False)
def run_pipeline(data_path: str):
    from modules.data_loader   import load_data
    from modules.preprocessing import split_train_test, perform_adf_test, scale_data
    from modules.forecasting   import naive_forecast, sarima_grid_search, lstm_grid_search
    from modules.optimization  import optimize_forecast
    from modules.impact        import calculate_impact
    from modules.metrics       import (compute_peak_metrics, compute_load_factor,
                                       compute_annual_projection)
    from config import SEASONAL_PERIOD
    import config as _cfg
    _cfg.DATA_PATH = data_path

    df           = load_data()
    train, test  = split_train_test(df)
    adf          = perform_adf_test(train["energy"])
    scaler, _, _ = scale_data(train["energy"], test["energy"])
    naive_res    = naive_forecast(train, test)

    try:
        sarima_res    = sarima_grid_search(train, test)
        sarima_failed = False
    except Exception:
        sarima_res    = None
        sarima_failed = True

    try:
        lstm_res    = lstm_grid_search(train["energy"], test["energy"], scaler)
        lstm_failed = False
    except Exception:
        lstm_res    = None
        lstm_failed = True

    if lstm_failed and sarima_failed:
        selected_type  = "NAIVE"
        selected_model = None
    elif sarima_failed or (not lstm_failed and lstm_res["mae"] <= sarima_res["mae"]):
        selected_type  = "LSTM"
        selected_model = lstm_res
    else:
        selected_type  = "SARIMA"
        selected_model = sarima_res

    future_index = pd.date_range(
        start=df.index[-1] + timedelta(minutes=30),
        periods=SEASONAL_PERIOD, freq="30min"
    )

    if selected_type == "LSTM":
        future_df = _lstm_forecast(df, selected_model, scaler, SEASONAL_PERIOD)
    elif selected_type == "SARIMA":
        vals      = selected_model["model"].forecast(steps=SEASONAL_PERIOD)
        future_df = pd.DataFrame({"forecast_energy": vals.values}, index=future_index)
    else:
        profile   = _hist_profile(df, future_index, SEASONAL_PERIOD)
        future_df = pd.DataFrame({"forecast_energy": profile}, index=future_index)

    optimized_df                            = optimize_forecast(future_df)
    impact                                  = calculate_impact(optimized_df)
    peak_before, peak_after, peak_pct       = compute_peak_metrics(optimized_df)
    lf_before,   lf_after,   lf_imp        = compute_load_factor(optimized_df)
    annual_cost                             = compute_annual_projection(impact["cost_saved"])
    annual_carbon                           = compute_annual_projection(impact["carbon_saved"])

    return dict(
        df=df, train=train, test=test, adf=adf,
        naive_res=naive_res,
        sarima_res=sarima_res, sarima_failed=sarima_failed,
        lstm_res=lstm_res,     lstm_failed=lstm_failed,
        selected_type=selected_type, selected_model=selected_model,
        future_df=future_df, optimized_df=optimized_df,
        impact=impact,
        peak_before=peak_before, peak_after=peak_after, peak_pct=peak_pct,
        lf_before=lf_before,     lf_after=lf_after,     lf_imp=lf_imp,
        annual_cost=annual_cost, annual_carbon=annual_carbon,
        scaler=scaler,
        seasonal_period=SEASONAL_PERIOD,
    )


# ==========================================================
# CHART FUNCTIONS  — each calls update_xaxes/update_yaxes
# separately so there is ZERO conflict with _layout()
# ==========================================================

def _peak_shade(fig, index):
    from config import PEAK_START_HOUR, PEAK_END_HOUR
    for date in np.unique(index.date):
        fig.add_vrect(
            x0=pd.Timestamp(f"{date} {PEAK_START_HOUR:02d}:00"),
            x1=pd.Timestamp(f"{date} {PEAK_END_HOUR:02d}:00"),
            fillcolor="rgba(239,68,68,0.08)", line_width=0, layer="below"
        )


def chart_train_test(train, test):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=train.index, y=train["energy"], name="Train Set",
                             line=dict(color=C_BLUE, width=1),
                             fill="tozeroy", fillcolor="rgba(58,134,255,0.06)"))
    fig.add_trace(go.Scatter(x=test.index, y=test["energy"], name="Test Set",
                             line=dict(color=C_ORANGE, width=1),
                             fill="tozeroy", fillcolor="rgba(224,123,57,0.06)"))
    fig.add_vline(x=test.index[0], line_dash="dash",
                  line_color="rgba(255,255,255,0.4)", line_width=1.5)
    fig.update_layout(_layout(title="Energy Consumption — Train / Test Split",
                               xaxis_title="Date", yaxis_title="Energy (units)"))
    fig.update_xaxes(gridcolor=C_GRID, showgrid=True)
    fig.update_yaxes(gridcolor=C_GRID, showgrid=True)
    return fig


def chart_daily_pattern(df):
    from config import PEAK_START_HOUR, PEAK_END_HOUR
    df2      = df.copy()
    df2["h"] = df2.index.hour
    avg      = df2.groupby("h")["energy"].mean()
    std      = df2.groupby("h")["energy"].std()
    hours    = avg.index

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(hours) + list(hours[::-1]),
        y=list(avg + std) + list((avg - std)[::-1]),
        fill="toself", fillcolor="rgba(58,134,255,0.12)",
        line=dict(color="rgba(0,0,0,0)"), name="±1 Std Dev"
    ))
    fig.add_trace(go.Scatter(
        x=hours, y=avg, name="Mean Energy",
        line=dict(color=C_BLUE, width=2.5),
        mode="lines+markers", marker=dict(size=5)
    ))
    fig.add_vrect(x0=PEAK_START_HOUR, x1=PEAK_END_HOUR,
                  fillcolor="rgba(239,68,68,0.08)", line_width=0,
                  annotation_text="Peak Tariff", annotation_position="top left",
                  annotation_font_color=C_RED)
    fig.update_layout(_layout(title="Daily Average Consumption Pattern",
                               xaxis_title="Hour of Day",
                               yaxis_title="Mean Energy (units)"))
    fig.update_xaxes(tickmode="linear", tick0=0, dtick=2,
                     gridcolor=C_GRID, showgrid=True)
    fig.update_yaxes(gridcolor=C_GRID, showgrid=True)
    return fig


def chart_weekly_overview(df):
    df2        = df.copy()
    df2["dow"] = df2.index.day_name()
    day_order  = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    avg        = df2.groupby("dow")["energy"].mean().reindex(day_order)
    std        = df2.groupby("dow")["energy"].std().reindex(day_order)
    colors     = [C_BLUE]*5 + [C_ORANGE]*2

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[d[:3] for d in day_order], y=avg.values,
        error_y=dict(type="data", array=std.values, visible=True,
                     color="rgba(255,255,255,0.3)"),
        marker_color=colors, marker_opacity=0.85, name="Mean Energy",
        text=[f"{v:.4f}" for v in avg.values],
        textposition="outside", textfont=dict(size=10)
    ))
    fig.update_layout(_layout(title="Weekly Consumption Overview",
                               xaxis_title="Day of Week",
                               yaxis_title="Mean Energy (units)"))
    fig.update_xaxes(gridcolor=C_GRID, showgrid=False)
    fig.update_yaxes(gridcolor=C_GRID, showgrid=True)
    return fig


def chart_heatmap(df):
    from config import PEAK_START_HOUR, PEAK_END_HOUR
    df2         = df.copy()
    df2["hour"] = df2.index.hour
    df2["dow"]  = df2.index.day_name()
    day_order   = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    pivot       = (df2.groupby(["hour","dow"])["energy"].mean()
                      .unstack("dow").reindex(columns=day_order))

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=[d[:3] for d in day_order],
        y=[f"{h:02d}:00" for h in range(24)],
        colorscale="YlOrRd",
        colorbar=dict(title="Mean Energy", tickfont=dict(size=10)),
    ))
    fig.add_hline(y=f"{PEAK_START_HOUR:02d}:00",
                  line_dash="dash", line_color="rgba(58,134,255,0.6)", line_width=1.5)
    fig.add_hline(y=f"{PEAK_END_HOUR:02d}:00",
                  line_dash="dash", line_color="rgba(58,134,255,0.6)", line_width=1.5)
    fig.update_layout(_layout(title="Energy Heatmap — Hour of Day × Day of Week",
                               xaxis_title="Day of Week",
                               yaxis_title="Hour of Day"))
    fig.update_yaxes(autorange="reversed", gridcolor=C_GRID, showgrid=True)
    fig.update_xaxes(gridcolor=C_GRID, showgrid=False)
    return fig


def chart_forecast_comparison(test, sarima_res, lstm_res):
    sarima_preds = sarima_res["forecast"].values
    lstm_preds   = lstm_res["predictions"]
    min_len      = min(len(sarima_preds), len(lstm_preds), len(test))
    idx          = test.index[:min_len]

    fig = go.Figure()
    _peak_shade(fig, idx)
    fig.add_trace(go.Scatter(x=idx, y=test["energy"].values[:min_len],
                             name="Actual", line=dict(color="#e2e8f0", width=1.8)))
    fig.add_trace(go.Scatter(x=idx, y=sarima_preds[:min_len],
                             name=f"SARIMA (MAE={sarima_res['mae']:.4f})",
                             line=dict(color=C_ORANGE, width=1.2, dash="dash")))
    fig.add_trace(go.Scatter(x=idx, y=lstm_preds[:min_len],
                             name=f"LSTM (MAE={lstm_res['mae']:.4f})",
                             line=dict(color=C_BLUE, width=1.2, dash="dash")))
    fig.update_layout(_layout(title="Model Comparison — Test Set Forecast",
                               xaxis_title="Time", yaxis_title="Energy (units)"))
    fig.update_xaxes(gridcolor=C_GRID, showgrid=True)
    fig.update_yaxes(gridcolor=C_GRID, showgrid=True)
    return fig


def chart_optimization(optimized_df, selected_type, mae):
    fig = go.Figure()
    _peak_shade(fig, optimized_df.index)
    fig.add_trace(go.Scatter(
        x=optimized_df.index, y=optimized_df["forecast_energy"],
        name="Before Optimization", line=dict(color=C_ORANGE, width=2),
        fill="tozeroy", fillcolor="rgba(224,123,57,0.06)"
    ))
    fig.add_trace(go.Scatter(
        x=optimized_df.index, y=optimized_df["optimized_energy"],
        name="After Optimization", line=dict(color=C_BLUE, width=2),
        fill="tozeroy", fillcolor="rgba(58,134,255,0.06)"
    ))
    fig.add_trace(go.Scatter(
        x=list(optimized_df.index) + list(optimized_df.index[::-1]),
        y=list(optimized_df["forecast_energy"]) + list(optimized_df["optimized_energy"][::-1]),
        fill="toself", fillcolor="rgba(76,175,130,0.10)",
        line=dict(color="rgba(0,0,0,0)"), name="Reduction Area"
    ))
    peak_red_pct = ((optimized_df["forecast_energy"].max() -
                     optimized_df["optimized_energy"].max()) /
                    optimized_df["forecast_energy"].max() * 100)
    title = f"Optimization Impact — 24h Forecast  |  Model: {selected_type}"
    if mae:
        title += f"  |  MAE: {mae:.4f}"
    fig.update_layout(_layout(title=title,
                               xaxis_title="Time", yaxis_title="Energy (units)"))
    fig.update_xaxes(gridcolor=C_GRID, showgrid=True)
    fig.update_yaxes(gridcolor=C_GRID, showgrid=True)
    fig.add_annotation(
        text=f"Peak Reduction: {peak_red_pct:.1f}%",
        xref="paper", yref="paper", x=0.99, y=0.97,
        showarrow=False, font=dict(size=12, color=C_GREEN),
        bgcolor=C_BG, bordercolor=C_GREEN, borderwidth=1,
        borderpad=6, align="right"
    )
    return fig


def chart_peak_shaving_bars(optimized_df):
    from config import PEAK_START_HOUR, PEAK_END_HOUR
    hourly_before = optimized_df["forecast_energy"].resample("1h").mean()
    hourly_after  = optimized_df["optimized_energy"].resample("1h").mean()
    hours         = [t.strftime("%H:%M") for t in hourly_before.index]
    bar_colors    = [
        "rgba(239,68,68,0.75)" if PEAK_START_HOUR <= t.hour < PEAK_END_HOUR else C_ORANGE
        for t in hourly_before.index
    ]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=hours, y=hourly_before.values, name="Before",
                         marker_color=bar_colors, opacity=0.85))
    fig.add_trace(go.Bar(x=hours, y=hourly_after.values, name="After",
                         marker_color=C_BLUE, opacity=0.85))
    fig.update_layout(_layout(title="Peak Shaving — Hourly Energy Before vs After",
                               xaxis_title="Hour", yaxis_title="Mean Energy (units)",
                               barmode="group"))
    fig.update_xaxes(gridcolor=C_GRID, showgrid=False)
    fig.update_yaxes(gridcolor=C_GRID, showgrid=True)
    return fig


def chart_cost_breakdown(optimized_df):
    from config import PEAK_START_HOUR, PEAK_END_HOUR, PEAK_TARIFF, NORMAL_TARIFF

    def costs(col):
        pk, op = 0.0, 0.0
        for ts, row in optimized_df.iterrows():
            e = row[col]
            if PEAK_START_HOUR <= ts.hour < PEAK_END_HOUR:
                pk += e * PEAK_TARIFF
            else:
                op += e * NORMAL_TARIFF
        return pk, op

    pb, ob = costs("forecast_energy")
    pa, oa = costs("optimized_energy")
    savings = (pb + ob) - (pa + oa)

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Off-Peak Cost", x=["Before", "After"], y=[ob, oa],
                         marker_color=C_GREEN, opacity=0.88,
                         text=[f"Rs {ob:.1f}", f"Rs {oa:.1f}"],
                         textposition="inside", textfont=dict(color="white")))
    fig.add_trace(go.Bar(name="Peak Cost", x=["Before", "After"], y=[pb, pa],
                         marker_color=C_ORANGE, opacity=0.88,
                         text=[f"Rs {pb:.1f}", f"Rs {pa:.1f}"],
                         textposition="inside", textfont=dict(color="white")))
    fig.update_layout(_layout(title=f"Cost Breakdown  |  Total Saved: Rs {savings:.2f}",
                               yaxis_title="Cost (Rs)", barmode="stack"))
    fig.update_xaxes(gridcolor=C_GRID, showgrid=False)
    fig.update_yaxes(gridcolor=C_GRID, showgrid=True)
    return fig


def chart_projection(impact, annual_cost):
    months     = pd.date_range("2025-01-01", periods=12, freq="MS")
    monthly    = [impact["cost_saved"] * 30] * 12
    cumulative = np.cumsum(monthly)
    labels     = [m.strftime("%b %Y") for m in months]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=labels, y=monthly, name="Monthly Saving",
                         marker_color=C_BLUE, opacity=0.8))
    fig.add_trace(go.Scatter(x=labels, y=cumulative, name="Cumulative",
                             line=dict(color=C_GREEN, width=2.5),
                             mode="lines+markers", yaxis="y2"))
    fig.update_layout(
        _layout(title="Projected Annual Cost Savings"),
        yaxis2=dict(title="Cumulative (Rs)", overlaying="y", side="right",
                    gridcolor="rgba(0,0,0,0)", color="#e2e8f0"),
        yaxis_title="Monthly Saving (Rs)",
    )
    fig.update_xaxes(gridcolor=C_GRID, showgrid=False)
    fig.update_yaxes(gridcolor=C_GRID, showgrid=True)
    return fig


# ==========================================================
# SIDEBAR
# ==========================================================

def render_sidebar():
    st.sidebar.title("⚡ SECFAOS")
    st.sidebar.caption("Smart Energy Consumption\nForecasting & Optimization System")
    st.sidebar.divider()

    data_dir  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    csv_files = [f for f in os.listdir(data_dir) if f.endswith(".csv")] if os.path.exists(data_dir) else []

    if not csv_files:
        st.sidebar.error("No CSV files found in /data folder.")
        st.stop()

    selected_file = st.sidebar.selectbox(
        "Select Meter", csv_files,
        format_func=lambda x: x.replace("_clean.csv","").replace(".csv","").replace("_"," ").upper()
    )
    data_path = os.path.join(data_dir, selected_file)

    st.sidebar.divider()
    page = st.sidebar.radio(
        "Navigation", [
            "📊 Overview",
            "🔍 Exploratory Analysis",
            "🤖 Model Comparison",
            "🔮 Forecasting",
            "⚙️ Optimization",
            "📈 Impact & Projections",
        ]
    )
    st.sidebar.divider()
    st.sidebar.caption("LSTM + SARIMA + PuLP LP Solver")
    return data_path, page, selected_file


# ==========================================================
# PAGES
# ==========================================================

def page_overview(p):
    st.markdown("## 📊 System Overview")
    st.caption("Results based on 24-hour forecast optimization | "
               "Energy values are normalized index units (0–1 scale, single residential meter)")
    st.divider()

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Records",         f"{len(p['df']):,}")
    k2.metric("Total Consumption",     f"{p['df']['energy'].sum():.2f} idx·units")
    k3.metric("Avg Daily Consumption", f"{p['df']['energy'].resample('D').sum().mean():.4f}")
    k4.metric("Peak Slot Value",       f"{p['df']['energy'].max():.4f}")
    k5.metric("Data Period",           f"{(p['df'].index[-1]-p['df'].index[0]).days} days")

    st.divider()
    st.markdown("### ⚡ Optimization Results")
    st.caption("Optimization shifts non-critical loads from peak hours (18:00–22:00) "
               "to lower-demand periods, reducing peak stress and tariff costs.")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Energy Saved (index)",
              f"{p['impact']['energy_saved']:.4f} units",
              delta=f"+{p['impact']['energy_saved']:.4f}",
              delta_color="normal")
    c2.metric("Cost Saved (Daily)",
              f"Rs {p['impact']['cost_saved']:.2f}",
              delta=f"+Rs {p['impact']['cost_saved']:.2f}",
              delta_color="normal")
    c3.metric("Peak Reduction",
              f"{p['peak_pct']:.1f}%",
              delta=f"+{p['peak_pct']:.1f}% reduction",
              delta_color="normal")
    c4.metric("Load Factor Improvement",
              f"{p['lf_imp']:.2f}%",
              delta=f"{p['lf_imp']:+.2f}%",
              delta_color="normal")

    st.divider()
    st.markdown("### 📉 Peak Load Comparison")
    pb1, pb2, pb3 = st.columns(3)
    pb1.metric("Peak Before Optimization", f"{p['peak_before']:.4f} units")
    pb2.metric("Peak After Optimization",  f"{p['peak_after']:.4f} units",
               delta=f"{p['peak_after'] - p['peak_before']:.4f}",
               delta_color="inverse")
    pb3.metric("Peak Reduction",           f"{p['peak_pct']:.2f}%",
               delta=f"+{p['peak_pct']:.2f}% improved",
               delta_color="normal")

    st.divider()
    st.markdown("### 🤖 Selected Model")
    m1, m2, m3 = st.columns(3)
    m1.metric("Model",    p["selected_type"])
    mae = p["selected_model"]["mae"] if p["selected_model"] else None
    m2.metric("MAE",      f"{mae:.4f}" if mae else "N/A")
    m3.metric("ADF Test", "✅ Stationary" if p["adf"]["Is Stationary"] else "❌ Non-Stationary")

    st.divider()
    st.markdown("### 📅 Annual Projections")
    st.caption("Extrapolated from 24-hour optimized savings × 365 days")
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Annual Cost Saving",       f"Rs {p['annual_cost']:,.2f}",
              delta=f"+Rs {p['annual_cost']:,.0f}/yr", delta_color="normal")
    a2.metric("Annual Carbon Reduction",  f"{p['annual_carbon']:,.2f} kg CO₂",
              delta=f"-{p['annual_carbon']:,.2f} kg", delta_color="inverse")
    a3.metric("Equivalent Trees Planted", f"{p['annual_carbon']/21:.0f} trees/year")
    a4.metric("Monthly Cost Saving",      f"Rs {p['annual_cost']/12:,.2f}")


def page_eda(p):
    st.markdown("## 🔍 Exploratory Data Analysis")
    st.divider()
    tab1, tab2, tab3, tab4 = st.tabs([
        "📉 Train / Test Split", "🕐 Daily Pattern",
        "📅 Weekly Overview",    "🌡️ Heatmap"
    ])
    with tab1:
        st.plotly_chart(chart_train_test(p["train"], p["test"]), use_container_width=True)
        c1, c2 = st.columns(2)
        c1.info(f"**Train**  n={len(p['train'])}  mean={p['train']['energy'].mean():.4f}  std={p['train']['energy'].std():.4f}")
        c2.info(f"**Test**   n={len(p['test'])}   mean={p['test']['energy'].mean():.4f}  std={p['test']['energy'].std():.4f}")
    with tab2:
        st.plotly_chart(chart_daily_pattern(p["df"]), use_container_width=True)
    with tab3:
        st.plotly_chart(chart_weekly_overview(p["df"]), use_container_width=True)
    with tab4:
        st.plotly_chart(chart_heatmap(p["df"]), use_container_width=True)


def page_models(p):
    st.markdown("## 🤖 Model Comparison")
    st.divider()

    rows = [{"Model": "Naive (Baseline)",
             "MAE":  f"{p['naive_res']['mae']:.4f}",
             "RMSE": f"{p['naive_res']['rmse']:.4f}",
             "Status": "✅", "Selected": ""}]

    if not p["sarima_failed"]:
        rows.append({
            "Model":    f"SARIMA {p['sarima_res']['order']} × {p['sarima_res']['seasonal_order']}",
            "MAE":      f"{p['sarima_res']['mae']:.4f}",
            "RMSE":     f"{p['sarima_res']['rmse']:.4f}",
            "Status":   "✅",
            "Selected": "⬅ Selected" if p["selected_type"] == "SARIMA" else ""
        })
    else:
        rows.append({"Model": "SARIMA", "MAE": "—", "RMSE": "—",
                     "Status": "❌ Failed", "Selected": ""})

    if not p["lstm_failed"]:
        cfg = p["lstm_res"]["config"]
        rows.append({
            "Model":    f"LSTM units={cfg['units']} seq={cfg['seq_len']} dropout={cfg['dropout']}",
            "MAE":      f"{p['lstm_res']['mae']:.4f}",
            "RMSE":     "—",
            "Status":   "✅",
            "Selected": "⬅ Selected" if p["selected_type"] == "LSTM" else ""
        })
    else:
        rows.append({"Model": "LSTM", "MAE": "—", "RMSE": "—",
                     "Status": "❌ Failed", "Selected": ""})

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.divider()

    if not p["sarima_failed"] and not p["lstm_failed"]:
        st.plotly_chart(
            chart_forecast_comparison(p["test"], p["sarima_res"], p["lstm_res"]),
            use_container_width=True
        )
    else:
        st.warning("Both SARIMA and LSTM needed to render comparison chart.")

    if not p["lstm_failed"]:
        st.divider()
        st.markdown("### LSTM Architecture")
        cfg = p["lstm_res"]["config"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Units per Layer", cfg["units"])
        c2.metric("Dropout",         cfg["dropout"])
        c3.metric("Learning Rate",   cfg["lr"])
        c4.metric("Sequence Length", f"{cfg['seq_len']} slots (12h)")


def page_optimization(p):
    st.markdown("## ⚙️ Optimization")
    st.divider()
    mae = p["selected_model"]["mae"] if p["selected_model"] else None

    tab1, tab2, tab3 = st.tabs(["📈 Before vs After", "📊 Hourly Bars", "💰 Cost Breakdown"])
    with tab1:
        st.plotly_chart(
            chart_optimization(p["optimized_df"], p["selected_type"], mae),
            use_container_width=True
        )
        opt = (p["optimized_df"]["optimizer_used"].iloc[0]
               if "optimizer_used" in p["optimized_df"].columns else "LP")
        st.info(f"**Solver:** {opt}  |  **Peak cap:** 75th pct  |  "
                f"**Flexible load:** 25%  |  **λ:** 0.5")
    with tab2:
        st.plotly_chart(chart_peak_shaving_bars(p["optimized_df"]), use_container_width=True)
    with tab3:
        st.plotly_chart(chart_cost_breakdown(p["optimized_df"]), use_container_width=True)

    st.divider()
    st.markdown("### Forecast Data Table")
    st.dataframe(
        p["optimized_df"][["forecast_energy","optimized_energy"]]
          .rename(columns={"forecast_energy": "Before (units)",
                            "optimized_energy": "After (units)"})
          .style.format("{:.4f}"),
        use_container_width=True, height=280
    )


def page_impact(p):
    st.markdown("## 📈 Impact & Projections")
    st.divider()

    st.markdown("### Daily Impact")
    d1, d2, d3 = st.columns(3)
    d1.metric("Energy Saved",  f"{p['impact']['energy_saved']:.4f} units")
    d2.metric("Cost Saved",    f"Rs {p['impact']['cost_saved']:.2f}")
    d3.metric("Carbon Saved",  f"{p['impact']['carbon_saved']:.4f} kg CO₂")

    st.divider()
    st.markdown("### Peak & Load Factor")
    p1, p2, p3, p4, p5 = st.columns(5)
    p1.metric("Peak Before",         f"{p['peak_before']:.4f}")
    p2.metric("Peak After",          f"{p['peak_after']:.4f}")
    p3.metric("Peak Reduction",      f"{p['peak_pct']:.2f}%", delta=f"-{p['peak_pct']:.2f}%")
    p4.metric("Load Factor Before",  f"{p['lf_before']:.4f}")
    p5.metric("Load Factor After",   f"{p['lf_after']:.4f}",
              delta=f"{p['lf_imp']:+.2f}%")

    st.divider()
    st.markdown("### Annual Projections")
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Annual Cost Saving",      f"Rs {p['annual_cost']:,.2f}")
    a2.metric("Annual Carbon Reduction", f"{p['annual_carbon']:,.2f} kg CO₂")
    a3.metric("Equivalent Trees",        f"{p['annual_carbon']/21:.0f} trees")
    a4.metric("Monthly Cost Saving",     f"Rs {p['annual_cost']/12:,.2f}")

    st.divider()
    st.markdown("### 12-Month Cost Saving Projection")
    st.plotly_chart(chart_projection(p["impact"], p["annual_cost"]),
                    use_container_width=True)



def page_forecast(p):
    st.markdown("## 🔮 24-Hour Energy Forecast")
    st.caption("Forecast generated using the best-selected model. "
               "Blended: 40% LSTM direct prediction + 60% historical same-day profile.")
    st.divider()

    # ── Forecast summary metrics ──────────────────────────
    fdf = p["future_df"]
    f1, f2, f3, f4 = st.columns(4)
    f1.metric("Forecast Mean",   f"{fdf['forecast_energy'].mean():.4f} units")
    f2.metric("Forecast Peak",   f"{fdf['forecast_energy'].max():.4f} units")
    f3.metric("Forecast Min",    f"{fdf['forecast_energy'].min():.4f} units")
    f4.metric("Forecast Std Dev",f"{fdf['forecast_energy'].std():.4f}",
              delta="low variance — low-activity period" if fdf['forecast_energy'].std() < 0.03 else None,
              delta_color="off")

    st.divider()

    # ── Forecast curve chart ──────────────────────────────
    fig = go.Figure()
    _peak_shade(fig, fdf.index)

    # Confidence band (±1 std simulated — visual only)
    std = fdf["forecast_energy"].std()
    upper = (fdf["forecast_energy"] + std).clip(upper=1.0)
    lower = (fdf["forecast_energy"] - std).clip(lower=0.0)
    fig.add_trace(go.Scatter(
        x=list(fdf.index) + list(fdf.index[::-1]),
        y=list(upper) + list(lower[::-1]),
        fill="toself", fillcolor="rgba(58,134,255,0.10)",
        line=dict(color="rgba(0,0,0,0)"), name="±1 Std Band",
    ))
    fig.add_trace(go.Scatter(
        x=fdf.index, y=fdf["forecast_energy"],
        name=f"Forecast ({p['selected_type']})",
        line=dict(color=C_BLUE, width=2.5),
        mode="lines",
    ))
    # Mark peak slot
    peak_idx = fdf["forecast_energy"].idxmax()
    fig.add_trace(go.Scatter(
        x=[peak_idx], y=[fdf["forecast_energy"].max()],
        mode="markers", marker=dict(color=C_RED, size=10, symbol="star"),
        name=f"Peak: {fdf['forecast_energy'].max():.4f}"
    ))
    fig.update_layout(_layout(
        title=f"24-Hour Energy Forecast  |  Model: {p['selected_type']}  |  "
              f"MAE: {p['selected_model']['mae']:.4f}" if p['selected_model'] else
              f"24-Hour Energy Forecast  |  Model: {p['selected_type']}",
        xaxis_title="Time", yaxis_title="Energy (normalized index units)"
    ))
    fig.update_xaxes(gridcolor=C_GRID, showgrid=True)
    fig.update_yaxes(gridcolor=C_GRID, showgrid=True)
    st.plotly_chart(fig, use_container_width=True)

    st.caption("🔴 Shaded region = Peak tariff hours (18:00–22:00) | "
               "⭐ Star marker = Forecast peak slot | "
               "Blue band = ±1 std dev confidence range")

    st.divider()

    # ── Hourly forecast bar chart ─────────────────────────
    st.markdown("### Hourly Forecast Breakdown")
    from config import PEAK_START_HOUR, PEAK_END_HOUR
    hourly = fdf["forecast_energy"].resample("1h").mean()
    bar_colors = [
        "rgba(239,68,68,0.75)" if PEAK_START_HOUR <= t.hour < PEAK_END_HOUR else C_BLUE
        for t in hourly.index
    ]
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=[t.strftime("%H:%M") for t in hourly.index],
        y=hourly.values,
        marker_color=bar_colors, opacity=0.85,
        text=[f"{v:.4f}" for v in hourly.values],
        textposition="outside", textfont=dict(size=9),
        name="Hourly Mean Forecast"
    ))
    fig2.update_layout(_layout(
        title="Hourly Mean Forecast  |  Red bars = Peak tariff window",
        xaxis_title="Hour", yaxis_title="Mean Energy (units)"
    ))
    fig2.update_xaxes(gridcolor=C_GRID, showgrid=False)
    fig2.update_yaxes(gridcolor=C_GRID, showgrid=True)
    st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # ── Raw forecast table ────────────────────────────────
    st.markdown("### Forecast Data Table")
    display_df = fdf.copy()
    display_df.index = display_df.index.strftime("%Y-%m-%d %H:%M")
    display_df.columns = ["Forecast Energy (units)"]
    st.dataframe(display_df.style.format("{:.4f}"),
                 use_container_width=True, height=300)

# ==========================================================
# MAIN
# ==========================================================

def main():
    data_path, page, selected_file = render_sidebar()

    meter_id = (selected_file.replace("_clean.csv","")
                             .replace(".csv","")
                             .replace("_"," ").upper())
    st.markdown(f"# ⚡ SECFAOS — {meter_id}")

    with st.spinner("⚙️ Running pipeline — training models, optimizing..."):
        try:
            p = run_pipeline(data_path)
        except Exception as e:
            st.error(f"Pipeline failed: {e}")
            st.exception(e)
            st.stop()

    opt_used = (p["optimized_df"]["optimizer_used"].iloc[0]
                if "optimizer_used" in p["optimized_df"].columns else "LP")
    st.success(f"✅ Pipeline complete — Model: **{p['selected_type']}**  "
               f"|  Optimizer: **{opt_used}**")

    if page == "📊 Overview":
        page_overview(p)
    elif page == "🔍 Exploratory Analysis":
        page_eda(p)
    elif page == "🤖 Model Comparison":
        page_models(p)
    elif page == "🔮 Forecasting":
        page_forecast(p)
    elif page == "⚙️ Optimization":
        page_optimization(p)
    elif page == "📈 Impact & Projections":
        page_impact(p)


if __name__ == "__main__":
    main()