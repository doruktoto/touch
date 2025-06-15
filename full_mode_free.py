import time
import board
import busio
import adafruit_mpr121
import mido
import json
import threading
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.clock import Clock

# Set window size for circular screen
Window.size = (720, 720)

# Setup I2C and MPR121
i2c = busio.I2C(board.SCL, board.SDA)
mpr121 = adafruit_mpr121.MPR121(i2c)

# Load scales from JSON
with open('scales.json', 'r') as f:
    scales_data = json.load(f)

available_scales = scales_data["C4_heptatonic_scales"]

# MIDI setup
rtpmidi_port_name = 'rtpmidid:Network Export 128:0'
try:
    outport = mido.open_output(rtpmidi_port_name)
except Exception as e:
    outport = None
    print(f"MIDI port not found: {e}")

# Pin indices for notes
NOTE_PINS = [0, 1, 2, 3, 7, 8, 9]

# Helper: generate all single and double pin combinations for free mode
from itertools import combinations
free_mode_combos = []
for n in [1, 2]:
    free_mode_combos.extend(combinations(NOTE_PINS, n))
# Map each combo to a chromatic note starting from 60 (C4)
free_mode_combo_to_note = {combo: 60 + i for i, combo in enumerate(free_mode_combos)}

class TouchSensorHandler:
    def __init__(self, get_mode, get_scale):
        self.get_mode = get_mode  # function to get current mode (free/scale)
        self.get_scale = get_scale  # function to get current scale name
        self.last_note = None
        self.running = True

    def get_current_notes(self):
        return available_scales[self.get_scale()]

    def run(self):
        while self.running:
            try:
                # Read touch state for all note pins
                pin_states = [int(mpr121[i].value) for i in NOTE_PINS]
                pressed_pins = [NOTE_PINS[i] for i, v in enumerate(pin_states) if v]

                note = None
                mode = self.get_mode()
                if mode == 'free':
                    # Free mode: use single/double combos
                    if 1 <= len(pressed_pins) <= 2:
                        combo = tuple(sorted(pressed_pins))
                        note = free_mode_combo_to_note.get(combo)
                else:
                    # Scale mode: only single pin, map to scale
                    if len(pressed_pins) == 1:
                        idx = NOTE_PINS.index(pressed_pins[0])
                        scale_notes = self.get_current_notes()
                        if idx < len(scale_notes):
                            note = scale_notes[idx]

                if note != self.last_note:
                    # Turn off previous note
                    if self.last_note is not None and outport is not None:
                        msg = mido.Message('note_off', note=self.last_note, velocity=0)
                        outport.send(msg)
                    # Turn on new note
                    if note is not None and outport is not None:
                        msg = mido.Message('note_on', note=note, velocity=100)
                        outport.send(msg)
                        print(f"Note On: {note} (Mode: {mode})")
                    self.last_note = note

                time.sleep(0.01)
            except Exception as e:
                print(f"Touch sensor error: {e}")
                time.sleep(0.1)

    def stop(self):
        self.running = False
        # Turn off last note
        if self.last_note is not None and outport is not None:
            msg = mido.Message('note_off', note=self.last_note, velocity=0)
            outport.send(msg)

class ModeScaleWidget(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.spacing = 10
        self.padding = 20

        self.current_scale = list(available_scales.keys())[0]
        self.free_mode = False

        # Title
        title = Label(text="Scale/Free Mode Selection", font_size=24, size_hint_y=0.15)
        self.add_widget(title)

        # Free Mode toggle button
        self.free_mode_btn = Button(text="Free Mode: OFF", font_size=18, size_hint_y=0.15, background_color=(0.5,0.5,0.5,1))
        self.free_mode_btn.bind(on_press=self.toggle_free_mode)
        self.add_widget(self.free_mode_btn)

        # Current scale display
        self.current_scale_label = Label(
            text=f"Current Scale: {self.current_scale}", 
            font_size=18, 
            size_hint_y=0.15
        )
        self.add_widget(self.current_scale_label)

        # Scale buttons
        button_layout = BoxLayout(orientation='vertical', spacing=10)
        for scale_name in available_scales.keys():
            btn = Button(
                text=scale_name.replace('_', ' '), 
                size_hint_y=0.15,
                font_size=16
            )
            btn.bind(on_press=lambda x, scale=scale_name: self.select_scale(scale))
            button_layout.add_widget(btn)
        self.add_widget(button_layout)

        # Start touch sensor thread
        self.touch_handler = TouchSensorHandler(self.get_mode, self.get_scale)
        self.sensor_thread = threading.Thread(target=self.touch_handler.run, daemon=True)
        self.sensor_thread.start()

    def toggle_free_mode(self, instance):
        self.free_mode = not self.free_mode
        self.free_mode_btn.text = f"Free Mode: {'ON' if self.free_mode else 'OFF'}"
        self.free_mode_btn.background_color = (0.2,0.8,0.2,1) if self.free_mode else (0.5,0.5,0.5,1)

    def select_scale(self, scale_name):
        self.current_scale = scale_name
        self.current_scale_label.text = f"Current Scale: {scale_name}"
        print(f"Scale changed to: {scale_name}")

    def get_mode(self):
        return 'free' if self.free_mode else 'scale'

    def get_scale(self):
        return self.current_scale

class FullModeFreeApp(App):
    def build(self):
        return ModeScaleWidget()
    def on_stop(self):
        if hasattr(self.root, 'touch_handler'):
            self.root.touch_handler.stop()

if __name__ == '__main__':
    FullModeFreeApp().run() 