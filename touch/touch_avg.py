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

# Colors for each pin (all light grey for live readings)
colors = {pin: 'lightgrey' for pin in range(12)}
avg_colors = ['red', 'blue', 'green']  # Red for plot 1, blue for plot 2, green for plot 3

# Setup plot
fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
plots = []
avg_lines = []  # To store average lines for each group
legends = []

for ax, group, title, avg_color in zip(
    axes,
    [pins_group1, pins_group2, pins_group3],
    ["Pins 0,1,2,3", "Pins 10,11", "Pins 4,5"],
    avg_colors
):
    lines = []
    labels = []
    for pin in group:
        (line,) = ax.plot([], [], label=f"Pin {pin}", color=colors[pin], linewidth=1)
        lines.append(line)
        labels.append(f"Pin {pin}")
    # Add average line
    (avg_line,) = ax.plot([], [], label="Average", color=avg_color, linewidth=2)
    avg_lines.append(avg_line)
    ax.set_ylabel("Capacitance")
    ax.set_title(title)
    ax.legend()
    ax.set_ylim(0, 1000)  # Set default y-axis range for visibility
    plots.append(lines)
    legends.append(labels)
axes[-1].set_xlabel("Time (s)")

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
            plt.close(fig)
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
    for ax, lines, group, avg_line in zip(axes, plots, [pins_group1, pins_group2, pins_group3], avg_lines):
        for i, pin in enumerate(group):
            lines[i].set_data(time_history, history[pin])
        # Only plot average if all pins in the group have at least one value
        if all(len(history[pin]) > 0 for pin in group):
            avg_series = [sum(vals)/len(vals) for vals in zip(*[history[pin] for pin in group])]
            avg_line.set_data(time_history, avg_series)
        ax.relim()
        ax.autoscale_view()
        ax.set_xlim(max(0, now - window_seconds), now)
    return [line for lines in plots for line in lines] + avg_lines

ani = animation.FuncAnimation(
    fig, update, interval=1000 // sample_rate, blit=False, cache_frame_data=False
)
plt.tight_layout()
plt.show()

# Keep a reference to the animation to prevent garbage collection
global ani_ref
ani_ref = ani