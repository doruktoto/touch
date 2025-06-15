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

# CC mapping
CC_MIN = 0
CC_MAX = 127
DIST_MAX = 720
CC3_NUM = 3
CC4_NUM = 4

class DraggableBall(Widget):
    color = ListProperty([1, 0, 0])
    radius = NumericProperty(30)
    cc_num = NumericProperty(3)
    anchor = ListProperty([0, 360])
    cc_value = NumericProperty(0)
    last_cc = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.dragging = False
        self.size = (self.radius*2, self.radius*2)
        self.center = kwargs.get('center', (100, 100))
        self.color = kwargs.get('color', [1, 0, 0])
        self.cc_num = kwargs.get('cc_num', 3)
        self.anchor = kwargs.get('anchor', [0, 360])
        self.label = Label(text="", font_size=20, color=(1,1,1,1), size_hint=(None, None), size=(80, 30))
        self.add_widget(self.label)

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

    def update_cc(self):
        dist = math.dist(self.center, self.anchor)
        cc_val = int(min(max(dist / DIST_MAX, 0), 1) * (CC_MAX - CC_MIN) + CC_MIN)
        self.cc_value = cc_val
        self.label.text = f"CC{self.cc_num}: {cc_val}"
        self.label.center = (self.center[0], self.center[1] + 50)
        if outport is not None and cc_val != self.last_cc:
            msg = mido.Message('control_change', control=self.cc_num, value=cc_val)
            outport.send(msg)
            self.last_cc = cc_val

class PinchDualCCWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ball 1: left, CC3, anchor (0,360)
        self.ball1 = DraggableBall(center=(100, 360), color=[0.2, 0.6, 1], cc_num=3, anchor=[0, 360])
        # Ball 2: right, CC4, anchor (720,360)
        self.ball2 = DraggableBall(center=(620, 360), color=[1, 0.4, 0.2], cc_num=4, anchor=[720, 360])
        self.add_widget(self.ball1)
        self.add_widget(self.ball2)
        Clock.schedule_interval(self.update, 1/30)

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
        self.canvas.before.clear()
        with self.canvas.before:
            Color(1, 1, 1, 1)
            Line(circle=(360, 360, 360), width=2)
        self.ball1.update_cc()
        self.ball2.update_cc()

class PinchDualCCApp(App):
    def build(self):
        return PinchDualCCWidget()

if __name__ == '__main__':
    PinchDualCCApp().run() 