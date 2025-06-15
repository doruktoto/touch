import time
import board
import busio
import adafruit_mpr121
import mido

# Setup I2C and MPR121
i2c = busio.I2C(board.SCL, board.SDA)
mpr121 = adafruit_mpr121.MPR121(i2c)

# List available output ports
print("Available MIDI output ports:")
for port in mido.get_output_names():
    print(port)

# Replace with the exact name of your rtpmidid port from the list above
rtpmidi_port_name = 'rtpmidid:Network Export 128:0'
outport = mido.open_output(rtpmidi_port_name)

NOTE = 24  # C1
CHANNEL = 0
VELOCITY = 100

last_state = False

try:
    while True:
        touched = mpr121[0].value
        if touched and not last_state:
            # Note On
            msg = mido.Message('note_on', note=NOTE, velocity=VELOCITY, channel=CHANNEL)
            outport.send(msg)
            print("C1 Note On")
        elif not touched and last_state:
            # Note Off
            msg = mido.Message('note_off', note=NOTE, velocity=0, channel=CHANNEL)
            outport.send(msg)
            print("C1 Note Off")
        last_state = touched
        time.sleep(0.01)
except KeyboardInterrupt:
    pass
finally:
    outport.close()
