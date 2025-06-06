import time
import board
import busio
import adafruit_mpr121
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque

# Setup I2C and MPR121
i2c = busio.I2C(board.SCL, board.SDA)
mpr121 = adafruit_mpr121.MPR121(i2c)

# Control parameters
alpha = 0.4          # Exponential smoothing (0.3-0.5 for responsive control)
deadband = 2         # Ignore changes smaller than this (reduces jitter)
scale_min = 0        # Minimum output value
scale_max = 127      # Maximum output value (MIDI range)

# Plot settings
window_seconds = 10  # Show last 10 seconds
sample_rate = 20     # Hz
maxlen = window_seconds * sample_rate

# Data storage
time_history = deque(maxlen=maxlen)
raw_history = deque(maxlen=maxlen)
smoothed_history = deque(maxlen=maxlen)
scaled_history = deque(maxlen=maxlen)

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
    print("\nStarting live plot...\n")

# Perform calibration
calibrate()

# Setup plot with two subplots
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

# Raw vs Smoothed plot
raw_line, = ax1.plot([], [], label='Raw Value', color='lightgray', linewidth=1)
smoothed_line, = ax1.plot([], [], label='Smoothed Value', color='blue', linewidth=2)
ax1.set_ylabel('Capacitance Value')
ax1.set_title('Raw vs Smoothed Touch Values')
ax1.legend()
ax1.grid(True, alpha=0.3)

# Scaled output plot (for synth control)
scaled_line, = ax2.plot([], [], label='Scaled Output (0-127)', color='red', linewidth=2)
ax2.set_ylabel('Control Value')
ax2.set_xlabel('Time (s)')
ax2.set_title('Synthesizer Control Output')
ax2.set_ylim(0, 127)
ax2.legend()
ax2.grid(True, alpha=0.3)

start_time = time.time()

def update_plot(frame):
    global smoothed_value, last_output
    
    now = time.time() - start_time
    time_history.append(now)
    
    # Read raw value
    try:
        raw_value = mpr121[0].raw_value
    except Exception:
        raw_value = touch_min if touch_min else 0
    
    # Apply exponential smoothing
    smoothed_value = exponential_smooth(raw_value, smoothed_value, alpha)
    
    # Apply deadband to reduce jitter
    smoothed_with_deadband = apply_deadband(smoothed_value, last_output, deadband)
    
    # Scale to control range (0-127 for MIDI)
    scaled_value = scale_value(smoothed_with_deadband, touch_min, touch_max, scale_min, scale_max)
    
    # Store data
    raw_history.append(raw_value)
    smoothed_history.append(smoothed_value)
    scaled_history.append(scaled_value)
    
    # Update plots
    raw_line.set_data(time_history, raw_history)
    smoothed_line.set_data(time_history, smoothed_history)
    scaled_line.set_data(time_history, scaled_history)
    
    # Auto-scale y-axis for raw/smoothed plot
    if len(raw_history) > 0:
        all_values = list(raw_history) + list(smoothed_history)
        y_min, y_max = min(all_values), max(all_values)
        margin = (y_max - y_min) * 0.1
        ax1.set_ylim(y_min - margin, y_max + margin)
    
    # Set x-axis limits
    ax1.set_xlim(max(0, now - window_seconds), now)
    ax2.set_xlim(max(0, now - window_seconds), now)
    
    last_output = smoothed_with_deadband
    
    return raw_line, smoothed_line, scaled_line

# Start animation
ani = animation.FuncAnimation(
    fig, update_plot, interval=1000 // sample_rate, blit=False, cache_frame_data=False
)

plt.tight_layout()
plt.show()

print("Plot closed. Touch control session ended.") 