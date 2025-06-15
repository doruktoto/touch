import time
import board
import busio
import adafruit_mpr121
import rtmidi

# Setup I2C and MPR121
i2c = busio.I2C(board.SCL, board.SDA)
mpr121 = adafruit_mpr121.MPR121(i2c)

# Setup MIDI out
midiout = rtmidi.MidiOut()
available_ports = midiout.get_ports()
if available_ports:
    midiout.open_port(0)
else:
    midiout.open_virtual_port("TouchMIDI")

# Pin to MIDI note mapping
pin_to_note = {0: 60, 1: 62, 2: 64, 3: 65}  # C4, D4, E4, F4

# Track previous state
last_state = [False] * 4

try:
    while True:
        for idx, pin in enumerate([0, 1, 2, 3]):
            touched = mpr121[pin].value
            if touched and not last_state[idx]:
                # Note On
                midiout.send_message([0x90, pin_to_note[pin], 100])
            elif not touched and last_state[idx]:
                # Note Off
                midiout.send_message([0x80, pin_to_note[pin], 0])
            last_state[idx] = touched
        time.sleep(0.01)
except KeyboardInterrupt:
    pass
finally:
    del midiout