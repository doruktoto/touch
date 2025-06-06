import time
import board
import busio
import adafruit_mpr121
from collections import deque

# Setup I2C and MPR121
i2c = busio.I2C(board.SCL, board.SDA)
mpr121 = adafruit_mpr121.MPR121(i2c)

# Control parameters
alpha = 0.4          # Exponential smoothing (0.3-0.5 for responsive control)
deadband = 2         # Ignore changes smaller than this (reduces jitter)
scale_min = 0        # Minimum output value
scale_max = 127      # Maximum output value (MIDI range)

# Calibration values (will be set during calibration)
touch_min = None
touch_max = None

# State variables
smoothed_value = None
last_output = None

def exponential_smooth(new_value, smoothed_value, alpha):
    """Responsive exponential smoothing"""
    if smoothed_value is None:
        return new_value
    return alpha * new_value + (1 - alpha) * smoothed_value

def apply_deadband(new_value, last_value, deadband):
    """Ignore small changes to reduce jitter"""
    if last_value is None:
        return new_value
    if abs(new_value - last_value) < deadband:
        return last_value
    return new_value

def scale_value(value, input_min, input_max, output_min, output_max):
    """Scale input range to output range"""
    if input_max == input_min:
        return output_min
    # Clamp input to range
    value = max(input_min, min(input_max, value))
    # Scale to 0-1, then to output range
    normalized = (value - input_min) / (input_max - input_min)
    return output_min + normalized * (output_max - output_min)

def calibrate():
    """Calibrate touch range"""
    global touch_min, touch_max
    
    print("=== CALIBRATION ===")
    print("1. Don't touch the sensor for 3 seconds...")
    time.sleep(1)
    
    # Get baseline (no touch)
    baseline_readings = []
    for i in range(30):  # 3 seconds at 10Hz
        try:
            val = mpr121[0].raw_value
            baseline_readings.append(val)
            print(f"Baseline reading {i+1}/30: {val}")
        except:
            baseline_readings.append(0)
        time.sleep(0.1)
    
    touch_min = sum(baseline_readings) / len(baseline_readings)
    
    print(f"\n2. Now touch the sensor firmly for 3 seconds...")
    time.sleep(1)
    
    # Get maximum touch
    touch_readings = []
    for i in range(30):  # 3 seconds at 10Hz
        try:
            val = mpr121[0].raw_value
            touch_readings.append(val)
            print(f"Touch reading {i+1}/30: {val}")
        except:
            touch_readings.append(0)
        time.sleep(0.1)
    
    touch_max = sum(touch_readings) / len(touch_readings)
    
    print(f"\nCalibration complete!")
    print(f"No touch (min): {touch_min:.1f}")
    print(f"Full touch (max): {touch_max:.1f}")
    print(f"Range: {touch_max - touch_min:.1f}")
    print("\nStarting control mode...\n")

# Perform calibration
calibrate()

print("Touch Control Mode")
print("Raw Value | Smoothed | Scaled (0-127) | Change")
print("-" * 50)

try:
    while True:
        # Read raw value
        try:
            raw_value = mpr121[0].raw_value
        except Exception:
            raw_value = touch_min if touch_min else 0
        
        # Apply exponential smoothing
        smoothed_value = exponential_smooth(raw_value, smoothed_value, alpha)
        
        # Apply deadband to reduce jitter
        smoothed_value = apply_deadband(smoothed_value, last_output, deadband)
        
        # Scale to control range (0-127 for MIDI)
        scaled_value = scale_value(smoothed_value, touch_min, touch_max, scale_min, scale_max)
        scaled_value = int(scaled_value)
        
        # Calculate change from last reading
        change = 0 if last_output is None else scaled_value - last_output
        change_str = f"+{change}" if change > 0 else str(change)
        
        # Display results
        print(f"{raw_value:8} | {smoothed_value:7.1f} | {scaled_value:10} | {change_str:6}")
        
        last_output = scaled_value
        time.sleep(0.05)  # 20Hz update rate
        
except KeyboardInterrupt:
    print("\nStopped control mode.")
    print("\nTips for better control:")
    print("- Adjust 'alpha' (0.3-0.5): higher = more responsive")
    print("- Adjust 'deadband' (1-5): higher = less jitter")
    print("- Re-calibrate if range seems wrong") 