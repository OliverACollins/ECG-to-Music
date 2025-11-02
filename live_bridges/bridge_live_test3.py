import numpy as np
from scipy.signal import find_peaks
import mido
import time
from pylsl import StreamInlet, resolve_streams
from mido.backends import rtmidi

# -------------------------------
# 1. MIDI output setup
# -------------------------------
available_ports = mido.get_output_names()
print("Available MIDI output ports:", available_ports)

midi_port_name = "ECG_MIDI 3"
if midi_port_name not in available_ports:
    raise RuntimeError(f"MIDI port '{midi_port_name}' not found.")

try:
    outport = mido.open_output(midi_port_name, backend=rtmidi)
except Exception as e:
    raise RuntimeError(f"Failed to open MIDI port '{midi_port_name}': {e}")

print(f"Using MIDI port: {midi_port_name}")

# -------------------------------
# 2. Find ECG/OpenSignals LSL stream
# -------------------------------
print("Scanning for available LSL streams...")
all_streams = resolve_streams()
if not all_streams:
    raise RuntimeError("No LSL streams found. Make sure LabRecorder is running.")

# Automatically pick the first stream with 'ECG' or 'OpenSignals' in its name
ecg_stream = None
for s in all_streams:
    name_lower = s.name().lower()
    if "ecg" in name_lower or "opensignals" in name_lower:
        ecg_stream = s
        break

if ecg_stream is None:
    raise RuntimeError("No ECG/OpenSignals stream found in LSL streams.")

inlet = StreamInlet(ecg_stream)
fs = int(ecg_stream.info().nominal_srate())
print(f"Connected to stream '{ecg_stream.name()}' with {ecg_stream.channel_count()} channels at {fs} Hz")

# -------------------------------
# 3. Define buffers and real-time parameters
# -------------------------------
buffer_size = fs * 10  # 10-second buffer
ecg_buffer = []
time_buffer = []

current_note = None
last_bpm = None
bpm_change_threshold = 3
note_glide_speed = 0.2
max_bpm_allowed = 200

# -------------------------------
# 4. MIDI mapping functions
# -------------------------------
min_note = 48  # C3
max_note = 84  # C6
min_velocity = 50
max_velocity = 70

def bpm_to_note_quantized(bpm, min_bpm, max_bpm):
    bpm = np.clip(bpm, min_bpm, max_bpm)
    norm = (bpm - min_bpm) / (max_bpm - min_bpm)
    return int(round(min_note + norm * (max_note - min_note)))

def bpm_to_velocity(bpm, min_bpm, max_bpm):
    bpm = np.clip(bpm, min_bpm, max_bpm)
    norm = (bpm - min_bpm) / (max_bpm - min_bpm)
    return int(min_velocity + (max_velocity - min_velocity) * np.sqrt(norm))

def moving_median(data, window=3):
    padded = np.pad(data, (window//2, window-1-window//2), mode='edge')
    return np.array([np.median(padded[i:i+window]) for i in range(len(data))])

# -------------------------------
# 5. Real-time ECG → MIDI loop
# -------------------------------
print("Starting real-time ECG to MIDI. Press Ctrl+C to stop.")

try:
    while True:
        sample, timestamp = inlet.pull_sample()
        ecg_value = sample[0]  # first channel assumed to be ECG
        ecg_buffer.append(ecg_value)
        time_buffer.append(timestamp)

        # Keep buffer fixed length
        if len(ecg_buffer) > buffer_size:
            ecg_buffer = ecg_buffer[-buffer_size:]
            time_buffer = time_buffer[-buffer_size:]

            # R-peak detection
            min_rr = 60 / max_bpm_allowed
            distance_samples = int(min_rr * fs)
            r_peaks, _ = find_peaks(np.array(ecg_buffer), height=0.8, distance=distance_samples)

            if len(r_peaks) >= 2:
                peak_times = np.array(time_buffer)[r_peaks]
                rr_intervals = np.diff(peak_times)
                smoothed_rr = moving_median(rr_intervals)
                smoothed_bpm = 60 / smoothed_rr
                min_bpm, max_bpm_val = np.min(smoothed_bpm), np.max(smoothed_bpm)

                bpm_value = smoothed_bpm[-1]
                rr_interval = smoothed_rr[-1]

                if last_bpm is None or abs(bpm_value - last_bpm) >= bpm_change_threshold:
                    target_note = bpm_to_note_quantized(bpm_value, min_bpm, max_bpm_val)
                    velocity = bpm_to_velocity(bpm_value, min_bpm, max_bpm_val)

                    if current_note is None:
                        current_note = target_note

                    # Glide towards target note
                    note_distance = target_note - current_note
                    glide_step = int(round(note_distance * note_glide_speed))
                    if glide_step == 0 and note_distance != 0:
                        glide_step = np.sign(note_distance)
                    note_to_play = current_note + glide_step
                    current_note = note_to_play

                    # Send MIDI
                    msg_on = mido.Message('note_on', note=note_to_play, velocity=velocity)
                    outport.send(msg_on)
                    print(f"note_on {note_to_play} at {peak_times[-1]:.3f}s")

                    time.sleep(rr_interval * 0.8)

                    msg_off = mido.Message('note_off', note=note_to_play, velocity=0)
                    outport.send(msg_off)
                    print(f"note_off {note_to_play}")

                    last_bpm = bpm_value

except KeyboardInterrupt:
    print("Stopped by user.")
