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

# Colors for each pin
colors = {
    0: 'red', 1: 'blue', 2: 'green', 3: 'orange',
    4: 'purple', 5: 'brown', 10: 'magenta', 11: 'cyan'
}

# Setup plot
fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
plots = []
legends = []

for ax, group, title in zip(
    axes,
    [pins_group1, pins_group2, pins_group3],
    ["Pins 0,1,2,3", "Pins 10,11", "Pins 4,5"]
):
    lines = []
    labels = []
    for pin in group:
        (line,) = ax.plot([], [], label=f"Pin {pin}", color=colors[pin])
        lines.append(line)
        labels.append(f"Pin {pin}")
    ax.set_ylabel("Capacitance")
    ax.set_title(title)
    ax.legend()
    plots.append(lines)
    legends.append(labels)
axes[-1].set_xlabel("Time (s)")

start_time = time.time()
# Prompt user for output file name
output_file = input('Enter the filename to save the plot (e.g., touch_plot.png): ')
run_duration = 15  # seconds

def update(frame):
    now = time.time() - start_time
    if now >= run_duration:
        plt.savefig(output_file)
        plt.close(fig)
        return []
    time_history.append(now)
    for pin in range(12):
        try:
            val = mpr121[pin].raw_value
        except Exception:
            val = 0
        history[pin].append(val)
    # Update each subplot
    for ax, lines, group in zip(axes, plots, [pins_group1, pins_group2, pins_group3]):
        for i, pin in enumerate(group):
            lines[i].set_data(time_history, history[pin])
        ax.relim()
        ax.autoscale_view()
        ax.set_xlim(max(0, now - window_seconds), now)
    return [line for lines in plots for line in lines]

# With this:
ani = animation.FuncAnimation(
    fig, update, interval=1000 // sample_rate, blit=False, cache_frame_data=False
)
plt.tight_layout()
plt.show()

# Keep a reference to the animation to prevent garbage collection
global ani_ref
ani_ref = ani