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

# Pin groups
pins_group1 = [0, 1, 2, 3]
pins_group2 = [10, 11]
pins_group3 = [4, 5]

# Plot settings
window_seconds = 30
sample_rate = 20  # Hz
maxlen = window_seconds * sample_rate

# Data storage
history = {pin: deque(maxlen=maxlen) for pin in range(12)}
time_history = deque(maxlen=maxlen)

# Colors for each pin (assign unique colors for 12 pins)
colors = {
    0: 'red', 1: 'blue', 2: 'green', 3: 'orange',
    4: 'purple', 5: 'brown', 6: 'pink', 7: 'olive',
    8: 'cyan', 9: 'black', 10: 'magenta', 11: 'grey'
}

# Setup plot (single plot for all pins)
fig, ax = plt.subplots(figsize=(12, 6))
lines = []
for pin in range(12):
    (line,) = ax.plot([], [], label=f"Pin {pin}", color=colors[pin])
    lines.append(line)
ax.set_ylabel("Capacitance")
ax.set_xlabel("Time (s)")
ax.set_title("Capacitance values for pins 0-11")
ax.legend()

start_time = time.time()
# Prompt user for output file name
output_file = input('Enter the filename to save the plot (e.g., touch_plot.png): ')
run_duration = 15  # seconds

save_done = False

def update(frame):
    global save_done
    now = time.time() - start_time
    if now >= run_duration:
        if not save_done:
            plt.savefig(output_file)
            save_done = True
            ani.event_source.stop()  # Stop the animation gracefully
        return []
    time_history.append(now)
    for pin in range(12):
        try:
            val = mpr121[pin].raw_value
        except Exception:
            val = 0
        history[pin].append(val)
    for pin, line in enumerate(lines):
        line.set_data(time_history, history[pin])
    ax.relim()
    ax.autoscale_view()
    ax.set_xlim(max(0, now - window_seconds), now)
    ax.set_ylim(0, 1000)  # Set a default y-axis range for visibility
    return lines

ani = animation.FuncAnimation(
    fig, update, interval=400 // sample_rate, blit=False, cache_frame_data=False
)
plt.tight_layout()
plt.show()

# Keep a reference to the animation to prevent garbage collection
global ani_ref
ani_ref = ani