"""CRT scanlines + vignette overlay — small texture scaled by GPU."""
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.graphics.texture import Texture


class CRTOverlay(Widget):
    """Fullscreen overlay with subtle scanlines and vignette.
    Generates a small (e.g. 128x128) texture and lets GPU scale it."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._tex = None
        self.bind(size=self._redraw, pos=self._redraw)
        self._build_texture()
        self._redraw()

    def on_touch_down(self, touch):
        return False  # Pass-through

    def on_touch_move(self, touch):
        return False

    def on_touch_up(self, touch):
        return False

    def _build_texture(self):
        # Small texture — GPU scales it to window size
        tw, th = 256, 256
        buf = bytearray(tw * th * 4)
        cx, cy = tw // 2, th // 2

        for y in range(th):
            # Scanline: every 3rd row
            scanline = 18 if y % 3 == 0 else 0
            for x in range(tw):
                idx = (y * tw + x) * 4
                # Vignette
                dx = (x - cx) / cx
                dy = (y - cy) / cy
                dist = (dx * dx + dy * dy) ** 0.5
                vignette = int(min(50, max(0, (dist - 0.5) * 90)))
                total = min(255, scanline + vignette)
                buf[idx] = 0
                buf[idx + 1] = 0
                buf[idx + 2] = 0
                buf[idx + 3] = total

        self._tex = Texture.create(size=(tw, th), colorfmt='rgba')
        self._tex.blit_buffer(bytes(buf), colorfmt='rgba', bufferfmt='ubyte')
        self._tex.mag_filter = 'nearest'  # Keep scanline sharpness

    def _redraw(self, *_args):
        self.canvas.clear()
        if self._tex:
            with self.canvas:
                Color(1, 1, 1, 1)
                Rectangle(texture=self._tex, pos=self.pos, size=self.size)
