import os
import requests
import pandas as pd
from datetime import datetime, timedelta
import time

# ==============================================================================
# IMPERIAL PHYSICS ENGINE - SURFACE NODE INGEST
# AUTHORITY: COMMANDER CARL DEAN CLINE SR.
# TARGET: USGS GEOMAGNETISM NETWORK
# ==============================================================================

# TARGET NODES (STATIONS)
# BOU = Boulder (Mid-Latitude Baseline)
# FRD = Fredericksburg (Mid-Latitude)
# CMO = College, Alaska (High-Latitude/Auroral Lattice Stress)
STATIONS = ["BOU", "FRD", "CMO"]

OUTPUT_DIR = "data/raw/usgs"

def setup_directories():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

def fetch_station_data(station):
    """
    Pulls raw magnetometer data.
    Imperial Protocol: We look for magnetic tension elements (H, D, Z, F).
    """
    print(f">>> ACCESSING SURFACE NODE: {station}...")
    
    # Calculate Imperial Time Window (Last 24 Hours)
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=1)
    
    # Format for USGS API
    # Example: https://geomag.usgs.gov/ws/data/?id=BOU&type=variation&param=F&starttime=...
    base_url = "https://geomag.usgs.gov/ws/data/"
    
    params = {
        "id": station,
        "type": "variation",
        "format": "json",
        "sampling_period": 60, # 1-minute cadence
        "starttime": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "endtime": end_time.strftime("%Y-%m-%dT%H:%M:%S")
    }

    try:
        r = requests.get(base_url, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        
        # Parse the nested JSON structure USGS uses
        if 'times' in data and 'values' in data:
            df = pd.DataFrame()
            df['time_tag'] = data['times']
            
            # Extract components (X, Y, Z or H, D, Z depending on station config)
            for component in data['values']:
                col_name = list(component.keys())[0] # e.g., 'BOUH'
                # Clean column name to generic 'H', 'D', 'Z'
                clean_name = col_name.replace(station, "") 
                df[clean_name] = component[col_name]
            
            # Save Raw Artifact
            filename = f"{station}_harvest_{end_time.strftime('%Y%m%d_%H%M')}.csv"
            filepath = os.path.join(OUTPUT_DIR, filename)
            df.to_csv(filepath, index=False)
            print(f">>> {station} SECURED. {len(df)} DATA POINTS.")
            return True
            
    except Exception as e:
        print(f"!!! CONNECTION FAILURE ({station}): {e}")
        return False

if __name__ == "__main__":
    print(">>> IMPERIAL PHYSICS ENGINE: GROUND SEQUENCER ACTIVE <<<")
    setup_directories()
    
    success_count = 0
    for station in STATIONS:
        if fetch_station_data(station):
            success_count += 1
        time.sleep(1) # Polite pause between requests
        
    print(f">>> GROUND HARVEST COMPLETE. {success_count}/{len(STATIONS)} NODES REPORTING. <<<")
