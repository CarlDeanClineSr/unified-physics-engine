import os
import glob
import pandas as pd
import numpy as np

# ==============================================================================
# GMVS CORRELATOR (IMPERIAL PHYSICS)
# AUTHORITY: Dr. Carl Dean Cline Sr.
# PURPOSE: Sync Space Cause (L1) with Ground Effect (Surface)
# ==============================================================================

L1_DIR = "data/raw/dscovr"
GROUND_DIR = "data/raw/usgs"
OUTPUT_FILE = "reports/GMVS_VERDICT.md"

# IMPERIAL CONSTANTS
VACUUM_QUANTUM = 10.0 

def get_latest_file(directory):
    list_of_files = glob.glob(os.path.join(directory, '*.csv'))
    if not list_of_files: return None
    return sorted(list_of_files)[-1]

def calculate_gmvs_stress(df):
    """
    Calculates Stress on the Vacuum Sheet using Vector Geometry.
    Formula: r / (1 + r^2)
    """
    # 1. Get Planar Vectors (The "Sheet" dimensions)
    if 'bx_gsm' in df.columns and 'by_gsm' in df.columns:
        # r = Vector Magnitude normalized to Vacuum Quantum
        r = np.sqrt(df['bx_gsm']**2 + df['by_gsm']**2) / VACUUM_QUANTUM
    else:
        # Fallback Estimate
        r = (df['bt'] * 0.707) / VACUUM_QUANTUM

    # 2. Compute Sheet Stress (The Geometry of the Bend)
    stress = (r / (1 + r**2)) 
    
    return stress

def analyze():
    print(">>> GMVS CORRELATOR ONLINE...")
    
    l1_file = get_latest_file(L1_DIR)
    ground_file = get_latest_file(GROUND_DIR)
    
    if not l1_file or not ground_file:
        print("!!! ERROR: GMVS DATA STREAMS MISSING.")
        return

    try:
        # Load and Force UTC Synchronization
        df_l1 = pd.read_csv(l1_file)
        df_ground = pd.read_csv(ground_file)
        
        # Force Numeric and UTC
        for col in df_l1.columns: 
            if 'time' not in col: df_l1[col] = pd.to_numeric(df_l1[col], errors='coerce')
        for col in df_ground.columns: 
            if 'time' not in col: df_ground[col] = pd.to_numeric(df_ground[col], errors='coerce')

        df_l1['time_tag'] = pd.to_datetime(df_l1['time_tag'], utc=True).dt.floor('min')
        df_ground['time_tag'] = pd.to_datetime(df_ground['time_tag'], utc=True).dt.floor('min')

        # Link Space to Ground
        merged = pd.merge(df_l1, df_ground, on='time_tag', how='inner', suffixes=('_space', '_ground'))

        if merged.empty:
            print("!!! STATUS: SYNCHRONIZING BUFFERS (No Time Overlap Yet)")
            return

        # CALCULATE STRESS
        merged['GMVS_STRESS'] = calculate_gmvs_stress(merged)
        
        # Identify Fractures (> 0.15)
        fractures = merged[merged['GMVS_STRESS'] > 0.15]
        peak_stress = merged['GMVS_STRESS'].max()

        # GENERATE REPORT (STERILE TERMINOLOGY)
        report = f"""
# GEOMAGNETIC VACUUM SHEET (GMVS) VERDICT
**Generated:** {pd.Timestamp.now(tz='UTC')}
**Space Node:** {os.path.basename(l1_file)}
**Ground Node:** {os.path.basename(ground_file)}

## GMVS INTEGRITY: {'🔴 FRACTURE DETECTED' if len(fractures) > 0 else '🟢 STABLE'}
* **Peak Stress:** {peak_stress:.4f}
* **Fracture Events (>0.15):** {len(fractures)}

## INSTANTANEOUS LOAD EVENTS
| Time (UTC) | Space Load (nT) | GMVS Stress | Ground Response |
| :--- | :--- | :--- | :--- |
"""
        
        top_events = merged.nlargest(5, 'GMVS_STRESS')
        for _, row in top_events.iterrows():
            # Search for Ground Value (H, F, X)
            g_val = "N/A"
            for target in ['F', 'F_ground', 'H', 'H_ground', 'X', 'X_ground']:
                if target in merged.columns:
                    g_val = row[target]
                    break
            
            report += f"| {row['time_tag']} | {row['bt']} | **{row['GMVS_STRESS']:.4f}** | {g_val} |\n"
            
        if not os.path.exists("reports"): os.makedirs("reports")
        with open(OUTPUT_FILE, "w") as f: f.write(report)
        print(f">>> GMVS REPORT PUBLISHED. PEAK STRESS: {peak_stress:.4f}")

    except Exception as e:
        print(f"!!! CORRELATOR ERROR: {e}")
        raise e

if __name__ == "__main__":
    analyze()
