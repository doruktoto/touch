import time
import board
import busio
import adafruit_mpr121
import mido

# Setup I2C and MPR121
i2c = busio.I2C(board.SCL, board.SDA)
mpr121 = adafruit_mpr121.MPR121(i2c)

# MIDI note mapping for C major scale
# 0: C4 (60), 1: D4 (62), 2: E4 (64), 3: F4 (65)
# 0+1: G4 (67), 1+2: A4 (69), 2+3: B4 (71)
key_map = {
    (1, 1, 0, 0): 67,  # 0+1 -> G4
    (0, 1, 1, 0): 69,  # 1+2 -> A4
    (0, 0, 1, 1): 71,  # 2+3 -> B4
    (1, 0, 0, 0): 60,  # 0 -> C4
    (0, 1, 0, 0): 62,  # 1 -> D4
    (0, 0, 1, 0): 64,  # 2 -> E4
    (0, 0, 0, 1): 65,  # 3 -> F4
}

# Find Bluetooth MIDI port
def find_bluetooth_midi_port():
    for port in mido.get_output_names():
        if 'Bluetooth' in port or 'bluetooth' in port:
            return port
    print('Available MIDI output ports:')
    for port in mido.get_output_names():
        print(port)
    raise RuntimeError('Bluetooth MIDI port not found! Make sure your Pi is advertising as a Bluetooth MIDI device and your Mac is connected.')

bluetooth_port_name = find_bluetooth_midi_port()
outport = mido.open_output(bluetooth_port_name)

last_note = None

try:
    while True:
        # Read touch state for pins 0-3
        state = tuple(int(mpr121[i].value) for i in range(4))
        note = key_map.get(state)
        if note != last_note:
            # Send Note Off for previous note
            if last_note is not None:
                msg = mido.Message('note_off', note=last_note, velocity=0)
                outport.send(msg)
            # Send Note On for new note
            if note is not None:
                msg = mido.Message('note_on', note=note, velocity=100)
                outport.send(msg)
                print(f"Note On: {note}")
            last_note = note
        time.sleep(0.01)
except KeyboardInterrupt:
    pass
finally:
    # Ensure last note is turned off
    if last_note is not None:
        msg = mido.Message('note_off', note=last_note, velocity=0)
        outport.send(msg)
    outport.close() 