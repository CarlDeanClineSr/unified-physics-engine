```python
import os
import glob
import pandas as pd
import numpy as np
from datetime import datetime

# ==============================================================================
# GMVS EXTRAPOLATOR (ADAPTIVE IMPERIAL)
# AUTHORITY: Dr. Carl Dean Cline Sr.
# STATUS: AUTO-CALIBRATED (Median Baseline)
# ==============================================================================

RAW_DIR = "data/raw/dscovr"
RESULTS_DIR = "results"
CHI_LIMIT = 0.15

def get_latest_file(directory):
    list_of_files = glob.glob(os.path.join(directory, '*.csv'))
    if not list_of_files: return None
    return max(list_of_files, key=os.path.getctime)

def calculate_vacuum_geometry(df):
    """
    Adaptive Imperial Math.
    Median defines lattice rest state.
    """
    print(">>> MAPPING VACUUM SHEET GEOMETRY...")
    
    df['bt'] = pd.to_numeric(df['bt'], errors='coerce').fillna(0)
    
    # BASELINE (Normalized)
    baseline = df['bt'].median()
    if baseline == 0: baseline = 1.0 
    df['B_baseline'] = baseline
    
    # CHI (Geometric Tension)
    df['CHI'] = abs(df['bt'] - baseline) / baseline
    
    # SHEET DEPTH (Compression Index)
    r = df['bt'] / baseline
    df['SHEET_DEPTH'] = r / (1 + df['CHI'])
    
    return df

def run_extrapolation():
    print(">>> EXTRAPOLATOR ONLINE (MODE: ADAPTIVE)...")
    
    if not os.path.exists(RESULTS_DIR): os.makedirs(RESULTS_DIR)
        
    data_file = get_latest_file(RAW_DIR)
    if not data_file:
        print("!!! HALT: No Data.")
        return
        
    print(f"Source: {os.path.basename(data_file)}")
    df = pd.read_csv(data_file)
    
    df_processed = calculate_vacuum_geometry(df)
    df_results = df_processed.copy()
    count = len(df_results)
    
    if count > 0:
        now_str = datetime.utcnow().strftime("%Y%m%d_%H%M")
        save_path = os.path.join(RESULTS_DIR, f"gmvs_state_{now_str}.csv")
        
        cols = ['time_tag', 'bt', 'B_baseline', 'CHI', 'SHEET_DEPTH']
        existing_cols = [c for c in cols if c in df_results.columns]
        df_results[existing_cols].to_csv(save_path, index=False)
        
        print(f">>> STATE LOGGED: {save_path}")
        print(f">>> BASELINE: {df_results['B_baseline'].iloc[0]:.4f} nT")
        print(f">>> MAX CHI: {df_results['CHI'].max():.4f}")

if __name__ == "__main__":
    run_extrapolation()
```
