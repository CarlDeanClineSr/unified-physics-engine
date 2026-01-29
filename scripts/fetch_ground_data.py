import requests
import pandas as pd
from datetime import datetime, timedelta
import os

# ==============================================================================
# USGS GROUND HARVESTER (CORRECTED)
# AUTHORITY: Dr. Carl Dean Cline Sr.
# PURPOSE: Extract NUMERIC DATA (nT), not Labels.
# ==============================================================================

# CONFIGURATION
# College (CMO) or Fredericksburg (FRD) are good baselines
OBSERVATORY = "CMO" 
OUTPUT_DIR = "data/raw/usgs"

def harvest_ground_data():
    print(f">>> TARGETING USGS OBSERVATORY: {OBSERVATORY}...")
    
    # 1. Define Time Window (Last 24 Hours)
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=1)
    
    # 2. Build URL (USGS JSON API)
    # We specifically request 'F' (Total Field) and 'H' (Horizontal)
    url = "https://geomag.usgs.gov/ws/data/"
    params = {
        "id": OBSERVATORY,
        "type": "variation",
        "elements": "F",
        "sampling_period": 60,
        "format": "json",
        "starttime": start_time.strftime("%Y-%m-%dT%H:%M:%S") + "Z",
        "endtime": end_time.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # 3. PARSE THE JSON (THE CRITICAL FIX)
        # We must dig into ['timeseries'][0]['values']
        if 'timeseries' not in data or not data['timeseries']:
            print("!!! ERROR: No data returned from USGS.")
            return

        # Extract the list of values
        # Each item looks like: {'date': '2026-01-29T...', 'value': 52104.3}
        records = data['timeseries'][0]['values']
        
        if not records:
            print("!!! ERROR: Data list is empty.")
            return

        # Convert to DataFrame
        df = pd.DataFrame(records)
        
        # RENAME COLUMNS (Standardize for the Engine)
        # The API gives 'date' and 'value'. We want 'time_tag' and 'F'.
        df.rename(columns={'date': 'time_tag', 'value': 'F'}, inplace=True)
        
        # Force Numeric on 'F' column (Removes any non-number junk)
        df['F'] = pd.to_numeric(df['F'], errors='coerce')
        
        # 4. SAVE
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)
            
        timestamp = end_time.strftime("%Y%m%d_%H%M")
        filename = f"{OBSERVATORY}_harvest_{timestamp}.csv"
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        df.to_csv(filepath, index=False)
        print(f">>> SUCCESS. GROUND DATA SECURED: {filepath}")
        print(f">>> SAMPLES: {len(df)}")
        print(f">>> SAMPLE DATA: {df.iloc[0]['F']} nT") # Print one number to prove it works

    except Exception as e:
        print(f"!!! HARVEST FAILED: {e}")

if __name__ == "__main__":
    harvest_ground_data()
