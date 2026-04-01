"""Vertical gradient background widget."""
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.graphics.texture import Texture
from theme.colors import BG_DARK, BG_LIGHT


class GradientBg(Widget):
    """Full-size vertical gradient from BG_DARK (top) to BG_LIGHT (bottom).
    Touch-transparent — never consumes input events."""

    def on_touch_down(self, touch):
        return False

    def on_touch_move(self, touch):
        return False

    def on_touch_up(self, touch):
        return False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._tex = None
        self.bind(size=self._rebuild)
        self._rebuild()

    def _rebuild(self, *_args):
        h = max(int(self.height), 2)
        # Build 1-pixel-wide vertical gradient
        buf = bytearray(h * 3)
        for y in range(h):
            # Kivy y=0 is bottom, so row 0 = BG_LIGHT, row h-1 = BG_DARK
            t = y / max(h - 1, 1)  # 0 at bottom, 1 at top
            r = int((BG_DARK[0] * t + BG_LIGHT[0] * (1 - t)) * 255)
            g = int((BG_DARK[1] * t + BG_LIGHT[1] * (1 - t)) * 255)
            b = int((BG_DARK[2] * t + BG_LIGHT[2] * (1 - t)) * 255)
            buf[y * 3] = r
            buf[y * 3 + 1] = g
            buf[y * 3 + 2] = b
        self._tex = Texture.create(size=(1, h), colorfmt='rgb')
        self._tex.blit_buffer(bytes(buf), colorfmt='rgb', bufferfmt='ubyte')
        self._tex.mag_filter = 'linear'
        self._redraw()

    def _redraw(self, *_args):
        self.canvas.before.clear()
        if self._tex:
            with self.canvas.before:
                Color(1, 1, 1, 1)
                Rectangle(texture=self._tex, pos=self.pos, size=self.size)
