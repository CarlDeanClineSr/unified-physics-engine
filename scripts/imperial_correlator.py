import os
import glob
import pandas as pd
import numpy as np

# ==============================================================================
# GMVS VECTOR CORRELATOR (IMPERIAL MATH)
# AUTHORITY: Dr. Carl Dean Cline Sr.
# METHOD: Instantaneous Vector Geometry (No Statistical Smoothing)
# ==============================================================================

L1_DIR = "data/raw/dscovr"
GROUND_DIR = "data/raw/usgs"
OUTPUT_FILE = "reports/GMVS_VERDICT.md"

# IMPERIAL CONSTANTS (Normalized to 10nT Baseline)
# Used to convert raw nT into Unitless Lattice Space (r)
VACUUM_QUANTUM = 10.0 

def get_latest_file(directory):
    list_of_files = glob.glob(os.path.join(directory, '*.csv'))
    if not list_of_files: return None
    return sorted(list_of_files)[-1]

def calculate_instant_chi(df):
    """
    Calculates Chi (χ) using Instantaneous Vector Geometry.
    NO AVERAGING. NO SMOOTHING.
    Formula: χ = r / (1 + r^2) * Scaling_Factor
    """
    # 1. Get Planar Vectors (The "Sheet" dimensions)
    # If bx/by missing, estimate from bt
    if 'bx_gsm' in df.columns and 'by_gsm' in df.columns:
        # r = sqrt(x^2 + y^2) / Quantum
        r = np.sqrt(df['bx_gsm']**2 + df['by_gsm']**2) / VACUUM_QUANTUM
    else:
        # Fallback for scalar data
        r = (df['bt'] * 0.707) / VACUUM_QUANTUM

    # 2. Compute Imperial Chi (The Knot)
    # This matches the form: x / (1 + x^2)
    # We scale it so the Critical Threshold aligns with 0.15
    chi = (r / (1 + r**2)) 
    
    return chi

def analyze():
    print(">>> GMVS VECTOR ENGINE ONLINE...")
    
    l1_file = get_latest_file(L1_DIR)
    ground_file = get_latest_file(GROUND_DIR)
    
    if not l1_file or not ground_file:
        print("!!! ERROR: STREAMS MISSING.")
        return

    try:
        # Load Raw Data
        df_l1 = pd.read_csv(l1_file)
        df_ground = pd.read_csv(ground_file)
        
        # Force Numeric
        for col in df_l1.columns: 
            if 'time' not in col: df_l1[col] = pd.to_numeric(df_l1[col], errors='coerce')
        for col in df_ground.columns: 
            if 'time' not in col: df_ground[col] = pd.to_numeric(df_ground[col], errors='coerce')

        # Sync Time (UTC)
        df_l1['time_tag'] = pd.to_datetime(df_l1['time_tag'], utc=True).dt.floor('min')
        df_ground['time_tag'] = pd.to_datetime(df_ground['time_tag'], utc=True).dt.floor('min')

        # Merge (Instantaneous Link)
        merged = pd.merge(df_l1, df_ground, on='time_tag', how='inner', suffixes=('_space', '_ground'))

        if merged.empty:
            print("!!! NO OVERLAP. BUFFERING...")
            return

        # CALCULATE STRESS (The New Math)
        merged['GMVS_CHI'] = calculate_instant_chi(merged)
        
        # Identify Fractures
        fractures = merged[merged['GMVS_CHI'] > 0.15]
        peak_stress = merged['GMVS_CHI'].max()

        # GENERATE REPORT
        report = f"""
# GMVS VECTOR VERDICT
**Generated:** {pd.Timestamp.now(tz='UTC')}
**Space Node:** {os.path.basename(l1_file)}
**Ground Node:** {os.path.basename(ground_file)}

## LATTICE INTEGRITY: {'🔴 FRACTURE' if len(fractures) > 0 else '🟢 STABLE'}
* **Peak Chi:** {peak_stress:.4f}
* **0.15 Violations:** {len(fractures)}

## INSTANTANEOUS SNAP EVENTS
| Time (UTC) | B_Total (nT) | GMVS Chi | Ground (F) |
| :--- | :--- | :--- | :--- |
"""
        
        top_events = merged.nlargest(5, 'GMVS_CHI')
        for _, row in top_events.iterrows():
            # Fix the "F" bug: Explicitly grab the column named 'F' or 'H'
            # We look for the column in the MERGED dataframe that came from ground
            # It will likely be 'F' or 'F_ground' or 'H'
            
            g_val = "N/A"
            # Priority Search for Ground Value
            for target in ['F', 'F_ground', 'H', 'H_ground', 'X', 'X_ground']:
                if target in merged.columns:
                    g_val = row[target]
                    break
            
            report += f"| {row['time_tag']} | {row['bt']} | **{row['GMVS_CHI']:.4f}** | {g_val} |\n"
            
        if not os.path.exists("reports"): os.makedirs("reports")
        with open(OUTPUT_FILE, "w") as f: f.write(report)
        print(f">>> REPORT PUBLISHED. PEAK CHI: {peak_stress:.4f}")

    except Exception as e:
        print(f"!!! VECTOR ENGINE ERROR: {e}")
        raise e

if __name__ == "__main__":
    analyze()
