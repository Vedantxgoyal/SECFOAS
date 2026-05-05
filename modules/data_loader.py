# ==========================================================
# DATA LOADER MODULE - SECFAOS
# ==========================================================

import os
import pandas as pd
from config import DATA_DIR, METER_FILES, TIME_FREQUENCY


def load_data():
    """
    Loads all meter CSV files defined in config.METER_FILES.
    Supports both 'timestamp' and 'datetime' column naming conventions.
    Normalises any meter whose energy range exceeds 1.0 (raw kWh safeguard).
    Merges into a single energy series using concat (sequential stacking).
    """

    if not os.path.exists(DATA_DIR):
        raise FileNotFoundError(f"Data directory not found: {DATA_DIR}")

    if not METER_FILES:
        raise ValueError("METER_FILES is empty in config.py")

    dfs = []

    for fname in METER_FILES:
        path = os.path.join(DATA_DIR, fname)

        # ── File existence ──────────────────────────────────────
        if not os.path.exists(path):
            print(f"  WARNING: {fname} not found — skipping")
            continue

        # ── Load raw ────────────────────────────────────────────
        try:
            raw = pd.read_csv(path)
        except Exception as e:
            print(f"  WARNING: Could not read {fname}: {e} — skipping")
            continue

        # ── Normalise timestamp column ──────────────────────────
        if "timestamp" in raw.columns:
            raw["timestamp"] = pd.to_datetime(raw["timestamp"], errors="coerce")
            raw = raw.set_index("timestamp")
        elif "datetime" in raw.columns:
            raw["datetime"] = pd.to_datetime(raw["datetime"], errors="coerce")
            raw = raw.set_index("datetime")
            raw.index.name = "timestamp"
        else:
            print(f"  WARNING: {fname} has no 'timestamp' or 'datetime' column — skipping")
            continue

        # ── Validate energy column ──────────────────────────────
        if "energy" not in raw.columns:
            print(f"  WARNING: {fname} missing 'energy' column — skipping")
            continue

        # ── Extract and clean ───────────────────────────────────
        df = raw[["energy"]].copy()
        df["energy"] = pd.to_numeric(df["energy"], errors="coerce")
        df = df.dropna(subset=["energy"])
        df = df.sort_index()
        df = df[~df.index.duplicated(keep="first")]

        # ── Resample to 30min ───────────────────────────────────
        df = df.resample(TIME_FREQUENCY).mean()

        # ── Fill small gaps (max 1 hour = 2 slots) ──────────────
        df["energy"] = df["energy"].ffill(limit=2).bfill(limit=2)
        df = df.dropna()

        if df.empty:
            print(f"  WARNING: {fname} is empty after cleaning — skipping")
            continue

        # ── Safety normalise (catches any un-normalised files) ───
        e_max = df["energy"].max()
        if e_max > 1.5:
            e_min = df["energy"].min()
            df["energy"] = (df["energy"] - e_min) / (e_max - e_min)
            print(f"  NOTE: {fname} was not normalised (max={e_max:.2f}) — auto-normalised to 0-1")

        print(f"  Loaded {fname:<30} | "
              f"records={len(df):<5} | "
              f"std={df['energy'].std():.4f} | "
              f"period={str(df.index[0])[:10]} to {str(df.index[-1])[:10]}")

        dfs.append(df)

    # ── Guard ────────────────────────────────────────────────────
    if not dfs:
        raise RuntimeError("No valid meter files loaded. Check DATA_DIR and METER_FILES.")

    # ── Merge: concat sequential stack ───────────────────────────
    combined = pd.concat(dfs)
    combined = combined.sort_index()
    combined = combined[~combined.index.duplicated(keep="first")]

    # ── Final resample to ensure clean frequency ─────────────────
    combined = combined.resample(TIME_FREQUENCY).mean()
    combined["energy"] = combined["energy"].ffill(limit=2)
    combined = combined.dropna()

    # ── Final validation ─────────────────────────────────────────
    if combined["energy"].isnull().any():
        raise ValueError("Null values remain after merge. Check meter files.")

    print(f"\n  Combined dataset:")
    print(f"    Meters loaded : {len(dfs)}/{len(METER_FILES)}")
    print(f"    Total records : {len(combined)}")
    print(f"    Period        : {combined.index[0]} to {combined.index[-1]}")
    print(f"    Std           : {combined['energy'].std():.4f}")
    print(f"    Mean          : {combined['energy'].mean():.4f}")
    print(f"    Min / Max     : {combined['energy'].min():.4f} / {combined['energy'].max():.4f}")

    return combined