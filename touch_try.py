import time
import board
import busio
import adafruit_mpr121

# Setup I2C and MPR121
i2c = busio.I2C(board.SCL, board.SDA)
mpr121 = adafruit_mpr121.MPR121(i2c)

# Pins to check
touch_pins = [0, 1, 2, 3, 5, 6, 7, 8, 9, 11]

print("Touch sensor test for pins:", touch_pins)
print("Press Ctrl+C to exit.")

try:
    while True:
        values = {}
        for pin in touch_pins:
            try:
                values[pin] = mpr121[pin].value
            except Exception as e:
                values[pin] = f"Error: {e}"
        print(" | ".join(f"Pin {pin}: {values[pin]}" for pin in touch_pins))
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nExiting touch test.")
