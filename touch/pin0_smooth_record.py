import time
import board
import busio
import adafruit_mpr121
from collections import deque

# Setup I2C and MPR121
i2c = busio.I2C(board.SCL, board.SDA)
mpr121 = adafruit_mpr121.MPR121(i2c)

# Recording settings
record_duration = 10  # seconds
sample_rate = 20  # Hz
interval = 1.0 / sample_rate

# Smoothing parameters
window_size = 5  # Number of samples for moving average
alpha = 0.2      # Lower = more smoothing (0.1-0.3 recommended)

# Data storage for filters
moving_avg_buffer = deque(maxlen=window_size)
exp_avg_value = None

def moving_average_filter(new_value):
    """Simple moving average filter"""
    moving_avg_buffer.append(new_value)
    return sum(moving_avg_buffer) / len(moving_avg_buffer)

def exponential_moving_average(new_value):
    """Exponential moving average filter"""
    global exp_avg_value
    if exp_avg_value is None:
        exp_avg_value = new_value
    else:
        exp_avg_value = alpha * new_value + (1 - alpha) * exp_avg_value
    return exp_avg_value

# Get filename from user
filename = input('Enter filename to save smoothed data (e.g., pin0_smooth.txt): ')

print(f"Recording Pin 0 values for {record_duration} seconds with smoothing...")
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
    
    # Read raw value
    try:
        raw_value = mpr121[0].raw_value
    except Exception:
        raw_value = 0
    
    # Apply smoothing filters
    moving_avg = moving_average_filter(raw_value)
    exp_avg = exponential_moving_average(raw_value)
    
    # Store all values
    data.append(f"{current_time:.3f},{raw_value},{moving_avg:.1f},{exp_avg:.1f}")
    print(f"Time: {current_time:.2f}s | Raw: {raw_value} | MovAvg: {moving_avg:.1f} | ExpAvg: {exp_avg:.1f}")
    
    time.sleep(interval)

print(f"\nRecording complete! Saving to {filename}...")

# Save data to file
with open(filename, 'w') as f:
    f.write("Time(s),Raw_Value,Moving_Average,Exponential_Average\n")  # Header
    for line in data:
        f.write(line + "\n")

print(f"Data saved to {filename}")
print(f"Total samples recorded: {len(data)}")
print("\nSmoothing methods used:")
print(f"- Moving Average: window size = {window_size}")
print(f"- Exponential Average: alpha = {alpha} (lower = more smoothing)") 