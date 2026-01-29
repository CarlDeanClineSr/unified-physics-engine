import os
import glob
import pandas as pd
import numpy as np

# ==============================================================================
# IMPERIAL PHYSICS CORRELATOR (ROBUST MODE)
# PURPOSE: Force Synchronization of Space (L1) and Ground (Surface) Data
# ==============================================================================

L1_DIR = "data/raw/dscovr"
GROUND_DIR = "data/raw/usgs"
OUTPUT_FILE = "reports/IMPERIAL_VERDICT.md"

def get_latest_file(directory):
    """Finds the freshest data by sorting filenames (timestamps)."""
    list_of_files = glob.glob(os.path.join(directory, '*.csv'))
    if not list_of_files:
        return None
    # Sort by name to get the latest timestamp in filename
    return sorted(list_of_files)[-1]

def calculate_chi(b_total):
    """Calculates Imperial Chi. Avoids division by zero."""
    # Ensure numeric
    b_total = pd.to_numeric(b_total, errors='coerce').fillna(0)
    
    # Calculate Baseline (Rolling Memory)
    baseline = b_total.rolling(window=60, min_periods=1).mean()
    baseline = baseline.replace(0, 0.0001) # Safety floor
    
    chi = abs(b_total - baseline) / baseline
    return chi

def analyze():
    print(">>> IMPERIAL CORRELATOR: DIAGNOSTIC SEQUENCE STARTING...")
    
    # 1. LOAD DATA
    l1_file = get_latest_file(L1_DIR)
    ground_file = get_latest_file(GROUND_DIR)
    
    if not l1_file:
        print("!!! ERROR: NO SATELLITE DATA FOUND.")
        return
    if not ground_file:
        print("!!! ERROR: NO GROUND DATA FOUND.")
        return

    print(f"Space Node:  {os.path.basename(l1_file)}")
    print(f"Ground Node: {os.path.basename(ground_file)}")

    try:
        df_l1 = pd.read_csv(l1_file)
        df_ground = pd.read_csv(ground_file)
        
        print(f"Loaded L1 Rows: {len(df_l1)}")
        print(f"Loaded Ground Rows: {len(df_ground)}")

        # 2. FORCE TIME SYNCHRONIZATION (THE CRITICAL FIX)
        # Convert both to datetime with UTC explicit
        df_l1['time_tag'] = pd.to_datetime(df_l1['time_tag'], utc=True)
        df_ground['time_tag'] = pd.to_datetime(df_ground['time_tag'], utc=True)
        
        # Round to minute to ignore seconds drift
        df_l1['time_tag'] = df_l1['time_tag'].dt.floor('min')
        df_ground['time_tag'] = df_ground['time_tag'].dt.floor('min')

        print("Time tags standardized to UTC.")

        # 3. MERGE
        merged = pd.merge(df_l1, df_ground, on='time_tag', how='inner', suffixes=('_space', '_ground'))
        print(f">>> CORRELATION LOCKED. {len(merged)} SYNCHRONIZED EVENTS FOUND.")

        if merged.empty:
            print("!!! WARNING: 0 CORRELATIONS. CHECK TIME RANGES.")
            print(f"L1 Range: {df_l1['time_tag'].min()} to {df_l1['time_tag'].max()}")
            print(f"Ground Range: {df_ground['time_tag'].min()} to {df_ground['time_tag'].max()}")
            
            # Write 'Wait' status to report
            if not os.path.exists("reports"):
                os.makedirs("reports")
            with open(OUTPUT_FILE, "w") as f:
                f.write("# IMPERIAL PHYSICS VERDICT\n**Status:** WAITING FOR OVERLAP.\nData is fresh, but time windows have not aligned yet.")
            return

        # 4. COMPUTE PHYSICS
        if 'bt' not in merged.columns:
            print("!!! ERROR: Column 'bt' missing from Satellite Data.")
            return

        merged['CHI_SPACE'] = calculate_chi(merged['bt'])
        snaps = merged[merged['CHI_SPACE'] > 0.15]
        
        # 5. GENERATE VERDICT
        max_chi = merged['CHI_SPACE'].max()
        print(f"MAX CHI DETECTED: {max_chi:.4f}")

        report = f"""
# IMPERIAL PHYSICS VERDICT
**Generated:** {pd.Timestamp.now(tz='UTC')}
**Correlation Window:** {len(merged)} minutes
**Space Source:** {os.path.basename(l1_file)}
**Ground Source:** {os.path.basename(ground_file)}

## STATUS: {'🔴 ALERT' if len(snaps) > 0 else '🟢 NOMINAL'}
* **Max Chi:** {max_chi:.4f}
* **0.15 Violations:** {len(snaps)}

## TOP EVENTS (Highest Tension)
| Time (UTC) | Space Tension (nT) | Imperial Chi | Ground Response |
| :--- | :--- | :--- | :--- |
"""
        
        top_events = merged.nlargest(5, 'CHI_SPACE')
        for _, row in top_events.iterrows():
            # Find a magnetic column in ground data
            ground_cols = [c for c in df_ground.columns if c not in ['time_tag'] and 'time' not in c]
            g_val = row[ground_cols[0]] if ground_cols else "N/A"
            
            report += f"| {row['time_tag']} | {row['bt']} | **{row['CHI_SPACE']:.4f}** | {g_val} |\n"
            
        # 6. SAVE
        if not os.path.exists("reports"):
            os.makedirs("reports")
        with open(OUTPUT_FILE, "w") as f:
            f.write(report)
            
        print(">>> REPORT GENERATED SUCCESSFULLY.")

    except Exception as e:
        print(f"!!! FATAL ERROR IN CORRELATOR: {e}")
        raise e

if __name__ == "__main__":
    analyze()
