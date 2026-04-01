"""Segmented neon progress bar."""
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ColorProperty
from kivy.graphics import Color, Rectangle
from theme.colors import SECONDARY, SUCCESS, WARNING, ALERT, PANEL_BG


class HackerProgressBar(Widget):
    value = NumericProperty(0)  # 0.0 to 1.0
    bar_color = ColorProperty(SUCCESS)
    auto_color = NumericProperty(0)  # if >0, auto-set color by value thresholds

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._redraw, size=self._redraw, value=self._redraw)
        self._redraw()

    def _redraw(self, *_args):
        self.canvas.clear()
        x, y = self.pos
        w, h = self.size
        v = max(0, min(1, self.value))

        # Auto-color based on value
        if self.auto_color:
            if v < 0.4:
                color = SUCCESS
            elif v < 0.7:
                color = WARNING
            else:
                color = ALERT
        else:
            color = self.bar_color

        with self.canvas:
            # Track
            Color(*PANEL_BG[:3], 0.8)
            Rectangle(pos=(x, y), size=(w, h))
            # Fill
            if v > 0:
                fill_w = int(w * v)
                Color(*color[:3], 0.7)
                Rectangle(pos=(x, y), size=(fill_w, h))
                # Segments
                seg_w = max(4, int(w * 0.015))
                gap = 2
                for sx in range(seg_w, fill_w, seg_w + gap):
                    Color(*PANEL_BG[:3], 0.6)
                    Rectangle(pos=(x + sx, y), size=(gap, h))
            # Border
            Color(*SECONDARY[:3], 0.5)
            from kivy.graphics import Line
            Line(rectangle=[x, y, w, h], width=1)
