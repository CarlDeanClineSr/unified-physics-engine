import os
import glob
import pandas as pd
import numpy as np

# ==============================================================================
# GEOMAGNETIC VACUUM SHEET (GMVS) CORRELATOR
# PURPOSE: Monitor the Structural Spine of the Galaxy
# ==============================================================================

L1_DIR = "data/raw/dscovr"
GROUND_DIR = "data/raw/usgs"
OUTPUT_FILE = "reports/GMVS_VERDICT.md"

def get_latest_file(directory):
    list_of_files = glob.glob(os.path.join(directory, '*.csv'))
    if not list_of_files: return None
    return sorted(list_of_files)[-1]

def calculate_gmvs_stress(b_total):
    """
    Calculates Stress on the Geomagnetic Vacuum Sheet.
    Formula: |Current_Load - Resting_State| / Resting_State
    """
    # Ensure numeric
    b_total = pd.to_numeric(b_total, errors='coerce').fillna(0)
    
    # Resting State (Baseline)
    resting_state = b_total.rolling(window=60, min_periods=1).mean()
    resting_state = resting_state.replace(0, 0.0001) 
    
    # Stress Ratio
    stress = abs(b_total - resting_state) / resting_state
    return stress

def analyze():
    print(">>> GMVS MONITORING ONLINE...")
    
    # 1. LOAD DATA
    l1_file = get_latest_file(L1_DIR)
    ground_file = get_latest_file(GROUND_DIR)
    
    if not l1_file or not ground_file:
        print("!!! ERROR: GMVS DATA STREAMS MISSING.")
        return

    try:
        df_l1 = pd.read_csv(l1_file)
        df_ground = pd.read_csv(ground_file)
        
        # 2. FORCE TIME SYNCHRONIZATION (UTC)
        df_l1['time_tag'] = pd.to_datetime(df_l1['time_tag'], utc=True).dt.floor('min')
        df_ground['time_tag'] = pd.to_datetime(df_ground['time_tag'], utc=True).dt.floor('min')

        # 3. MERGE (Check Space-Ground Connection)
        merged = pd.merge(df_l1, df_ground, on='time_tag', how='inner', suffixes=('_space', '_ground'))

        if merged.empty:
            print("!!! NO DATA OVERLAP. GMVS BUFFER FILLING.")
            return

        # 4. COMPUTE GMVS STRESS
        if 'bt' not in merged.columns: return

        merged['GMVS_STRESS'] = calculate_gmvs_stress(merged['bt'])
        snaps = merged[merged['GMVS_STRESS'] > 0.15]
        max_stress = merged['GMVS_STRESS'].max()

        # 5. GENERATE GMVS REPORT
        report = f"""
# GEOMAGNETIC VACUUM SHEET (GMVS) STATUS
**Generated:** {pd.Timestamp.now(tz='UTC')}
**Space Node:** {os.path.basename(l1_file)}
**Ground Node:** {os.path.basename(ground_file)}

## GMVS INTEGRITY: {'🔴 FRACTURE DETECTED' if len(snaps) > 0 else '🟢 STABLE'}
* **Peak Stress Ratio:** {max_stress:.4f}
* **Fracture Events (>0.15):** {len(snaps)}

## TOP GMVS LOAD EVENTS
| Time (UTC) | Space Load (nT) | GMVS Stress | Ground Response |
| :--- | :--- | :--- | :--- |
"""
        
        top_events = merged.nlargest(5, 'GMVS_STRESS')
        for _, row in top_events.iterrows():
            ground_cols = [c for c in df_ground.columns if c not in ['time_tag'] and 'time' not in c]
            g_val = row[ground_cols[0]] if ground_cols else "N/A"
            
            report += f"| {row['time_tag']} | {row['bt']} | **{row['GMVS_STRESS']:.4f}** | {g_val} |\n"
            
        if not os.path.exists("reports"): os.makedirs("reports")
        with open(OUTPUT_FILE, "w") as f: f.write(report)
        print(">>> GMVS REPORT GENERATED.")

    except Exception as e:
        print(f"!!! GMVS MONITOR ERROR: {e}")
        raise e

if __name__ == "__main__":
    analyze()
