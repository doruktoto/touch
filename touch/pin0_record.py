import time
import board
import busio
import adafruit_mpr121

# Setup I2C and MPR121
i2c = busio.I2C(board.SCL, board.SDA)
mpr121 = adafruit_mpr121.MPR121(i2c)

# Recording settings
record_duration = 10  # seconds
sample_rate = 20  # Hz (20 samples per second)
interval = 1.0 / sample_rate  # 0.05 seconds between samples

# Get filename from user
filename = input('Enter filename to save data (e.g., pin0_data.txt): ')

print(f"Recording Pin 0 values for {record_duration} seconds...")
print("Starting in 3 seconds...")
time.sleep(3)

# Start recording
start_time = time.time()
data = []

print("Recording started!")
while True:
    current_time = time.time() - start_time
    if current_time >= record_duration:
        break
    
    # Read pin 0 value
    try:
        pin0_value = mpr121[0].raw_value
    except Exception:
        pin0_value = 0
    
    # Store timestamp and value
    data.append(f"{current_time:.3f},{pin0_value}")
    print(f"Time: {current_time:.2f}s, Pin 0: {pin0_value}")
    
    time.sleep(interval)

print(f"\nRecording complete! Saving to {filename}...")

# Save data to file
with open(filename, 'w') as f:
    f.write("Time(s),Pin0_Value\n")  # Header
    for line in data:
        f.write(line + "\n")

print(f"Data saved to {filename}")
print(f"Total samples recorded: {len(data)}") 