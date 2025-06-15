import kivy
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Line
from kivy.core.window import Window
from kivy.uix.label import Label
from kivy.properties import ListProperty, NumericProperty
from kivy.clock import Clock
import math
import mido

# Set window size
Window.size = (720, 720)

# MIDI setup
rtpmidi_port_name = 'rtpmidid:Network Export 128:0'  # Change if needed
try:
    outport = mido.open_output(rtpmidi_port_name)
except Exception as e:
    outport = None
    print(f"MIDI port not found: {e}")

# Distance mapping
MIN_DIST = 50
MAX_DIST = 600
CC_MIN = 0
CC_MAX = 127
CC_NUM = 3  # CC3

class DraggableBall(Widget):
    color = ListProperty([1, 0, 0])
    radius = NumericProperty(40)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dragging = False
        self.size = (self.radius*2, self.radius*2)
        self.center = kwargs.get('center', (100, 100))

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.dragging = True
            return True
        return False

    def on_touch_move(self, touch):
        if self.dragging:
            # Keep within window
            x = min(max(touch.x, self.radius), Window.width - self.radius)
            y = min(max(touch.y, self.radius), Window.height - self.radius)
            self.center = (x, y)
            return True
        return False

    def on_touch_up(self, touch):
        self.dragging = False
        return False

class PinchCCWidget(Widget):
    cc_value = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ball1 = DraggableBall(center=(200, 360), color=[0.2, 0.6, 1])
        self.ball2 = DraggableBall(center=(520, 360), color=[1, 0.4, 0.2])
        self.add_widget(self.ball1)
        self.add_widget(self.ball2)
        self.label = Label(text="CC3: 0", pos=(10, Window.height-50), font_size=32, color=(1,1,1,1))
        self.add_widget(self.label)
        Clock.schedule_interval(self.update, 1/30)
        self.last_cc = None

    def on_touch_down(self, touch):
        if self.ball1.on_touch_down(touch):
            return True
        if self.ball2.on_touch_down(touch):
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.ball1.on_touch_move(touch):
            return True
        if self.ball2.on_touch_move(touch):
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        self.ball1.on_touch_up(touch)
        self.ball2.on_touch_up(touch)
        return super().on_touch_up(touch)

    def update(self, dt):
        self.canvas.after.clear()
        with self.canvas.after:
            Color(1, 1, 1, 0.5)
            Line(points=[*self.ball1.center, *self.ball2.center], width=3)
        # Calculate distance
        dist = math.dist(self.ball1.center, self.ball2.center)
        # Map to CC value
        cc_val = int(
            min(max((dist - MIN_DIST) / (MAX_DIST - MIN_DIST), 0), 1) * (CC_MAX - CC_MIN) + CC_MIN
        )
        self.cc_value = cc_val
        self.label.text = f"CC3: {cc_val}"
        # Send MIDI CC if changed
        if cc_val != self.last_cc and outport is not None:
            msg = mido.Message('control_change', control=CC_NUM, value=cc_val)
            outport.send(msg)
            self.last_cc = cc_val

class PinchCCApp(App):
    def build(self):
        return PinchCCWidget()

if __name__ == '__main__':
    PinchCCApp().run() 