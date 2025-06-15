import time
import board
import busio
import adafruit_mpr121
import mido
import json
import threading
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.clock import Clock

# Set window size
Window.size = (400, 600)

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

    def run(self):
        while self.running:
            try:
                # Read touch state for pins 0-3 (keys)
                state = tuple(int(mpr121[i].value) for i in range(4))
                scale_index = touch_to_scale_index.get(state)
                
                base_note = None
                if scale_index is not None:
                    current_notes = self.get_current_notes()
                    base_note = current_notes[scale_index]
                
                # Apply pitch offset to get final note
                note = base_note + self.pitch_offset if base_note is not None else None
                
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
                
                if note != self.last_note:
                    # Send Note Off for previous note
                    if self.last_note is not None and outport is not None:
                        msg = mido.Message('note_off', note=self.last_note, velocity=0)
                        outport.send(msg)
                    
                    # Send Note On for new note
                    if note is not None and outport is not None:
                        msg = mido.Message('note_on', note=note, velocity=100)
                        outport.send(msg)
                        print(f"Note On: {note} (Scale: {self.current_scale}, Offset: {self.pitch_offset})")
                    
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

class ScaleSelectionWidget(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.spacing = 10
        self.padding = 20
        
        # Initialize touch sensor handler
        self.touch_handler = TouchSensorHandler()
        
        # Title
        title = Label(text="Scale Selection", font_size=24, size_hint_y=0.15)
        self.add_widget(title)
        
        # Current scale display
        self.current_scale_label = Label(
            text=f"Current: {self.touch_handler.current_scale}", 
            font_size=18, 
            size_hint_y=0.15
        )
        self.add_widget(self.current_scale_label)
        
        # Pitch offset display
        self.pitch_offset_label = Label(
            text=f"Octave Offset: {self.touch_handler.pitch_offset}", 
            font_size=16, 
            size_hint_y=0.1
        )
        self.add_widget(self.pitch_offset_label)
        
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
        self.sensor_thread = threading.Thread(target=self.touch_handler.run, daemon=True)
        self.sensor_thread.start()
        
        # Schedule UI updates
        Clock.schedule_interval(self.update_pitch_display, 0.1)

    def select_scale(self, scale_name):
        self.touch_handler.set_scale(scale_name)
        self.current_scale_label.text = f"Current: {scale_name}"
        print(f"Scale changed to: {scale_name}")

    def update_pitch_display(self, dt):
        # Update pitch offset display
        self.pitch_offset_label.text = f"Octave Offset: {self.touch_handler.get_pitch_offset()}"

class FullModApp(App):
    def build(self):
        return ScaleSelectionWidget()
    
    def on_stop(self):
        # Clean shutdown
        if hasattr(self.root, 'touch_handler'):
            self.root.touch_handler.stop()

if __name__ == '__main__':
    FullModApp().run() 