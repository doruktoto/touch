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
from kivy.uix.slider import Slider
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.graphics import Color, Line

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

# Touch combination to scale index mapping
# Same as 7-key.py but mapped to scale indices 0-6
touch_to_scale_index = {
    (1, 0, 0, 0): 0,  # 0 -> scale[0] (first note)
    (0, 1, 0, 0): 1,  # 1 -> scale[1] (second note)
    (0, 0, 1, 0): 2,  # 2 -> scale[2] (third note)
    (0, 0, 0, 1): 3,  # 3 -> scale[3] (fourth note)
    (1, 1, 0, 0): 4,  # 0+1 -> scale[4] (fifth note)
    (0, 1, 1, 0): 5,  # 1+2 -> scale[5] (sixth note)
    (0, 0, 1, 1): 6,  # 2+3 -> scale[6] (seventh note)
}

class Arpeggiator:
    def __init__(self, get_notes, get_tempo):
        self.get_notes = get_notes  # function returning list of notes to arpeggiate
        self.get_tempo = get_tempo  # function returning tempo in BPM
        self.running = False
        self.thread = None
        self.last_note = None

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        if self.last_note is not None and outport is not None:
            msg = mido.Message('note_off', note=self.last_note, velocity=0)
            outport.send(msg)
            self.last_note = None

    def run(self):
        notes = self.get_notes()
        if not notes:
            return
        idx = 0
        while self.running:
            note = notes[idx % len(notes)]
            # Turn off previous note
            if self.last_note is not None and outport is not None:
                msg = mido.Message('note_off', note=self.last_note, velocity=0)
                outport.send(msg)
            # Turn on new note
            if outport is not None:
                msg = mido.Message('note_on', note=note, velocity=100)
                outport.send(msg)
            self.last_note = note
            idx += 1
            # Wait for next note (tempo in BPM)
            tempo = self.get_tempo()
            interval = 60.0 / max(tempo, 1)
            time.sleep(interval)
        # Turn off last note when stopped
        if self.last_note is not None and outport is not None:
            msg = mido.Message('note_off', note=self.last_note, velocity=0)
            outport.send(msg)
            self.last_note = None

class TouchSensorHandler:
    def __init__(self, get_arpeggiator_notes, get_arpeggiator_tempo):
        self.current_scale = "Major_Ionian"
        self.last_note = None
        self.last_chord = None  # Track current chord notes
        self.running = True
        self.pitch_offset = 0
        self.PITCH_MIN = -12
        self.PITCH_MAX = 12
        self.touch_prev_7 = False
        self.touch_prev_8 = False
        self.touch_prev_5 = False  # For pitch up
        self.arpeggiator = Arpeggiator(get_arpeggiator_notes, get_arpeggiator_tempo)
        self.arpeggiator_active = False
        self.chord_button = False
        self.last_pressed_state = (0, 0, 0, 0)

    def get_current_notes(self):
        return available_scales[self.current_scale]

    def set_scale(self, scale_name):
        self.current_scale = scale_name

    def get_pitch_offset(self):
        return self.pitch_offset

    def get_chord_notes(self, root_index):
        scale_notes = self.get_current_notes()
        chord_notes = []
        chord_notes.append(scale_notes[root_index] + self.pitch_offset)
        third_index = (root_index + 2) % 7
        chord_notes.append(scale_notes[third_index] + self.pitch_offset)
        fifth_index = (root_index + 4) % 7
        fifth_note = scale_notes[fifth_index] + self.pitch_offset
        if fifth_index < root_index:
            fifth_note += 12
        chord_notes.append(fifth_note)
        return chord_notes

    def run(self):
        while self.running:
            try:
                # Read touch state for pins 0-3 (keys)
                state = tuple(int(mpr121[i].value) for i in range(4))
                scale_index = touch_to_scale_index.get(state)
                chord_button = mpr121[9].value
                self.chord_button = chord_button
                base_note = None
                chord_notes = None
                if scale_index is not None:
                    current_notes = self.get_current_notes()
                    base_note = current_notes[scale_index]
                    if chord_button:
                        chord_notes = self.get_chord_notes(scale_index)
                    else:
                        base_note = base_note + self.pitch_offset
                # Read arpeggiator button (pin 7)
                touch_9 = mpr121[9].value
                # Read pitch down button (pin 8)
                touch_6 = mpr121[6].value
                # Read pitch up button (pin 5)
                touch_5 = mpr121[5].value
                # Arpeggiator logic
                if touch_9 and not self.touch_prev_9:
                    # Start arpeggiator
                    self.arpeggiator_active = True
                    self.arpeggiator.start()
                if not touch_9 and self.touch_prev_9:
                    # Stop arpeggiator
                    self.arpeggiator_active = False
                    self.arpeggiator.stop()
                self.touch_prev_9 = touch_9
                # Pitch up (on rising edge)
                if touch_5 and not self.touch_prev_5:
                    if self.pitch_offset < self.PITCH_MAX:
                        self.pitch_offset += 1
                        print(f"Pitch up: {self.pitch_offset}")
                self.touch_prev_5 = touch_5
                # Pitch down (on rising edge)
                if touch_6 and not self.touch_prev_6:
                    if self.pitch_offset > self.PITCH_MIN:
                        self.pitch_offset -= 1
                        print(f"Pitch down: {self.pitch_offset}")
                self.touch_prev_6 = touch_6
                # Only play notes if arpeggiator is not active
                if not self.arpeggiator_active:
                    if chord_button and chord_notes:
                        if chord_notes != self.last_chord:
                            if self.last_chord is not None:
                                self.send_chord_off(self.last_chord)
                            if self.last_note is not None and outport is not None:
                                msg = mido.Message('note_off', note=self.last_note, velocity=0)
                                outport.send(msg)
                                self.last_note = None
                            if chord_notes is not None:
                                self.send_chord_on(chord_notes)
                                print(f"Chord On: {chord_notes} (Scale: {self.current_scale}, Offset: {self.pitch_offset})")
                            self.last_chord = chord_notes
                    else:
                        if base_note != self.last_note:
                            if self.last_chord is not None:
                                self.send_chord_off(self.last_chord)
                                self.last_chord = None
                            if self.last_note is not None and outport is not None:
                                msg = mido.Message('note_off', note=self.last_note, velocity=0)
                                outport.send(msg)
                            if base_note is not None and outport is not None:
                                msg = mido.Message('note_on', note=base_note, velocity=100)
                                outport.send(msg)
                                print(f"Note On: {base_note} (Scale: {self.current_scale}, Offset: {self.pitch_offset})")
                            self.last_note = base_note
                time.sleep(0.01)
            except Exception as e:
                print(f"Touch sensor error: {e}")
                time.sleep(0.1)

    def send_chord_off(self, chord_notes):
        if chord_notes and outport is not None:
            for note in chord_notes:
                msg = mido.Message('note_off', note=note, velocity=0)
                outport.send(msg)

    def send_chord_on(self, chord_notes):
        if chord_notes and outport is not None:
            for note in chord_notes:
                msg = mido.Message('note_on', note=note, velocity=100)
                outport.send(msg)

    def stop(self):
        self.running = False
        if self.last_note is not None and outport is not None:
            msg = mido.Message('note_off', note=self.last_note, velocity=0)
            outport.send(msg)
        if self.last_chord is not None:
            self.send_chord_off(self.last_chord)
        self.arpeggiator.stop()

class CircularScaleWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tempo = 120  # Default BPM
        # Initialize touch sensor handler
        self.touch_handler = TouchSensorHandler(self.get_arpeggiator_notes, self.get_arpeggiator_tempo)
        # Title (top center) - positioned manually
        title = Label(
            text="CICADA", 
            font_size=24, 
            color=(1, 1, 1, 1),
            halign='center',
            text_size=(400, None),
            pos=(160, 600),  # Centered horizontally, near top
            size_hint=(None, None),
            size=(400, 40)
        )
        self.add_widget(title)
        # Current scale display - positioned in upper middle
        self.current_scale_label = Label(
            text=f"Scale: {self.touch_handler.current_scale.replace('_', ' ')}", 
            font_size=18, 
            color=(1, 1, 1, 1),
            halign='center',
            text_size=(300, None),
            pos=(210, 520),  # Centered horizontally
            size_hint=(None, None),
            size=(300, 30)
        )
        self.add_widget(self.current_scale_label)
        # Pitch offset display - positioned in center
        self.pitch_offset_label = Label(
            text=f"Octave: {self.touch_handler.pitch_offset}", 
            font_size=16, 
            color=(1, 1, 1, 1),
            halign='center',
            text_size=(200, None),
            pos=(260, 380),  # Center of screen
            size_hint=(None, None),
            size=(200, 25)
        )
        self.add_widget(self.pitch_offset_label)
        # Tempo slider for arpeggiator
        self.tempo_label = Label(
            text=f"Arp Tempo: {self.tempo} BPM",
            font_size=16,
            color=(1, 1, 1, 1),
            halign='center',
            text_size=(200, None),
            pos=(260, 340),
            size_hint=(None, None),
            size=(200, 25)
        )
        self.add_widget(self.tempo_label)
        self.tempo_slider = Slider(min=40, max=240, value=self.tempo, step=1, pos=(160, 300), size_hint=(None, None), size=(400, 40))
        self.tempo_slider.bind(value=self.on_tempo_change)
        self.add_widget(self.tempo_slider)
        # Scale buttons positioned in a 2x2 grid around center
        scale_names = list(available_scales.keys())
        button_positions = [
            (10, 335),  # Top-left
            (550, 335),  # Top-right  
            (280, 10),  # Bottom-left
            (280, 660)   # Bottom-right
        ]
        for i, scale_name in enumerate(scale_names):
            btn = Button(
                text=scale_name.replace('_', ' '), 
                font_size=14,
                background_color=(0.2, 0.4, 0.8, 1),
                pos=button_positions[i],
                size_hint=(None, None),
                size=(160, 50)
            )
            btn.bind(on_press=lambda x, scale=scale_name: self.select_scale(scale))
            self.add_widget(btn)
        # Chord instruction at bottom
        chord_info = Label(
            text="Hold Pin 9 + Pins 0-3 for chords, Hold Pin 7 for Arp", 
            font_size=14, 
            color=(0.8, 0.8, 0.8, 1),
            halign='center',
            text_size=(400, None),
            pos=(160, 120),  # Bottom center
            size_hint=(None, None),
            size=(400, 30)
        )
        self.add_widget(chord_info)
        # Start touch sensor thread
        self.sensor_thread = threading.Thread(target=self.touch_handler.run, daemon=True)
        self.sensor_thread.start()
        # Schedule UI updates
        Clock.schedule_interval(self.update_display, 0.1)
    def select_scale(self, scale_name):
        self.touch_handler.set_scale(scale_name)
        self.current_scale_label.text = f"Scale: {scale_name.replace('_', ' ')}"
        print(f"Scale changed to: {scale_name}")
    def update_display(self, dt):
        self.pitch_offset_label.text = f"Octave: {self.touch_handler.get_pitch_offset()}"
        self.tempo_label.text = f"Arp Tempo: {int(self.tempo_slider.value)} BPM"
    def on_tempo_change(self, instance, value):
        self.tempo = int(value)
    def get_arpeggiator_tempo(self):
        return self.tempo
    def get_arpeggiator_notes(self):
        # If chord button is held and a chord is available, return chord notes
        if self.touch_handler.chord_button and self.touch_handler.last_chord:
            return self.touch_handler.last_chord
        # Otherwise, if a single note is pressed, return that note as a list
        if self.touch_handler.last_note is not None:
            return [self.touch_handler.last_note]
        return []
    def on_size(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(1, 1, 1, 1)
            Line(circle=(360, 360, 360), width=3)
class FullModeArpApp(App):
    def build(self):
        return CircularScaleWidget()
    def on_stop(self):
        if hasattr(self.root, 'touch_handler'):
            self.root.touch_handler.stop()
if __name__ == '__main__':
    FullModeArpApp().run() 