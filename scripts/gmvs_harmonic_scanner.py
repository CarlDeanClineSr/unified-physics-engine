import pandas as pd
import matplotlib.pyplot as plt
import glob
import os
import numpy as np

# ==============================================================================
# GMVS HARMONIC SCANNER
# AUTHORITY: Dr. Carl Dean Cline Sr.
# PURPOSE: Detect rhythmic patterns (heartbeats) in Vacuum Fractures.
# ==============================================================================

RESULTS_DIR = "results"
EVIDENCE_DIR = "evidence"

def get_latest_result():
    files = glob.glob(os.path.join(RESULTS_DIR, 'gmvs_state_*.csv'))
    if not files: return None
    return max(files, key=os.path.getmtime)

def analyze_rhythm(file_path):
    print(f">>> SCANNING FOR HEARTBEAT: {os.path.basename(file_path)}")
    df = pd.read_csv(file_path)
    df['time_tag'] = pd.to_datetime(df['time_tag'])
    
    # 1. ISOLATE FRACTURES
    # We only care about the moments the limit broke.
    snaps = df[df['CHI'] > 0.15].copy()
    
    if len(snaps) < 2:
        print("!!! INSUFFICIENT DATA: Not enough fractures to establish a rhythm.")
        return

    # 2. CALCULATE THE "SILENCE" (Time between snaps)
    # This reveals the recharge time of the vacuum.
    snaps['interval'] = snaps['time_tag'].diff().dt.total_seconds() / 60.0 # In Minutes
    
    # Remove large gaps (e.g. gaps in data stream) to focus on the 'chatter'
    intervals = snaps['interval'].dropna()
    valid_intervals = intervals[intervals < 180] # Focus on 0-3 hour patterns
    
    if valid_intervals.empty:
        print("!!! NO RHYTHM DETECTED (Fractures are too sporadic).")
        return

    # 3. STATISTICAL SEARCH
    mean_beat = valid_intervals.mean()
    median_beat = valid_intervals.median()
    print(f">>> HEARTBEAT DETECTED.")
    print(f"    AVERAGE GAP: {mean_beat:.2f} minutes")
    print(f"    MEDIAN GAP:  {median_beat:.2f} minutes")

    # 4. VISUALIZE THE PULSE
    plt.style.use('dark_background')
    plt.figure(figsize=(10, 6))
    
    # Histogram of Time-Between-Snaps
    counts, bins, patches = plt.hist(valid_intervals, bins=30, color='#00ff00', edgecolor='black', alpha=0.7)
    
    # Mark the Imperial 0.9h Harmonic (54 minutes)
    plt.axvline(x=54, color='yellow', linestyle='--', linewidth=2, label='Imperial Harmonic (54 min)')
    plt.axvline(x=median_beat, color='red', linestyle='-', linewidth=2, label=f'Actual Median ({median_beat:.1f} min)')
    
    plt.xlabel('Time Between Fractures (Minutes)')
    plt.ylabel('Frequency of Occurrence')
    plt.title('GMVS FRACTURE RHYTHM ANALYSIS', fontweight='bold')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    save_path = os.path.join(EVIDENCE_DIR, "HARMONIC_HEARTBEAT.png")
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f">>> RHYTHM MAP SAVED: {save_path}")

if __name__ == "__main__":
    latest = get_latest_result()
    if latest:
        analyze_rhythm(latest)
    else:
        print("!!! NO DATA TO ANALYZE.")
