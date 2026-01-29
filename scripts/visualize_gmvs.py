import pandas as pd
import matplotlib.pyplot as plt
import glob
import os

# ==============================================================================
# GMVS OSCILLOSCOPE (VISUALIZATION)
# AUTHORITY: Dr. Carl Dean Cline Sr.
# PURPOSE: Visual proof of Vacuum Fractures (Chi > 0.15)
# ==============================================================================

RESULTS_DIR = "results"
EVIDENCE_DIR = "evidence"

def get_latest_result():
    files = glob.glob(os.path.join(RESULTS_DIR, 'gmvs_state_*.csv'))
    if not files: return None
    # sort by modification time, latest first
    return max(files, key=os.path.getmtime)

def plot_fracture(file_path):
    print(f">>> LOADING EVIDENCE: {os.path.basename(file_path)}")
    df = pd.read_csv(file_path)
    
    # Setup Time
    df['time_tag'] = pd.to_datetime(df['time_tag'])
    
    # Setup Canvas
    plt.style.use('dark_background')
    fig, ax1 = plt.subplots(figsize=(12, 6))
    
    # PLOT 1: GMVS STRESS (SPACE) - RED
    color = '#ff4444' # Imperial Red
    ax1.set_xlabel('Universal Time (UTC)')
    ax1.set_ylabel('GMVS Stress (Chi)', color=color)
    ax1.plot(df['time_tag'], df['CHI'], color=color, linewidth=1.5, label='Vacuum Stress')
    ax1.tick_params(axis='y', labelcolor=color)
    
    # Draw the 0.15 Limit
    ax1.axhline(y=0.15, color='#ffff00', linestyle='--', linewidth=2, label='Imperial Limit (0.15)')
    
    # Highlight Fractures
    # We filter for where CHI actually exceeds the limit to plot the dots
    fractures = df[df['CHI'] > 0.15]
    if not fractures.empty:
        ax1.scatter(fractures['time_tag'], fractures['CHI'], color='white', s=20, zorder=5, label='Fracture Point')
        plt.title(f"WARNING: VACUUM FRACTURE DETECTED (Max: {df['CHI'].max():.4f})", color='red', fontweight='bold')
    else:
        plt.title(f"GMVS STATUS: STABLE (Max: {df['CHI'].max():.4f})", color='#00ff00')

    # Grid
    plt.grid(True, alpha=0.3)
    plt.legend(loc='upper right')
    
    # Save
    if not os.path.exists(EVIDENCE_DIR): os.makedirs(EVIDENCE_DIR)
    
    # Use a fixed name for the latest, or timestamped
    filename = f"SNAP_EVIDENCE_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.png"
    save_path = os.path.join(EVIDENCE_DIR, filename)
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f">>> VISUAL PROOF SAVED: {save_path}")

if __name__ == "__main__":
    latest = get_latest_result()
    if latest:
        plot_fracture(latest)
    else:
        print("!!! NO RESULTS TO PLOT. RUN EXTRAPOLATOR FIRST.")
