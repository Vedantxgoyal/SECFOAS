# ==========================================================
# OPTIMIZATION MODULE - SECFAOS
# PuLP LP solver (primary) + greedy heuristic (fallback)
#
# TWO-LAYER OPTIMIZATION:
#   Layer 1 — Generic LP: shifts flexible load away from peak
#   Layer 2 — Device LP: schedules EV, Geyser, Washing Machine
#
# Guarantees:
#   - Peak tariff slots never upshifted
#   - No slot exceeds original global forecast maximum
#   - Device constraints respected (power, window, daily run)
# ==========================================================

import logging
import numpy as np
import pandas as pd

from config import (
    FLEXIBLE_LOAD_PERCENT,
    PEAK_PERCENTILE_THRESHOLD,
    OPTIMIZATION_WEIGHT,
    NORMAL_TARIFF,
    PEAK_TARIFF,
    PEAK_START_HOUR,
    PEAK_END_HOUR,
    ENERGY_SCALE_KWH,
)
from modules.carbon_model import get_carbon_intensity

logger = logging.getLogger(__name__)

DEMAND_TOLERANCE = 0.15

# ----------------------------------------------------------
# DEVICE DEFINITIONS
# Device power is in normalised units (kWh / ENERGY_SCALE_KWH)
# ----------------------------------------------------------
# Each device:
#   power_kwh    — energy consumed per 30-min slot when ON
#   slots_needed — number of consecutive 30-min slots required
#   window_hours — tuple (start_hour, end_hour) allowed operation
#   must_run     — must complete exactly once in 24h window
#   name         — display name

DEVICES = [
    {
        "name":         "EV Charger",
        "power_kwh":    1.5,
        "slots_needed": 4,
        "window_hours": (22, 6),
        "must_run":     True,
    },
    {
        "name":         "Water Heater",
        "power_kwh":    1.0,
        "slots_needed": 2,
        "window_hours": (6, 10),
        "must_run":     True,
    },
    {
        "name":         "Washing Machine",
        "power_kwh":    0.8,
        "slots_needed": 3,
        "window_hours": (8, 18),
        "must_run":     False,
    },
    {
        "name":         "Ceiling Fan",
        "power_kwh":    0.075,
        "slots_needed": 16,
        "window_hours": (6, 22),
        "must_run":     False,
    },
    {
        "name":         "Air Conditioner",
        "power_kwh":    1.2,
        "slots_needed": 6,
        "window_hours": (14, 20),
        "must_run":     False,
    },
]


# ----------------------------------------------------------
# SHARED HELPERS
# ----------------------------------------------------------

def get_tariff(timestamp) -> float:
    hour = timestamp.hour
    return PEAK_TARIFF if PEAK_START_HOUR <= hour < PEAK_END_HOUR else NORMAL_TARIFF


def _is_peak_tariff_slot(timestamp) -> bool:
    return PEAK_START_HOUR <= timestamp.hour < PEAK_END_HOUR


def _is_cheap_slot(timestamp) -> bool:
    h = timestamp.hour
    return ((0 <= h < 6) or (10 <= h < 16)) and not _is_peak_tariff_slot(timestamp)


def _build_price_vector(index: pd.DatetimeIndex) -> np.ndarray:
    return np.array([
        get_tariff(ts) + OPTIMIZATION_WEIGHT * get_carbon_intensity(ts)
        for ts in index
    ])


def _slot_in_window(hour: int, window: tuple) -> bool:
    """
    Check if hour is within the device operation window.
    Handles windows that wrap midnight (e.g. 22:00-06:00).
    """
    start, end = window
    if start < end:
        return start <= hour < end
    else:
        # Wraps midnight
        return hour >= start or hour < end


# ----------------------------------------------------------
# LAYER 1: GENERIC LP OPTIMIZER
# ----------------------------------------------------------

def _lp_optimize(future_df: pd.DataFrame) -> pd.DataFrame:
    import pulp

    demand       = future_df["forecast_energy"].values.copy().astype(float)
    n            = len(demand)
    prices       = _build_price_vector(future_df.index)
    total_demand = demand.sum()
    global_peak  = demand.max()

    peak_cap = np.percentile(demand[demand > 0], 75) if (demand > 0).any() else global_peak

    prob = pulp.LpProblem("EnergyScheduleOptimization", pulp.LpMinimize)
    e    = [pulp.LpVariable(f"e_{t}", lowBound=0) for t in range(n)]

    prob += pulp.lpSum(prices[t] * e[t] for t in range(n))

    prob += pulp.lpSum(e[t] for t in range(n)) >= (1 - DEMAND_TOLERANCE) * total_demand
    prob += pulp.lpSum(e[t] for t in range(n)) <= (1 + DEMAND_TOLERANCE) * total_demand

    for t in range(n):
        ts       = future_df.index[t]
        d_t      = float(demand[t])
        is_peak  = _is_peak_tariff_slot(ts)
        is_cheap = _is_cheap_slot(ts)

        prob += e[t] <= float(global_peak)

        if is_peak:
            prob += e[t] <= d_t
            if d_t > peak_cap:
                effective_cap = max(float(peak_cap), 0.50 * d_t)
                prob += e[t] <= effective_cap
            prob += e[t] >= 0.50 * d_t

        elif is_cheap:
            prob += e[t] <= min(d_t * (1 + FLEXIBLE_LOAD_PERCENT), float(global_peak))
            prob += e[t] >= 0.75 * d_t

        else:
            prob += e[t] <= d_t
            prob += e[t] >= (1 - FLEXIBLE_LOAD_PERCENT) * d_t

    solver = pulp.PULP_CBC_CMD(msg=0)
    status = prob.solve(solver)

    if pulp.LpStatus[status] != "Optimal":
        raise RuntimeError(
            f"LP solver did not reach Optimal. Status: {pulp.LpStatus[status]}"
        )

    optimized = np.array([max(pulp.value(e[t]), 0.0) for t in range(n)])

    for t, ts in enumerate(future_df.index):
        if _is_peak_tariff_slot(ts):
            optimized[t] = min(optimized[t], demand[t])

    optimized = np.clip(optimized, 0, global_peak)

    result_df                     = future_df.copy()
    result_df["optimized_energy"] = optimized
    result_df["optimizer_used"]   = "LP"

    peak_red    = (100 * (demand.max() - optimized.max()) / demand.max()
                   if demand.max() > 0 else 0)
    cost_before = sum(prices[t] * demand[t]    for t in range(n))
    cost_after  = sum(prices[t] * optimized[t] for t in range(n))

    logger.info(
        "LP complete | Total: %.4f->%.4f | Peak: %.4f->%.4f (%.1f%%) | Cost: %.4f->%.4f",
        total_demand, optimized.sum(),
        demand.max(), optimized.max(), peak_red,
        cost_before, cost_after,
    )

    return result_df


# ----------------------------------------------------------
# LAYER 2: DEVICE-LEVEL LP SCHEDULER
# ----------------------------------------------------------

def _device_lp_optimize(future_df: pd.DataFrame) -> pd.DataFrame:
    """
    Schedules individual appliances (EV, Geyser, Washing Machine)
    within their allowed operation windows to minimise cost + carbon.

    Each device is modelled as a binary start variable — the device
    starts at slot s and runs for slots_needed consecutive slots.
    The LP picks the cheapest valid start slot for each device.

    Returns future_df with additional columns:
        device_{name}_schedule  — binary array (1=ON, 0=OFF) per slot
        device_{name}_kwh       — normalised energy added per slot
        device_total_added      — total normalised energy from all devices
        optimized_with_devices  — final schedule including device load
    """
    import pulp

    n      = len(future_df)
    index  = future_df.index
    prices = _build_price_vector(index)

    result_df = future_df.copy()
    device_loads = np.zeros(n)

    for device in DEVICES:
        name         = device["name"]
        power_kwh    = device["power_kwh"]
        slots_needed = device["slots_needed"]
        window       = device["window_hours"]
        must_run     = device["must_run"]

        # Convert kWh to normalised units
        power_norm = power_kwh / ENERGY_SCALE_KWH

        # Find valid start slots — device must fit entirely within window
        valid_starts = []
        for t in range(n - slots_needed + 1):
            # All slots in the run must be within the window
            all_in_window = all(
                _slot_in_window(index[t + k].hour, window)
                for k in range(slots_needed)
            )
            # None of the slots can be peak tariff
            no_peak = all(
                not _is_peak_tariff_slot(index[t + k])
                for k in range(slots_needed)
            )
            if all_in_window and no_peak:
                valid_starts.append(t)

        if not valid_starts:
            logger.warning("Device %s: no valid start slots found — skipping", name)
            result_df[f"device_{name}_schedule"] = np.zeros(n)
            result_df[f"device_{name}_kwh"]      = np.zeros(n)
            continue

        # Binary LP: x[s] = 1 means device starts at slot s
        prob   = pulp.LpProblem(f"Device_{name}", pulp.LpMinimize)
        x      = {s: pulp.LpVariable(f"x_{s}", cat="Binary") for s in valid_starts}

        # Objective: minimise cost of running this device
        prob += pulp.lpSum(
            x[s] * sum(prices[s + k] * power_norm for k in range(slots_needed))
            for s in valid_starts
        )

        # Must run exactly once if must_run=True, at most once otherwise
        if must_run:
            prob += pulp.lpSum(x[s] for s in valid_starts) == 1
        else:
            prob += pulp.lpSum(x[s] for s in valid_starts) <= 1

        solver = pulp.PULP_CBC_CMD(msg=0)
        status = prob.solve(solver)

        # Build schedule array
        schedule   = np.zeros(n)
        device_kwh = np.zeros(n)

        if pulp.LpStatus[status] == "Optimal":
            for s in valid_starts:
                if pulp.value(x[s]) is not None and pulp.value(x[s]) > 0.5:
                    for k in range(slots_needed):
                        schedule[s + k]   = 1
                        device_kwh[s + k] = power_norm
                    chosen_start = index[s]
                    chosen_cost  = sum(
                        prices[s + k] * power_norm for k in range(slots_needed)
                    )
                    logger.info(
                        "Device %s scheduled at %s | cost=%.4f | slots=%d",
                        name, chosen_start, chosen_cost, slots_needed
                    )
                    print(f"  Device [{name}]: start={chosen_start.strftime('%H:%M')} | "
                          f"duration={slots_needed * 30}min | "
                          f"power={power_kwh}kWh/slot | "
                          f"cost=Rs {round(chosen_cost * PEAK_TARIFF, 2)}")
        else:
            logger.warning("Device %s LP infeasible — not scheduled", name)

        result_df[f"device_{name}_schedule"] = schedule
        result_df[f"device_{name}_kwh"]      = device_kwh
        device_loads += device_kwh

    # Add device load on top of generic optimized schedule
    result_df["device_total_added"]     = device_loads
    result_df["optimized_with_devices"] = (
        result_df["optimized_energy"] + device_loads
    )

    # Summary
    total_device_kwh  = device_loads.sum() * ENERGY_SCALE_KWH
    total_device_cost = sum(
        device_loads[t] * get_tariff(index[t])
        for t in range(n)
    )
    print(f"\n  Device scheduling complete:")
    print(f"    Total device energy : {round(total_device_kwh, 3)} kWh")
    print(f"    Total device cost   : Rs {round(total_device_cost * ENERGY_SCALE_KWH, 2)}")

    return result_df


# ----------------------------------------------------------
# FALLBACK: GREEDY TOU-AWARE OPTIMIZER
# ----------------------------------------------------------

def _greedy_optimize(future_df: pd.DataFrame) -> pd.DataFrame:
    demand      = future_df["forecast_energy"].values.astype(float)
    optimized   = demand.copy()
    global_peak = demand.max()
    threshold   = np.percentile(demand[demand > 0], 75) if (demand > 0).any() else global_peak
    saved       = 0.0

    for i, ts in enumerate(future_df.index):
        d_t       = demand[i]
        is_high   = d_t > threshold
        is_peak_t = _is_peak_tariff_slot(ts)

        if is_high or is_peak_t:
            reduction     = FLEXIBLE_LOAD_PERCENT * d_t
            cost_saving   = reduction * get_tariff(ts)
            carbon_saving = reduction * get_carbon_intensity(ts)

            if cost_saving + OPTIMIZATION_WEIGHT * carbon_saving > 0:
                floor         = 0.50 * d_t if is_peak_t else 0.45 * d_t
                new_val       = max(d_t - reduction, floor)
                saved        += d_t - new_val
                optimized[i]  = new_val

    cheap_slots = [
        i for i, ts in enumerate(future_df.index)
        if _is_cheap_slot(ts) and not _is_peak_tariff_slot(ts)
    ]

    if cheap_slots and saved > 0:
        per_slot = saved / len(cheap_slots)
        for i in cheap_slots:
            cap          = min(demand[i] * (1 + FLEXIBLE_LOAD_PERCENT), global_peak)
            optimized[i] = min(optimized[i] + per_slot, cap)

    for i, ts in enumerate(future_df.index):
        if _is_peak_tariff_slot(ts):
            optimized[i] = min(optimized[i], demand[i])

    optimized = np.clip(optimized, 0, global_peak)

    result_df                     = future_df.copy()
    result_df["optimized_energy"] = optimized
    result_df["optimizer_used"]   = "Greedy"

    peak_red = (
        100 * (demand.max() - optimized.max()) / demand.max()
        if demand.max() > 0 else 0
    )
    logger.info(
        "Greedy complete | Peak: %.4f->%.4f (%.1f%%)",
        demand.max(), optimized.max(), peak_red,
    )

    return result_df


# ----------------------------------------------------------
# PUBLIC INTERFACE
# ----------------------------------------------------------

def optimize_forecast(future_df: pd.DataFrame) -> pd.DataFrame:
    """
    Two-layer optimization:
      Layer 1 — Generic LP (or greedy fallback)
      Layer 2 — Device-level LP scheduling

    Returns DataFrame with both generic and device-aware schedules.
    """
    # ── Layer 1: Generic LP ───────────────────────────────────────────────
    try:
        import pulp  # noqa: F401
        result = _lp_optimize(future_df)
        logger.info("Optimizer: LP (PuLP)")
    except ImportError:
        logger.warning("PuLP not installed — greedy fallback.")
        result = _greedy_optimize(future_df)
    except RuntimeError as e:
        logger.warning("LP failed (%s) — greedy fallback.", e)
        result = _greedy_optimize(future_df)
    except Exception as e:
        logger.warning("Unexpected LP error (%s) — greedy fallback.", e)
        result = _greedy_optimize(future_df)

    # ── Layer 2: Device-level LP ──────────────────────────────────────────
    print("\n----- DEVICE SCHEDULING -----")
    try:
        result = _device_lp_optimize(result)
        logger.info("Device LP complete.")
    except Exception as e:
        logger.warning("Device LP failed (%s) — skipping device scheduling.", e)
        result["device_total_added"]     = 0.0
        result["optimized_with_devices"] = result["optimized_energy"]

    return result