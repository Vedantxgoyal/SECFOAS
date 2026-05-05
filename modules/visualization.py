# ==========================================================
# VISUALIZATION MODULE - SECFAOS
# ==========================================================

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
from config import PEAK_START_HOUR, PEAK_END_HOUR, NORMAL_TARIFF, PEAK_TARIFF


def _shade_peak_hours(ax, index):
    """Shade peak tariff hours on a time-series axis."""
    dates = np.unique(index.date)
    for date in dates:
        peak_start = date.strftime(f"%Y-%m-%d {PEAK_START_HOUR:02d}:00:00")
        peak_end   = date.strftime(f"%Y-%m-%d {PEAK_END_HOUR:02d}:00:00")
        ax.axvspan(peak_start, peak_end, alpha=0.08, color="red", label="_nolegend_")


# ----------------------------------------------------------
# PLOT 1 — Model Comparison (Test Set)
# ----------------------------------------------------------

def plot_forecast(test_index, actual, sarima_pred, lstm_pred,
                  sarima_mae=None, lstm_mae=None, selected_model=None):
    fig, ax = plt.subplots(figsize=(14, 6))

    ax.plot(test_index, actual,      color="#2c2c2c", linewidth=1.5, label="Actual",  zorder=3)
    ax.plot(test_index, sarima_pred, color="#e07b39", linewidth=1.2, linestyle="--",
            label=f"SARIMA  (MAE={sarima_mae:.4f})" if sarima_mae else "SARIMA", zorder=2)
    ax.plot(test_index, lstm_pred,   color="#3a86ff", linewidth=1.2, linestyle="--",
            label=f"LSTM    (MAE={lstm_mae:.4f})"   if lstm_mae   else "LSTM",   zorder=2)

    _shade_peak_hours(ax, test_index)

    peak_patch = mpatches.Patch(color="red", alpha=0.15,
                                label=f"Peak Hours ({PEAK_START_HOUR}:00-{PEAK_END_HOUR}:00)")
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles=handles + [peak_patch], fontsize=9, loc="upper left")

    subtitle = f"Selected Model: {selected_model}" if selected_model else ""
    ax.set_title("Model Comparison — Test Set Forecast", fontsize=13, fontweight="bold", pad=10)
    if subtitle:
        ax.set_xlabel(
            f"Time                                                         [{subtitle}]",
            fontsize=9
        )
    else:
        ax.set_xlabel("Time", fontsize=10)

    ax.set_ylabel("Energy (units)", fontsize=10)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.tick_params(axis="x", rotation=30)

    plt.tight_layout()
    plt.savefig("output_forecast_comparison.png", dpi=150, bbox_inches="tight")
    plt.show()


# ----------------------------------------------------------
# PLOT 2 — Optimization Impact (Before vs After)
# ----------------------------------------------------------

def plot_optimization(future_df, mae=None, selected_model=None):
    fig, ax = plt.subplots(figsize=(14, 6))

    ax.plot(future_df.index, future_df["forecast_energy"],  color="#e07b39",
            linewidth=1.8, label="Before Optimization", zorder=3)
    ax.plot(future_df.index, future_df["optimized_energy"], color="#3a86ff",
            linewidth=1.8, label="After Optimization",  zorder=3)

    ax.fill_between(
        future_df.index,
        future_df["forecast_energy"],
        future_df["optimized_energy"],
        alpha=0.12, color="#3a86ff", label="Reduction Area"
    )

    _shade_peak_hours(ax, future_df.index)

    peak_before      = future_df["forecast_energy"].max()
    peak_after       = future_df["optimized_energy"].max()
    peak_reduction   = (peak_before - peak_after) / peak_before * 100
    peak_before_time = future_df["forecast_energy"].idxmax()
    peak_after_time  = future_df["optimized_energy"].idxmax()

    ax.annotate(f"Peak: {peak_before:.3f}",
                xy=(peak_before_time, peak_before),
                xytext=(10, 10), textcoords="offset points",
                fontsize=8, color="#e07b39",
                arrowprops=dict(arrowstyle="->", color="#e07b39", lw=0.8))
    ax.annotate(f"Peak: {peak_after:.3f}",
                xy=(peak_after_time, peak_after),
                xytext=(10, -18), textcoords="offset points",
                fontsize=8, color="#3a86ff",
                arrowprops=dict(arrowstyle="->", color="#3a86ff", lw=0.8))

    # ── FIX: show which optimizer was used ───────────────────────────────
    optimizer_used = (
        future_df["optimizer_used"].iloc[0]
        if "optimizer_used" in future_df.columns else "Unknown"
    )

    peak_patch = mpatches.Patch(color="red", alpha=0.15,
                                label=f"Peak Hours ({PEAK_START_HOUR}:00-{PEAK_END_HOUR}:00)")
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles=handles + [peak_patch], fontsize=9, loc="upper left")

    title_suffix = (f"  |  Model: {selected_model}  |  MAE: {mae:.4f}"
                    if (selected_model and mae) else "")
    ax.set_title(f"Optimization Impact — 24-Hour Forecast{title_suffix}",
                 fontsize=12, fontweight="bold", pad=10)
    ax.set_xlabel("Time", fontsize=10)
    ax.set_ylabel("Energy (units)", fontsize=10)

    # Peak reduction badge (top-right)
    ax.text(0.99, 0.97, f"Peak Reduction: {peak_reduction:.1f}%  |  Solver: {optimizer_used}",
            transform=ax.transAxes, fontsize=9, color="#2c2c2c",
            ha="right", va="top",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow",
                      edgecolor="gray", alpha=0.8))

    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.tick_params(axis="x", rotation=30)

    plt.tight_layout()
    plt.savefig("output_optimization.png", dpi=150, bbox_inches="tight")
    plt.show()


# ----------------------------------------------------------
# PLOT 3 — Energy Consumption Heatmap
# ----------------------------------------------------------

def plot_energy_heatmap(df):
    df_copy         = df.copy()
    df_copy["hour"] = df_copy.index.hour
    df_copy["dow"]  = df_copy.index.day_name()

    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pivot     = (
        df_copy.groupby(["hour", "dow"])["energy"]
        .mean()
        .unstack("dow")
        .reindex(columns=day_order)
    )

    fig, ax = plt.subplots(figsize=(12, 7))
    im = ax.imshow(pivot.values, aspect="auto", cmap="YlOrRd", interpolation="nearest")

    cbar = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("Mean Energy (units)", fontsize=9)

    ax.set_xticks(range(len(day_order)))
    ax.set_xticklabels([d[:3] for d in day_order], fontsize=9)
    ax.set_yticks(range(0, 24, 2))
    ax.set_yticklabels([f"{h:02d}:00" for h in range(0, 24, 2)], fontsize=8)

    ax.axhline(y=PEAK_START_HOUR - 0.5, color="blue", linewidth=1.5, linestyle="--", alpha=0.6)
    ax.axhline(y=PEAK_END_HOUR   - 0.5, color="blue", linewidth=1.5, linestyle="--", alpha=0.6)
    ax.text(6.6, PEAK_START_HOUR + 0.3, "Peak Start", fontsize=7, color="blue", alpha=0.8)
    ax.text(6.6, PEAK_END_HOUR   + 0.3, "Peak End",   fontsize=7, color="blue", alpha=0.8)

    ax.set_title("Energy Consumption Heatmap — Hour of Day vs Day of Week",
                 fontsize=12, fontweight="bold", pad=10)
    ax.set_xlabel("Day of Week", fontsize=10)
    ax.set_ylabel("Hour of Day", fontsize=10)

    plt.tight_layout()
    plt.savefig("output_heatmap.png", dpi=150, bbox_inches="tight")
    plt.show()


# ----------------------------------------------------------
# PLOT 4 — Peak Shaving Bar Chart
# ----------------------------------------------------------

def plot_peak_shaving_bars(future_df):
    hourly_before = future_df["forecast_energy"].resample("1h").mean()
    hourly_after  = future_df["optimized_energy"].resample("1h").mean()
    hours         = [t.strftime("%H:%M") for t in hourly_before.index]

    x     = np.arange(len(hours))
    width = 0.38

    fig, ax = plt.subplots(figsize=(14, 6))

    ax.bar(x - width/2, hourly_before.values, width,
           color="#e07b39", alpha=0.85, label="Before Optimization")
    ax.bar(x + width/2, hourly_after.values,  width,
           color="#3a86ff", alpha=0.85, label="After Optimization")

    for i, t in enumerate(hourly_before.index):
        if PEAK_START_HOUR <= t.hour < PEAK_END_HOUR:
            ax.axvspan(i - 0.5, i + 0.5, alpha=0.07, color="red", zorder=0)

    ax.set_xticks(x)
    ax.set_xticklabels(hours, rotation=45, fontsize=8)
    ax.set_xlabel("Hour", fontsize=10)
    ax.set_ylabel("Mean Energy (units)", fontsize=10)
    ax.set_title("Peak Shaving — Hourly Energy Before vs After Optimization",
                 fontsize=12, fontweight="bold", pad=10)

    peak_patch = mpatches.Patch(color="red", alpha=0.15,
                                label=f"Peak Hours ({PEAK_START_HOUR}:00-{PEAK_END_HOUR}:00)")
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles=handles + [peak_patch], fontsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    plt.tight_layout()
    plt.savefig("output_peak_shaving_bars.png", dpi=150, bbox_inches="tight")
    plt.show()


# ----------------------------------------------------------
# PLOT 5 — Cost Breakdown Chart
# ----------------------------------------------------------

def plot_cost_breakdown(future_df):
    def compute_costs(col):
        peak_cost    = 0.0
        offpeak_cost = 0.0
        for ts, row in future_df.iterrows():
            energy = row[col]
            if PEAK_START_HOUR <= ts.hour < PEAK_END_HOUR:
                peak_cost    += energy * PEAK_TARIFF
            else:
                offpeak_cost += energy * NORMAL_TARIFF
        return peak_cost, offpeak_cost

    peak_before,  offpeak_before = compute_costs("forecast_energy")
    peak_after,   offpeak_after  = compute_costs("optimized_energy")

    categories   = ["Before Optimization", "After Optimization"]
    peak_vals    = [peak_before,   peak_after]
    offpeak_vals = [offpeak_before, offpeak_after]

    x     = np.arange(len(categories))
    width = 0.45

    fig, ax = plt.subplots(figsize=(8, 6))

    ax.bar(x, offpeak_vals, width, label="Off-Peak Cost (Rs)", color="#4caf82", alpha=0.88)
    ax.bar(x, peak_vals,    width, bottom=offpeak_vals,
           label="Peak Cost (Rs)", color="#e07b39", alpha=0.88)

    for i, (op, pk) in enumerate(zip(offpeak_vals, peak_vals)):
        total = op + pk
        ax.text(i, total + 0.3, f"Rs {total:.1f}", ha="center", va="bottom",
                fontsize=10, fontweight="bold")
        ax.text(i, op / 2,      f"Rs {op:.1f}",    ha="center", va="center",
                fontsize=8, color="white")
        ax.text(i, op + pk / 2, f"Rs {pk:.1f}",    ha="center", va="center",
                fontsize=8, color="white")

    savings = (peak_before + offpeak_before) - (peak_after + offpeak_after)
    ax.text(0.98, 0.97, f"Total Saved: Rs {savings:.2f}",
            transform=ax.transAxes, fontsize=10, color="#2c2c2c",
            ha="right", va="top",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="lightyellow",
                      edgecolor="gray", alpha=0.9))

    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=10)
    ax.set_ylabel("Cost (Rs)", fontsize=10)
    ax.set_title("Cost Breakdown — Peak vs Off-Peak\nBefore and After Optimization",
                 fontsize=12, fontweight="bold", pad=10)
    ax.legend(fontsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    plt.tight_layout()
    plt.savefig("output_cost_breakdown.png", dpi=150, bbox_inches="tight")
    plt.show()


# ----------------------------------------------------------
# PLOT 6 — Train vs Test Split
# FIX: stat boxes moved inside axes (were clipping outside figure)
# FIX: legend uses loc="upper right" to avoid overlap with split line
# ----------------------------------------------------------

def plot_train_test_split(train, test):
    fig, ax = plt.subplots(figsize=(14, 5))

    ax.plot(train.index, train["energy"], color="#3a86ff", linewidth=0.8, label="Train Set")
    ax.plot(test.index,  test["energy"],  color="#e07b39", linewidth=0.8, label="Test Set")

    split_time = test.index[0]
    ax.axvline(x=split_time, color="#2c2c2c", linewidth=1.5, linestyle="--", alpha=0.7)

    # Split label — placed just below top so it never clips
    ymin, ymax = ax.get_ylim()
    ax.text(split_time, ymax * 0.92,
            "  Train / Test\n  Split (80/20)",
            fontsize=8, color="#2c2c2c", va="top")

    # ── FIX: stat boxes use axes-fraction coords, clipped=False ──────────
    train_mean = train["energy"].mean()
    test_mean  = test["energy"].mean()

    ax.text(
        0.01, 0.96,
        f"Train  mean={train_mean:.4f}  n={len(train)}",
        transform=ax.transAxes,
        fontsize=8, va="top", ha="left",
        clip_on=False,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#dceeff",
                  edgecolor="#3a86ff", alpha=0.85)
    )
    ax.text(
        0.99, 0.96,
        f"Test  mean={test_mean:.4f}  n={len(test)}",
        transform=ax.transAxes,
        fontsize=8, va="top", ha="right",
        clip_on=False,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#ffe8d6",
                  edgecolor="#e07b39", alpha=0.85)
    )

    ax.set_title("Energy Consumption — Train vs Test Split",
                 fontsize=12, fontweight="bold", pad=10)
    ax.set_xlabel("Date", fontsize=10)
    ax.set_ylabel("Energy (units)", fontsize=10)

    # ── FIX: legend bottom-right — never overlaps the split line or boxes
    ax.legend(fontsize=9, loc="lower right")

    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.tick_params(axis="x", rotation=30)

    plt.tight_layout()
    plt.savefig("output_train_test_split.png", dpi=150, bbox_inches="tight")
    plt.show()


# ----------------------------------------------------------
# PLOT 7 — Daily Average Consumption Pattern
# ----------------------------------------------------------

def plot_daily_pattern(df):
    df_copy         = df.copy()
    df_copy["hour"] = df_copy.index.hour
    hourly_avg      = df_copy.groupby("hour")["energy"].mean()
    hourly_std      = df_copy.groupby("hour")["energy"].std()

    hours = hourly_avg.index
    fig, ax = plt.subplots(figsize=(12, 5))

    ax.plot(hours, hourly_avg.values, color="#3a86ff", linewidth=2.0,
            marker="o", markersize=4, label="Mean Energy")
    ax.fill_between(hours,
                    hourly_avg.values - hourly_std.values,
                    hourly_avg.values + hourly_std.values,
                    alpha=0.15, color="#3a86ff", label="±1 Std Dev")

    ax.axvspan(PEAK_START_HOUR, PEAK_END_HOUR, alpha=0.08, color="red")
    ax.text(PEAK_START_HOUR + 0.1, hourly_avg.max() * 0.97,
            f"Peak Tariff Zone\n({PEAK_START_HOUR}:00-{PEAK_END_HOUR}:00)",
            fontsize=7, color="red", alpha=0.8)

    ax.set_xticks(range(0, 24))
    ax.set_xticklabels([f"{h:02d}:00" for h in range(24)], rotation=45, fontsize=7)
    ax.set_title("Daily Average Energy Consumption Pattern",
                 fontsize=12, fontweight="bold", pad=10)
    ax.set_xlabel("Hour of Day", fontsize=10)
    ax.set_ylabel("Mean Energy (units)", fontsize=10)
    ax.legend(fontsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    plt.tight_layout()
    plt.savefig("output_daily_pattern.png", dpi=150, bbox_inches="tight")
    plt.show()


# ----------------------------------------------------------
# PLOT 8 — Weekly Consumption Overview
# ----------------------------------------------------------

def plot_weekly_overview(df):
    df_copy        = df.copy()
    df_copy["dow"] = df_copy.index.day_name()
    day_order      = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    weekly_avg = df_copy.groupby("dow")["energy"].mean().reindex(day_order)
    weekly_std = df_copy.groupby("dow")["energy"].std().reindex(day_order)

    colors = ["#3a86ff"] * 5 + ["#e07b39"] * 2
    x      = np.arange(len(day_order))

    fig, ax = plt.subplots(figsize=(10, 5))

    bars = ax.bar(x, weekly_avg.values, color=colors, alpha=0.85,
                  yerr=weekly_std.values, capsize=4, error_kw={"elinewidth": 1})

    for bar, val in zip(bars, weekly_avg.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.002,
                f"{val:.4f}", ha="center", va="bottom", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels([d[:3] for d in day_order], fontsize=10)
    ax.set_title("Weekly Energy Consumption Overview — Mean per Day of Week",
                 fontsize=12, fontweight="bold", pad=10)
    ax.set_xlabel("Day of Week", fontsize=10)
    ax.set_ylabel("Mean Energy (units)", fontsize=10)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    weekday_patch = mpatches.Patch(color="#3a86ff", alpha=0.85, label="Weekdays")
    weekend_patch = mpatches.Patch(color="#e07b39", alpha=0.85, label="Weekends")
    ax.legend(handles=[weekday_patch, weekend_patch], fontsize=9)

    plt.tight_layout()
    plt.savefig("output_weekly_overview.png", dpi=150, bbox_inches="tight")
    plt.show()