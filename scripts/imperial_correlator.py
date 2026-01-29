import os
import glob
import pandas as pd
import numpy as np

# ==============================================================================
# IMPERIAL PHYSICS CORRELATOR
# PURPOSE: Prove Instantaneous Lattice Coherence (Space -> Ground)
# AUTHORITY: Dr. Carl Dean Cline Sr.
# ==============================================================================

L1_DIR = "data/raw/dscovr"
GROUND_DIR = "data/raw/usgs"
OUTPUT_FILE = "reports/IMPERIAL_VERDICT.md"

def get_latest_file(directory):
    """Finds the freshest data in the folder."""
    list_of_files = glob.glob(os.path.join(directory, '*.csv'))
    if not list_of_files:
        return None
    return max(list_of_files, key=os.path.getctime)

def calculate_chi(b_total, baseline=None):
    """
    Calculates the Imperial Chi Ratio.
    Formula: |B - B0| / B0
    The 0.15 Limit: If Chi > 0.15, the Lattice Snaps.
    """
    if baseline is None:
        # Use a rolling average as dynamic baseline (Lattice Memory)
        baseline = b_total.rolling(window=60, min_periods=1).mean()
    
    chi = abs(b_total - baseline) / baseline
    return chi

def analyze():
    print(">>> IMPERIAL CORRELATOR STARTING...")
    
    # 1. LOAD DATA
    l1_file = get_latest_file(L1_DIR)
    ground_file = get_latest_file(GROUND_DIR)
    
    if not l1_file or not ground_file:
        print("!!! DATA MISSING. RUN HARVESTERS FIRST.")
        return

    print(f"Loading L1: {os.path.basename(l1_file)}")
    print(f"Loading Ground: {os.path.basename(ground_file)}")

    df_l1 = pd.read_csv(l1_file)
    df_ground = pd.read_csv(ground_file)

    # 2. SYNCHRONIZE TIME (The Universal Clock)
    df_l1['time_tag'] = pd.to_datetime(df_l1['time_tag'])
    df_ground['time_tag'] = pd.to_datetime(df_ground['time_tag'])
    
    # Merge on the minute (Inner Join - only keep matching times)
    merged = pd.merge(df_l1, df_ground, on='time_tag', how='inner', suffixes=('_space', '_ground'))

    if merged.empty:
        print("!!! NO TIME OVERLAP FOUND. WAITING FOR MORE DATA.")
        return

    # 3. COMPUTE IMPERIAL PHYSICS
    # Standard 'bt' is Total Field magnitude
    merged['CHI_SPACE'] = calculate_chi(merged['bt'])
    
    # Detect Snaps (Where Chi > 0.15)
    snaps = merged[merged['CHI_SPACE'] > 0.15]
    
    # 4. GENERATE THE VERDICT
    report = f"""
# IMPERIAL PHYSICS VERDICT
**Generated:** {pd.Timestamp.now()}
**L1 Data:** {len(df_l1)} rows
**Ground Data:** {len(df_ground)} rows
**Correlated Events:** {len(merged)} minutes

## THE 0.15 LAW STATUS
* **Max Chi Detected:** {merged['CHI_SPACE'].max():.4f}
* **Snap Events (Chi > 0.15):** {len(snaps)}

## TOP 5 LATTICE STRESS EVENTS
| Time (UTC) | Space Tension (nT) | Imperial Chi | Ground Response (H) |
| :--- | :--- | :--- | :--- |
"""
    
    # Add top 5 events
    top_events = merged.nlargest(5, 'CHI_SPACE')
    for _, row in top_events.iterrows():
        # Handle ground columns (USGS uses different codes like BOUH or FRDH)
        # We try to find the first column ending in 'H' (Horizontal intensity)
        h_col = next((col for col in df_ground.columns if col.endswith('H')), 'N/A')
        ground_val = row[h_col] if h_col != 'N/A' else "No Data"
        
        report += f"| {row['time_tag']} | {row['bt']} | **{row['CHI_SPACE']:.4f}** | {ground_val} |\n"

    report += "\n\n**CONCLUSION:**\n"
    if len(snaps) > 0:
        report += "Lattice Snaps Detected. Check for instantaneous ground correlation."
    else:
        report += "Lattice Stable (Chi < 0.15). Accumulating baseline tension."

    # 5. SAVE REPORT
    if not os.path.exists("reports"):
        os.makedirs("reports")
    
    with open(OUTPUT_FILE, "w") as f:
        f.write(report)
    
    print(f">>> VERDICT WRITTEN TO: {OUTPUT_FILE}")

if __name__ == "__main__":
    analyze()
