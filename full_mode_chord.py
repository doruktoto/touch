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

class TouchSensorHandler:
    def __init__(self):
        self.current_scale = "Major_Ionian"
        self.last_note = None
        self.last_chord = None  # Track current chord notes
        self.running = True
        # Pitch offset functionality from 7-key-pitch.py
        self.pitch_offset = 0
        self.PITCH_MIN = -12
        self.PITCH_MAX = 12
        # Track previous state for pitch buttons
        self.touch_prev_7 = False
        self.touch_prev_8 = False

    def get_current_notes(self):
        return available_scales[self.current_scale]

    def set_scale(self, scale_name):
        self.current_scale = scale_name

    def get_pitch_offset(self):
        return self.pitch_offset

    def get_chord_notes(self, root_index):
        """Get triad chord notes (root, 3rd, 5th) from scale"""
        scale_notes = self.get_current_notes()
        chord_notes = []
        
        # Root note
        chord_notes.append(scale_notes[root_index] + self.pitch_offset)
        
        # 3rd (2 scale degrees up)
        third_index = (root_index + 2) % 7
        chord_notes.append(scale_notes[third_index] + self.pitch_offset)
        
        # 5th (4 scale degrees up)
        fifth_index = (root_index + 4) % 7
        fifth_note = scale_notes[fifth_index] + self.pitch_offset
        # If 5th wraps around, add octave
        if fifth_index < root_index:
            fifth_note += 12
        chord_notes.append(fifth_note)
        
        return chord_notes

    def send_chord_off(self, chord_notes):
        """Send note off for all chord notes"""
        if chord_notes and outport is not None:
            for note in chord_notes:
                msg = mido.Message('note_off', note=note, velocity=0)
                outport.send(msg)

    def send_chord_on(self, chord_notes):
        """Send note on for all chord notes"""
        if chord_notes and outport is not None:
            for note in chord_notes:
                msg = mido.Message('note_on', note=note, velocity=100)
                outport.send(msg)

    def run(self):
        while self.running:
            try:
                # Read touch state for pins 0-3 (keys)
                state = tuple(int(mpr121[i].value) for i in range(4))
                scale_index = touch_to_scale_index.get(state)
                
                # Read chord button (pin 9)
                chord_button = mpr121[9].value
                
                base_note = None
                chord_notes = None
                
                if scale_index is not None:
                    current_notes = self.get_current_notes()
                    base_note = current_notes[scale_index]
                    
                    if chord_button:
                        # Chord mode: get triad notes
                        chord_notes = self.get_chord_notes(scale_index)
                    else:
                        # Single note mode: apply pitch offset
                        base_note = base_note + self.pitch_offset

                # Read pitch up/down buttons (pins 7 and 8)
                touch_7 = mpr121[7].value
                touch_8 = mpr121[8].value

                # Pitch up (on rising edge)
                if touch_7 and not self.touch_prev_7:
                    if self.pitch_offset < self.PITCH_MAX:
                        self.pitch_offset += 1
                        print(f"Pitch up: {self.pitch_offset}")
                
                # Pitch down (on rising edge)
                if touch_8 and not self.touch_prev_8:
                    if self.pitch_offset > self.PITCH_MIN:
                        self.pitch_offset -= 1
                        print(f"Pitch down: {self.pitch_offset}")
                
                self.touch_prev_7 = touch_7
                self.touch_prev_8 = touch_8
                
                # Handle chord vs single note logic
                if chord_button and chord_notes:
                    # Chord mode
                    if chord_notes != self.last_chord:
                        # Turn off previous chord
                        if self.last_chord is not None:
                            self.send_chord_off(self.last_chord)
                        # Turn off any single note
                        if self.last_note is not None and outport is not None:
                            msg = mido.Message('note_off', note=self.last_note, velocity=0)
                            outport.send(msg)
                            self.last_note = None
                        
                        # Turn on new chord
                        if chord_notes is not None:
                            self.send_chord_on(chord_notes)
                            print(f"Chord On: {chord_notes} (Scale: {self.current_scale}, Offset: {self.pitch_offset})")
                        
                        self.last_chord = chord_notes
                else:
                    # Single note mode
                    if base_note != self.last_note:
                        # Turn off previous chord
                        if self.last_chord is not None:
                            self.send_chord_off(self.last_chord)
                            self.last_chord = None
                        # Turn off previous single note
                        if self.last_note is not None and outport is not None:
                            msg = mido.Message('note_off', note=self.last_note, velocity=0)
                            outport.send(msg)
                        
                        # Turn on new single note
                        if base_note is not None and outport is not None:
                            msg = mido.Message('note_on', note=base_note, velocity=100)
                            outport.send(msg)
                            print(f"Note On: {base_note} (Scale: {self.current_scale}, Offset: {self.pitch_offset})")
                        
                        self.last_note = base_note
                
                time.sleep(0.01)
            except Exception as e:
                print(f"Touch sensor error: {e}")
                time.sleep(0.1)

    def stop(self):
        self.running = False
        # Turn off last note and chord
        if self.last_note is not None and outport is not None:
            msg = mido.Message('note_off', note=self.last_note, velocity=0)
            outport.send(msg)
        if self.last_chord is not None:
            self.send_chord_off(self.last_chord)

class CircularScaleWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Initialize touch sensor handler
        self.touch_handler = TouchSensorHandler()
        
        # Create main layout
        main_layout = BoxLayout(orientation='vertical', spacing=20, padding=[80, 80, 80, 80])
        
        # Title (top center)
        title = Label(
            text="Scale Selection + Chords", 
            font_size=28, 
            size_hint_y=0.15,
            color=(1, 1, 1, 1),
            halign='center'
        )
        main_layout.add_widget(title)
        
        # Status info layout
        status_layout = BoxLayout(orientation='vertical', size_hint_y=0.25, spacing=10)
        
        # Current scale display
        self.current_scale_label = Label(
            text=f"Scale: {self.touch_handler.current_scale.replace('_', ' ')}", 
            font_size=20, 
            color=(1, 1, 1, 1),
            halign='center'
        )
        status_layout.add_widget(self.current_scale_label)
        
        # Pitch offset display
        self.pitch_offset_label = Label(
            text=f"Octave: {self.touch_handler.pitch_offset}", 
            font_size=18, 
            color=(1, 1, 1, 1),
            halign='center'
        )
        status_layout.add_widget(self.pitch_offset_label)
        
        # Chord instruction
        chord_info = Label(
            text="Hold Pin 9 + Pins 0-3 for chords", 
            font_size=16, 
            color=(0.8, 0.8, 0.8, 1),
            halign='center'
        )
        status_layout.add_widget(chord_info)
        
        main_layout.add_widget(status_layout)
        
        # Scale buttons in a 2x2 grid for better circular layout
        button_container = BoxLayout(orientation='vertical', size_hint_y=0.6, spacing=15)
        
        # First row of buttons
        row1 = BoxLayout(orientation='horizontal', spacing=15, size_hint_y=0.5)
        # Second row of buttons  
        row2 = BoxLayout(orientation='horizontal', spacing=15, size_hint_y=0.5)
        
        scale_names = list(available_scales.keys())
        
        # Distribute buttons across rows
        for i, scale_name in enumerate(scale_names):
            btn = Button(
                text=scale_name.replace('_', ' '), 
                font_size=16,
                background_color=(0.2, 0.4, 0.8, 1)
            )
            btn.bind(on_press=lambda x, scale=scale_name: self.select_scale(scale))
            
            if i < 2:
                row1.add_widget(btn)
            else:
                row2.add_widget(btn)
        
        button_container.add_widget(row1)
        button_container.add_widget(row2)
        main_layout.add_widget(button_container)
        
        self.add_widget(main_layout)
        
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
        # Update pitch offset display
        self.pitch_offset_label.text = f"Octave: {self.touch_handler.get_pitch_offset()}"
    
    def on_size(self, *args):
        # Draw the circular background
        self.canvas.before.clear()
        with self.canvas.before:
            Color(1, 1, 1, 1)  # White color
            Line(circle=(360, 360, 360), width=3)  # Center circle with radius 360

class FullModeChordApp(App):
    def build(self):
        return CircularScaleWidget()
    
    def on_stop(self):
        # Clean shutdown
        if hasattr(self.root, 'touch_handler'):
            self.root.touch_handler.stop()

if __name__ == '__main__':
    FullModeChordApp().run() 