import time
import board
import busio
import adafruit_mpr121

# Setup I2C and MPR121
i2c = busio.I2C(board.SCL, board.SDA)
mpr121 = adafruit_mpr121.MPR121(i2c)

print("Reading capacitance values from Pin 0...")
print("Press Ctrl+C to stop")

try:
    while True:
        # Read raw capacitance value from pin 0
        pin0_value = mpr121[0].raw_value
        print(f"Pin 0: {pin0_value}")
        time.sleep(0.1)  # Wait 100ms between readings
except KeyboardInterrupt:
    print("\nStopped reading.") 