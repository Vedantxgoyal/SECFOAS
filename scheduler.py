# ==========================================================
# LIVE DATA SIMULATION - SECFAOS
# APScheduler-based pipeline runner
#
# Simulates a live BSES AMI feed by:
#   1. Taking the last N days of real meter data
#   2. Adding small realistic noise to simulate "new" readings
#   3. Appending to a live_feed.csv file
#   4. Running the full pipeline on updated data every 24 hours
#
# Run: python scheduler.py
# Stops with Ctrl+C
# ==========================================================

import os
import time
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
DATA_DIR      = os.path.join(BASE_DIR, "data")
LIVE_FEED_CSV = os.path.join(DATA_DIR, "live_feed.csv")
LOG_FILE      = os.path.join(BASE_DIR, "scheduler_log.txt")

# How many recent days to use as seed for simulation
SEED_DAYS = 7

# Noise level — realistic meter reading variation (±3%)
NOISE_LEVEL = 0.03


# ----------------------------------------------------------
# STEP 1: SIMULATE NEW METER DATA
# ----------------------------------------------------------

def simulate_new_readings() -> pd.DataFrame:
    """
    Takes the last SEED_DAYS of meter2 (most complete single meter)
    and generates a new 24-hour block of synthetic readings by:
      - Taking the same-DOW profile from last week
      - Adding Gaussian noise (±NOISE_LEVEL)
      - Advancing timestamps by 24 hours
    """
    source_path = os.path.join(DATA_DIR, "meter2_clean.csv")

    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source meter file not found: {source_path}")

    df = pd.read_csv(source_path, parse_dates=["datetime"])
    df = df.set_index("datetime").sort_index()
    df = df[["energy"]]

    # Get last complete 48-slot day as template
    last_date  = df.index[-1].date()
    target_dow = (pd.Timestamp(last_date) + timedelta(days=1)).dayofweek

    # Find most recent same-DOW day
    template = None
    for date, group in reversed(list(df.groupby(df.index.date))):
        if pd.Timestamp(date).dayofweek == target_dow and len(group) == 48:
            template = group["energy"].values.copy()
            break

    if template is None:
        # Fallback: use last 48 slots
        template = df["energy"].values[-48:].copy()

    # Add realistic noise
    noise     = np.random.normal(0, NOISE_LEVEL, size=len(template))
    new_vals  = np.clip(template + noise, 0, 1)

    # New timestamps = last timestamp + 30min increments
    last_ts    = df.index[-1]
    new_index  = pd.date_range(
        start=last_ts + timedelta(minutes=30),
        periods=len(new_vals),
        freq="30min"
    )

    new_df = pd.DataFrame({"energy": new_vals}, index=new_index)
    new_df.index.name = "datetime"

    logger.info("Simulated %d new readings for %s (DOW=%d)",
                len(new_df), new_index[0].date(), target_dow)

    return new_df


# ----------------------------------------------------------
# STEP 2: APPEND TO LIVE FEED
# ----------------------------------------------------------

def update_live_feed(new_readings: pd.DataFrame):
    """
    Appends new readings to live_feed.csv.
    Creates the file on first run by copying meter2_clean.csv.
    Keeps only the last 90 days to prevent unbounded growth.
    """
    if not os.path.exists(LIVE_FEED_CSV):
        # First run — seed with meter2
        source = os.path.join(DATA_DIR, "meter2_clean.csv")
        df_seed = pd.read_csv(source)
        df_seed.to_csv(LIVE_FEED_CSV, index=False)
        logger.info("Created live_feed.csv seeded from meter2_clean.csv")

    # Load existing feed
    existing = pd.read_csv(LIVE_FEED_CSV, parse_dates=["datetime"])
    existing = existing.set_index("datetime").sort_index()

    # Append new readings
    combined = pd.concat([existing, new_readings])
    combined = combined[~combined.index.duplicated(keep="last")]
    combined = combined.sort_index()

    # Keep only last 90 days (4,320 slots)
    cutoff  = combined.index[-1] - timedelta(days=90)
    combined = combined[combined.index >= cutoff]

    combined.to_csv(LIVE_FEED_CSV)
    logger.info("Live feed updated | Total records: %d | Latest: %s",
                len(combined), combined.index[-1])


# ----------------------------------------------------------
# STEP 3: RUN PIPELINE
# ----------------------------------------------------------

def run_pipeline():
    """
    Runs the full SECFAOS pipeline on current data.
    Uses force_retrain=False so saved LSTM model is reused.
    Logs results to scheduler_log.txt.
    """
    logger.info("=" * 50)
    logger.info("SCHEDULED PIPELINE RUN — %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    logger.info("=" * 50)

    try:
        # Run main pipeline
        import subprocess
        result = subprocess.run(
            ["python", "main.py"],
            capture_output=True,
            text=True,
            cwd=BASE_DIR
        )

        # Log output
        with open(LOG_FILE, "a") as f:
            f.write(f"\n{'='*50}\n")
            f.write(f"Run at: {datetime.now()}\n")
            f.write(result.stdout)
            if result.returncode != 0:
                f.write(f"\nERROR:\n{result.stderr}")

        if result.returncode == 0:
            logger.info("Pipeline completed successfully")
            # Extract key metrics from output
            for line in result.stdout.split("\n"):
                if any(k in line for k in [
                    "Peak Reduction", "Annual Cost", "Carbon Reduction",
                    "Selected Model", "LSTM MAE"
                ]):
                    logger.info("  %s", line.strip())
        else:
            logger.error("Pipeline failed. Check scheduler_log.txt")

    except Exception as e:
        logger.error("Pipeline run failed: %s", e)


# ----------------------------------------------------------
# STEP 4: FULL SCHEDULED JOB
# ----------------------------------------------------------

def scheduled_job():
    """
    Complete job executed on each schedule tick:
      1. Simulate new meter readings
      2. Append to live feed
      3. Run full pipeline
    """
    logger.info("Starting scheduled job...")

    try:
        new_readings = simulate_new_readings()
        update_live_feed(new_readings)
        run_pipeline()
        logger.info("Scheduled job complete.")

    except Exception as e:
        logger.error("Scheduled job failed: %s", e)


# ----------------------------------------------------------
# MAIN — SCHEDULER SETUP
# ----------------------------------------------------------

if __name__ == "__main__":

    print("=" * 50)
    print(" SECFAOS Live Data Simulation Scheduler")
    print("=" * 50)
    print(f" Schedule  : Every 24 hours")
    print(f" Live feed : {LIVE_FEED_CSV}")
    print(f" Log file  : {LOG_FILE}")
    print(f" Started   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    print(" Press Ctrl+C to stop\n")

    # Run once immediately on startup
    logger.info("Running initial job on startup...")
    scheduled_job()

    # Schedule every 24 hours
    scheduler = BlockingScheduler()
    scheduler.add_job(
        scheduled_job,
        trigger=IntervalTrigger(hours=24),
        id="secfaos_pipeline",
        name="SECFAOS Daily Pipeline",
        misfire_grace_time=3600,   # allow 1 hour grace if missed
        coalesce=True,             # don't stack missed runs
    )

    logger.info("Scheduler started. Next run in 24 hours.")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped by user.")
        scheduler.shutdown()
        print("\nScheduler stopped cleanly.")