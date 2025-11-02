import serial

ser = serial.Serial("COM7", 115200, timeout=1)
print("Listening for BITalino ECG data...")

while True:
    line = ser.readline().decode(errors='ignore').strip()
    if line:
        print("ECG raw:", line)


import numpy as np
import mido
import time
import serial
from scipy.signal import find_peaks, medfilt

# -------------------------------
# 1. Configure MIDI output
# -------------------------------
available_ports = mido.get_output_names()
print("Available MIDI output ports:", available_ports)

midi_port_name = None
for port in available_ports:
    if "ECG_MIDI 3" in port:
        midi_port_name = port
        break

if midi_port_name is None:
    raise RuntimeError("No MIDI port named 'ECG_MIDI 3' found. Please create one in LoopMIDI.")

print(f"✅ Using MIDI port: {midi_port_name}")
outport = mido.open_output(midi_port_name)

# -------------------------------
# 2. Serial port configuration
# -------------------------------
SERIAL_PORT = "COM7"  # Incoming BITalino port
BAUD_RATE = 115200
fs = 1000  # sampling rate (Hz)

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    print(f"✅ Connected to BITalino ECG on {SERIAL_PORT} at {BAUD_RATE} baud.\n")
except serial.SerialException as e:
    raise RuntimeError(f"❌ Could not open serial port {SERIAL_PORT}: {e}")

# -------------------------------
# 3. Test MIDI output
# -------------------------------
print("🎹 Sending test MIDI note...")
msg_on = mido.Message('note_on', note=60, velocity=100)
outport.send(msg_on)
time.sleep(0.5)
msg_off = mido.Message('note_off', note=60)
outport.send(msg_off)
print("✅ Test note sent. Make sure you hear a sound!\n")

# -------------------------------
# 4. Helper functions
# -------------------------------
def bpm_to_note_quantized(bpm, min_bpm, max_bpm, min_note=48, max_note=84):
    bpm = np.clip(bpm, min_bpm, max_bpm)
    norm = (bpm - min_bpm) / (max_bpm - min_bpm)
    note_float = min_note + norm * (max_note - min_note)
    return int(round(note_float))

def bpm_to_velocity(bpm, min_bpm, max_bpm, min_velocity=50, max_velocity=70):
    bpm = np.clip(bpm, min_bpm, max_bpm)
    norm = (bpm - min_bpm) / (max_bpm - min_bpm)
    velocity = int(min_velocity + (max_velocity - min_velocity) * np.sqrt(norm))
    return velocity

# -------------------------------
# 5. Processing parameters
# -------------------------------
buffer_size = fs * 5
ecg_buffer = np.zeros(buffer_size)
min_rr = 60 / 200
distance_samples = int(min_rr * fs)

current_note = None
last_bpm = None
bpm_change_threshold = 1.0
note_glide_speed = 0.2

print("🎶 Starting live ECG → MIDI mapping with debugging...")
print("💓 Press Ctrl+C to stop\n")

t0 = time.time()
sample_count = 0

while True:
    try:
        line = ser.readline().decode(errors='ignore').strip()
        if not line:
            continue

        try:
            ecg_value = float(line)
        except ValueError:
            continue

        # Print raw ECG for debugging
        print(f"ECG raw: {ecg_value}")

        # Update buffer
        ecg_buffer = np.roll(ecg_buffer, -1)
        ecg_buffer[-1] = ecg_value
        sample_count += 1

        # Process ~4 times per second
        if sample_count % int(fs / 4) == 0:
            mean_val = np.mean(ecg_buffer)
            std_val = np.std(ecg_buffer)
            # Adaptive threshold: mean + 0.3 * std
            threshold = mean_val + 0.3 * std_val

            peaks, _ = find_peaks(ecg_buffer, height=threshold, distance=distance_samples)
            peak_times = peaks / fs

            if len(peak_times) > 1:
                rr_intervals = np.diff(peak_times)
                rr_filtered = medfilt(rr_intervals, kernel_size=3)
                bpm_values = 60 / rr_filtered
                bpm_value = np.median(bpm_values[-3:]) if len(bpm_values) >= 3 else bpm_values[-1]

                if bpm_value < 30 or bpm_value > 200:
                    continue

                min_bpm = max(40, np.min(bpm_values))
                max_bpm = min(180, np.max(bpm_values))

                if last_bpm is None or abs(bpm_value - last_bpm) >= bpm_change_threshold:
                    target_note = bpm_to_note_quantized(bpm_value, min_bpm, max_bpm)
                    velocity = bpm_to_velocity(bpm_value, min_bpm, max_bpm)

                    if current_note is None:
                        current_note = target_note

                    note_distance = target_note - current_note
                    glide_step = int(round(note_distance * note_glide_speed))
                    if glide_step == 0 and note_distance != 0:
                        glide_step = np.sign(note_distance)
                    note_to_play = current_note + glide_step
                    current_note = note_to_play

                    # Print debug info before sending MIDI
                    print(f"BPM: {bpm_value:.1f}, Target Note: {target_note}, Velocity: {velocity}")

                    msg_on = mido.Message('note_on', note=note_to_play, velocity=velocity)
                    outport.send(msg_on)
                    time.sleep(0.1)
                    msg_off = mido.Message('note_off', note=note_to_play, velocity=0)
                    outport.send(msg_off)

                    last_bpm = bpm_value

    except KeyboardInterrupt:
        print("\n🛑 Stopping live ECG → MIDI stream...")
        ser.close()
        break
