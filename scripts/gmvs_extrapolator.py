import os
import glob
import pandas as pd
import numpy as np
from datetime import datetime

# ==============================================================================
# GMVS EXTRAPOLATOR (IMPERIAL PHYSICS)
# AUTHORITY: Dr. Carl Dean Cline Sr.
# OBJECTIVE: Map the curvature of the Geomagnetic Vacuum Sheet.
# ==============================================================================

RAW_DIR = "data/raw/dscovr"
RESULTS_DIR = "results"
CHI_SNAP_LIMIT = 0.15

def get_latest_file(directory):
    list_of_files = glob.glob(os.path.join(directory, '*.csv'))
    if not list_of_files: return None
    return max(list_of_files, key=os.path.getctime)

def calculate_vacuum_geometry(df):
    """
    Applies Imperial Math to model the Sheet.
    1. Baseline = Resting State
    2. Chi = Tension Ratio
    3. Depth = 3D Curvature
    """
    print(">>> MAPPING VACUUM SHEET GEOMETRY...")
    
    df['bt'] = pd.to_numeric(df['bt'], errors='coerce')
    
    # 1. BASELINE (Resting State)
    # The sheet seeks equilibrium over time.
    df['B_baseline'] = df['bt'].rolling(window=60, min_periods=1).mean()
    
    # 2. CHI RATIO (Tension)
    # How tight is the sheet pulled?
    df['CHI'] = abs(df['bt'] - df['B_baseline']) / df['B_baseline']
    
    # 3. VACUUM DEPTH (z)
    # Standard Math calls this "Lattice Distortion". 
    # Imperial Physics calls this "Sheet Depth".
    planar_tension = (df['bt'] * 0.707)**2
    df['SHEET_DEPTH'] = np.sqrt(planar_tension) / (1 + df['CHI'])
    
    return df

def filter_significant_events(df):
    # Only keep data where the Sheet is moving (Chi > 0.05)
    mask = (df['CHI'] > 0.05)
    events = df[mask].copy()
    return events

def run_extrapolation():
    print(">>> EXTRAPOLATOR ONLINE...")
    
    if not os.path.exists(RESULTS_DIR): os.makedirs(RESULTS_DIR)
        
    data_file = get_latest_file(RAW_DIR)
    if not data_file:
        print("!!! HALT: No Raw Data.")
        return
        
    print(f"Source: {os.path.basename(data_file)}")
    df = pd.read_csv(data_file)
    
    df_processed = calculate_vacuum_geometry(df)
    df_results = filter_significant_events(df_processed)
    
    count = len(df_results)
    print(f">>> SCAN COMPLETE. SHEET EVENTS: {count}")
    
    if count > 0:
        now_str = datetime.utcnow().strftime("%Y%m%d_%H%M")
        save_path = os.path.join(RESULTS_DIR, f"gmvs_state_{now_str}.csv")
        
        # Save Imperial Columns Only
        cols = ['time_tag', 'bt', 'B_baseline', 'CHI', 'SHEET_DEPTH']
        df_results[cols].to_csv(save_path, index=False)
        print(f">>> SHEET DATA SECURED: {save_path}")
        
        max_chi = df_results['CHI'].max()
        if max_chi >= CHI_SNAP_LIMIT:
            print(f"!!! ALERT: VACUUM FRACTURE (Chi={max_chi:.4f})")
        else:
            print(f"Status: Stable (Max Chi={max_chi:.4f})")
    else:
        print(">>> VACUUM QUIET.")

if __name__ == "__main__":
    run_extrapolation()
