# ECG-to-Music
**The equivalent of EEG-to-Music, but for ECG.**

My attempt at creating an ECG-music interface, whereby a participant's EEG signals would create/modulate music in Ableton Live.

My aim is to create functional bridge scripts for both (1) live ECG-MIDI and ECG-guitar conversion and (2) ECG-MIDI and ECG-guitar conversion for pre-recorded EEG data. The goal would be to test these interfaces within a biofeedback meditation paradigm.


## Requirements
### Hardware
- PC/Laptop
- ECG device (if undertaking *live* ECG-to-music) with biosignal acquisition kit (e.g., BITalino)

### Software
- VScode (with Python and Jupyter extensions)
- Python
- [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html)
- Ableton Live

## Proposed Setup: Live ECG-to-MIDI
1. Record live EEG signals through OpenSignals
2. Run a Python bridge script to extract the live ECG signals and convert them to MIDI output
3. Direct the MIDI output into loopMIDI, creating a virtual port
4. Send the information from loopMIDI into Ableton Live
5. Once the output is in Ableton Live, notes will be played/parameters will be modulated according to BPM change threshold (currently: +/- 2 BPM)

### Roadmap
- [ ] Play script: Create a live bridge script that plays MIDI notes in accordance with each BPM change threshold
- [ ] Modulation script: Create a live bridge script that modulates a quality of a MIDI/guitar note (e.g., default note could be C4/participant could play notes themselves, where an increase or decrease in heart rate leads to more or less distortion/chorus of the tone)

### Project status
- Play script: Live MIDI works, with each R peak accurately detected, but BPM is calculated inaccurately in VScode terminal. Also, pitch does not currently change with BPM, most likely due to inaccuracies in BPM calculation.
- Modulation script: Coded, needs testing.

## Proposed Setup: Pre-recorded ECG-to-MIDI
1. Locate .csv file containing (clean) ECG data
2. Run a Python bridge script to extract the pre-recorded ECG signals and convert them to MIDI output
3. Direct the MIDI output into loopMIDI, creating a virtual port
4. Send the information from loopMIDI into Ableton Live
5. Once the output is in Ableton Live, notes will be played/parameters will be modulated according to BPM change threshold (currently: +/- 2 BPM)

### Roadmap
- [x] Create a pre-recorded bridge script that plays notes for each BPM change threshold, working for changes BOTH for increases and decreases of BPM
- [ ] Create a pre-recorded bridge script that modulates a quality (volume, distortion, pitch) of a note (e.g., default note could be C4, where an increase or decrease in heart rate leads to more or less gain/distortion of the tone, OR it could be that a pre-recorded piece of music is played, OR the participant could just play any live music with the pre-recorded ECG modulating the timbre)

## Usage: Live ECG-to-MIDI

(TBC)

## Usage: Pre-recorded ECG-to-MIDI
- Two versions of the pre-recorded bridge: (1) a "play" script, which converts ECG R peaks into notes and (2) a "modulation" script, which manipulates the timbre/quality of live music using the pre-recorded ECG signal.

(TBC)

## Ideas for both live and pre-recorded ECG-to-MIDI conversion
- Change in BPM = change in pitch of note
- Change in BPM = more or less gain/distiortion
- Make a particularly relaxing version for biofeedback meditation session(?) - find an appropriate instrument on Ableton (e.g., ambient synth, marimba, acoustic instrument). Look for instruments that can be arpeggiated (e.g., marimba)
- Maybe make a paradigm focusing on HRV? Would need to be highly-sensitive to intervals between heart beats. Although, cannot really see any useful psychological applications of this idea

## Troubleshooting
- Create a new loopMIDI port each time the PC/laptop is restarted
- In Ableton, in the Preferences page, under the relevant loopMIDI input port, ensure that the "Track" and "Remote" boxes are ticked
