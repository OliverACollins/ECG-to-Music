import pandas as pd
import numpy as np
from scipy.signal import find_peaks
import mido
import time
import os

# -------------------------------
# 1. Set MIDI output port to ECG_MIDI 3
# -------------------------------
midi_port_name = "ECG_MIDI 3"

available_ports = mido.get_output_names()
print("Available MIDI output ports:", available_ports)

if midi_port_name not in available_ports:
    raise RuntimeError(f"MIDI port '{midi_port_name}' not found. Make sure loopMIDI is running.")

outport = mido.open_output(midi_port_name)
print(f"Opened MIDI output: {midi_port_name}")

# -------------------------------
# 2. Load ECG CSV
# -------------------------------
csv_file = 'bpm_decrease_ecg.csv'
if not os.path.exists(csv_file):
    raise FileNotFoundError(f"CSV file '{csv_file}' not found.")

df = pd.read_csv(csv_file)
print("CSV columns detected:", df.columns.tolist())

fs = 1000  # sampling rate
time_col = df['Time_s'].values if 'Time_s' in df.columns else np.arange(len(df)) / fs
ecg_signal = df['ECG'].values if 'ECG' in df.columns else df.iloc[:, 0].values

# -------------------------------
# 3. Detect R-peaks
# -------------------------------
max_bpm = 200
min_rr_seconds = 60 / max_bpm
distance_samples = int(min_rr_seconds * fs)

r_peaks, properties = find_peaks(ecg_signal, height=0.8, distance=distance_samples)
peak_heights = properties['peak_heights']

if len(r_peaks) < 2:
    raise ValueError("Not enough R-peaks detected. Try adjusting the threshold.")

peak_times = time_col[r_peaks]
rr_intervals = np.diff(peak_times)
print(f"Detected {len(peak_times)} R-peaks with amplitude >= 0.8.")

# -------------------------------
# 4. Smooth RR intervals with moving median
# -------------------------------
def moving_median(data, window_size=3):
    padded = np.pad(data, (window_size//2, window_size-1-window_size//2), mode='edge')
    return np.array([np.median(padded[i:i+window_size]) for i in range(len(data))])

smoothed_rr = moving_median(rr_intervals, window_size=3)
smoothed_bpm = 60 / smoothed_rr
min_bpm, max_bpm = np.min(smoothed_bpm), np.max(smoothed_bpm)

# -------------------------------
# 5. Define CC 113 mapping
# -------------------------------
min_cc113 = 0
max_cc113 = 127

def bpm_to_cc113(bpm):
    bpm = np.clip(bpm, min_bpm, max_bpm)
    norm = (bpm - min_bpm) / (max_bpm - min_bpm)
    return int(round(min_cc113 + norm * (max_cc113 - min_cc113)))

# -------------------------------
# 6. Send CC 113 messages smoothly for R-peaks >= 0.8
# -------------------------------
last_cc113 = 0
glide_speed = 0.1  # fraction of difference applied per step (smaller = smoother)

for i, peak_time in enumerate(peak_times):
    if peak_heights[i] < 0.8:
        # Skip peaks below threshold
        rr_interval = smoothed_rr[i] if i < len(smoothed_rr) else smoothed_rr[-1]
        time.sleep(rr_interval)
        continue

    bpm_value = smoothed_bpm[i] if i < len(smoothed_rr) else smoothed_bpm[-1]
    target_cc = bpm_to_cc113(bpm_value)

    # Smooth glide towards target CC
    cc_value = last_cc113
    while cc_value != target_cc:
        step = max(1, int(abs(target_cc - cc_value) * glide_speed))
        if cc_value < target_cc:
            cc_value = min(target_cc, cc_value + step)
        else:
            cc_value = max(target_cc, cc_value - step)
        cc_msg = mido.Message('control_change', control=113, value=cc_value, channel=0)
        outport.send(cc_msg)
        print(f"Sent CC113: {cc_value} at {peak_time:.3f}s")
        last_cc113 = cc_value
        # Short sleep to make glide perceptible
        time.sleep(0.01)

    # Wait until next R-peak
    rr_interval = smoothed_rr[i] if i < len(smoothed_rr) else smoothed_rr[-1]
    time.sleep(rr_interval)

print("Finished sending smooth CC113 from CSV BPM data.")
