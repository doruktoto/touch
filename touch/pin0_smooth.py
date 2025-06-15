import time
import board
import busio
import adafruit_mpr121
from collections import deque

# Setup I2C and MPR121
i2c = busio.I2C(board.SCL, board.SDA)
mpr121 = adafruit_mpr121.MPR121(i2c)

# Smoothing parameters
window_size = 5  # Number of samples for moving average
alpha = 0.3      # Smoothing factor for exponential moving average (0-1, lower = more smoothing)

# Data storage for filters
moving_avg_buffer = deque(maxlen=window_size)
median_buffer = deque(maxlen=window_size)
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

def median_filter(new_value):
    """Median filter - good for removing spikes"""
    median_buffer.append(new_value)
    sorted_values = sorted(median_buffer)
    n = len(sorted_values)
    if n % 2 == 0:
        return (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
    else:
        return sorted_values[n//2]

print("Pin 0 Capacitance with Noise Filtering")
print("Raw Value | Moving Avg | Exp Avg | Median Filter")
print("-" * 50)

try:
    while True:
        # Read raw value
        try:
            raw_value = mpr121[0].raw_value
        except Exception:
            raw_value = 0
        
        # Apply different filters
        moving_avg = moving_average_filter(raw_value)
        exp_avg = exponential_moving_average(raw_value)
        median_val = median_filter(raw_value)
        
        # Display results
        print(f"{raw_value:8} | {moving_avg:9.1f} | {exp_avg:7.1f} | {median_val:11.1f}")
        
        time.sleep(0.1)
        
except KeyboardInterrupt:
    print("\nStopped reading.") 