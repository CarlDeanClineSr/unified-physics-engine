import os
import glob
import pandas as pd
import numpy as np

# ==============================================================================
# GEOMAGNETIC VACUUM SHEET (GMVS) CORRELATOR
# AUTHORITY: Dr. Carl Dean Cline Sr.
# PURPOSE: Force Synchronization of Space (L1) and Ground (Surface) Data
# ==============================================================================

L1_DIR = "data/raw/dscovr"
GROUND_DIR = "data/raw/usgs"
OUTPUT_FILE = "reports/GMVS_VERDICT.md"

def get_latest_file(directory):
    list_of_files = glob.glob(os.path.join(directory, '*.csv'))
    if not list_of_files: return None
    # Sort by filename to get the latest timestamp
    return sorted(list_of_files)[-1]

def calculate_gmvs_stress(b_total):
    """
    Calculates Mechanical Stress on the Geomagnetic Vacuum Sheet.
    Formula: |Load - Baseline| / Baseline
    """
    # Force numeric
    b_total = pd.to_numeric(b_total, errors='coerce').fillna(0)
    
    # Establish the Vacuum Baseline (Resting State)
    baseline = b_total.rolling(window=60, min_periods=1).mean()
    baseline = baseline.replace(0, 0.0001) 
    
    # Stress Ratio
    stress = abs(b_total - baseline) / baseline
    return stress

def analyze():
    print(">>> GMVS MONITOR INITIALIZED...")
    
    # 1. LOAD STREAMS
    l1_file = get_latest_file(L1_DIR)
    ground_file = get_latest_file(GROUND_DIR)
    
    if not l1_file or not ground_file:
        print("!!! ERROR: DATA STREAMS EMPTY.")
        return

    try:
        # Load and Force UTC Synchronization
        df_l1 = pd.read_csv(l1_file)
        df_ground = pd.read_csv(ground_file)
        
        df_l1['time_tag'] = pd.to_datetime(df_l1['time_tag'], utc=True).dt.floor('min')
        df_ground['time_tag'] = pd.to_datetime(df_ground['time_tag'], utc=True).dt.floor('min')

        # Link Space to Ground
        merged = pd.merge(df_l1, df_ground, on='time_tag', how='inner', suffixes=('_space', '_ground'))

        if merged.empty:
            print("!!! STATUS: SYNCHRONIZING... (No time overlap yet)")
            # Create a placeholder report so workflow doesn't fail
            if not os.path.exists("reports"): os.makedirs("reports")
            with open(OUTPUT_FILE, "w") as f:
                f.write("# GMVS STATUS\n**Status:** SYNCHRONIZING BUFFERS...")
            return

        # 2. CALCULATE GMVS STRESS
        if 'bt' not in merged.columns: return

        merged['GMVS_STRESS'] = calculate_gmvs_stress(merged['bt'])
        
        # 3. IDENTIFY FRACTURE POINTS (> 0.15)
        fractures = merged[merged['GMVS_STRESS'] > 0.15]
        peak_load = merged['GMVS_STRESS'].max()

        # 4. GENERATE REPORT (STRICT TERMINOLOGY)
        report = f"""
# GEOMAGNETIC VACUUM SHEET (GMVS) VERDICT
**Generated:** {pd.Timestamp.now(tz='UTC')}
**Space Node:** {os.path.basename(l1_file)}
**Ground Node:** {os.path.basename(ground_file)}

## GMVS STATUS: {'🔴 STRUCTURAL WARNING' if len(fractures) > 0 else '🟢 STABLE'}
* **Peak Stress Ratio:** {peak_load:.4f}
* **Fracture Events (>0.15):** {len(fractures)}

## TOP GMVS LOAD EVENTS
| Time (UTC) | Space Load (nT) | GMVS Stress | Ground Response |
| :--- | :--- | :--- | :--- |
"""
        
        top_events = merged.nlargest(5, 'GMVS_STRESS')
        for _, row in top_events.iterrows():
            # Find the Ground Vector (H, F, or X)
            ground_cols = [c for c in df_ground.columns if c not in ['time_tag'] and 'time' not in c]
            g_val = row[ground_cols[0]] if ground_cols else "N/A"
            
            # FORMAT: Time | Load | Stress | Ground
            report += f"| {row['time_tag']} | {row['bt']} | **{row['GMVS_STRESS']:.4f}** | {g_val} |\n"
            
        # 5. PUBLISH
        if not os.path.exists("reports"): os.makedirs("reports")
        with open(OUTPUT_FILE, "w") as f: f.write(report)
        print(f">>> GMVS REPORT PUBLISHED: {peak_load:.4f} MAX STRESS")

    except Exception as e:
        print(f"!!! SYSTEM ERROR: {e}")
        raise e

if __name__ == "__main__":
    analyze()
