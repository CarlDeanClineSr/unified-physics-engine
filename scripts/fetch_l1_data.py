import os
import json
import requests
import pandas as pd
from datetime import datetime

# ==============================================================================
# IMPERIAL PHYSICS ENGINE - L1 DATA INGEST
# AUTHORITY: COMMANDER CARL DEAN CLINE SR.
# TARGET: NOAA DSCOVR (L1 LATTICE MONITOR)
# ==============================================================================

# CONFIGURATION
# We target the 7-day JSON streams for high-cadence integrity checks.
URL_MAG = "https://services.swpc.noaa.gov/products/solar-wind/mag-7-day.json"
URL_PLASMA = "https://services.swpc.noaa.gov/products/solar-wind/plasma-7-day.json"

# OUTPUT DESTINATION
OUTPUT_DIR = "data/raw/dscovr"

def setup_directories():
    """Builds the local storage for the Lattice Data."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f">>> STORAGE CREATED: {OUTPUT_DIR}")

def fetch_stream(url, name):
    """
    Retrieves the raw data stream.
    NOTE: Standard Science calls this 'Solar Wind'. 
    Imperial Physics recognizes this as 'Lattice Update Stream'.
    """
    print(f">>> ESTABLISHING CONNECTION TO L1 FOR {name}...")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        print(f">>> {name} STREAM SECURED. PACKETS: {len(data)}")
        return data
    except Exception as e:
        print(f"!!! CONNECTION FAILURE ({name}): {e}")
        return None

def process_and_save(mag_data, plasma_data):
    """
    Aligns the Magnetic Tension (Mag) with the Logic Flow (Plasma).
    Saves to CSV for the 0.15 Analysis.
    """
    # Convert to DataFrames (Imperial Logic Matrix)
    # The first row is headers, so we slice [1:] and set columns=data[0]
    df_mag = pd.DataFrame(mag_data[1:], columns=mag_data[0])
    df_plasma = pd.DataFrame(plasma_data[1:], columns=plasma_data[0])

    # Convert Time stamps to Imperial Standard Time (UTC)
    df_mag['time_tag'] = pd.to_datetime(df_mag['time_tag'])
    df_plasma['time_tag'] = pd.to_datetime(df_plasma['time_tag'])

    # Merge on Time (Synchronize the Lattice Snapshot)
    # detailed inner join to ensure we have both Tension (B) and Density (N)
    merged = pd.merge(df_mag, df_plasma, on='time_tag', how='inner')

    # GENERATE FILENAME (Timestamped)
    now_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"dscovr_l1_harvest_{now_str}.csv"
    filepath = os.path.join(OUTPUT_DIR, filename)

    # SAVE
    merged.to_csv(filepath, index=False)
    print(f"\n>>> HARVEST COMPLETE. DATA SAVED TO: {filepath}")
    print(f">>> ROWS READY FOR ANALYSIS: {len(merged)}")
    
    # QUICK LOOK FOR 0.15 VIOLATIONS (PREVIEW)
    # Standard 'bt' is Total Magnetic Field. 
    # Standard 'density' is Proton Density.
    if 'bt' in merged.columns and 'density' in merged.columns:
        # Check first row
        b_val = float(merged.iloc[0]['bt'])
        print(f">>> LATEST TENSION (Bt): {b_val} nT")

if __name__ == "__main__":
    print(">>> IMPERIAL PHYSICS ENGINE: L1 INGEST SEQUENCE INITIATED <<<")
    setup_directories()
    
    # 1. FETCH MAGNETIC TENSION (MAG)
    mag_packet = fetch_stream(URL_MAG, "MAGNETIC_TENSION")
    
    # 2. FETCH LATTICE LOGIC (PLASMA)
    plasma_packet = fetch_stream(URL_PLASMA, "LATTICE_FLOW")
    
    # 3. SYNCHRONIZE AND STORE
    if mag_packet and plasma_packet:
        process_and_save(mag_packet, plasma_packet)
    else:
        print("!!! INGEST ABORTED: DATA STREAM MISSING !!!")
