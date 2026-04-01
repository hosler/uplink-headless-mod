"""HackerButton — tech-styled button with hover glow and corner accents."""
from kivy.uix.behaviors import ButtonBehavior, FocusBehavior
from kivy.uix.label import Label
from kivy.properties import ColorProperty, BooleanProperty
from kivy.graphics import Color, Rectangle, Line
from theme.colors import PRIMARY, TEXT_DIM, PANEL_BG


class HackerButton(ButtonBehavior, Label):
    button_color = ColorProperty(PRIMARY)
    hovered = BooleanProperty(False)

    def __init__(self, **kwargs):
        kwargs.setdefault('font_name', 'AeroMatics')
        kwargs.setdefault('font_size', '18sp')
        kwargs.setdefault('halign', 'center')
        kwargs.setdefault('valign', 'middle')
        super().__init__(**kwargs)
        self.bind(pos=self._redraw, size=self._redraw,
                  hovered=self._redraw, button_color=self._redraw,
                  disabled=self._redraw)
        self._redraw()

    def on_touch_down(self, touch):
        # Only consume the touch if it's actually on this button
        if self.collide_point(*touch.pos) and not self.disabled:
            # Don't steal focus from TextInput widgets
            return super().on_touch_down(touch)
        return False

    def on_touch_move(self, touch):
        # Update hover state based on touch position
        if self.collide_point(*touch.pos):
            self.hovered = True
        else:
            self.hovered = False
        return super().on_touch_move(touch)

    def _redraw(self, *_args):
        self.canvas.before.clear()
        x, y = self.pos
        w, h = self.size
        bc = self.button_color if not self.disabled else TEXT_DIM
        self.color = bc

        with self.canvas.before:
            # Background
            alpha = 0.15 if self.hovered else 0.05
            Color(*bc[:3], alpha)
            Rectangle(pos=(x, y), size=(w, h))
            # Border
            Color(*bc[:3], 0.6 if self.hovered else 0.3)
            Line(rectangle=[x, y, w, h], width=1.1)
            # Corner accents
            cl = min(8, w * 0.1)
            Color(*bc)
            Line(points=[x, y, x + cl, y], width=1.2)
            Line(points=[x, y, x, y + cl], width=1.2)
            Line(points=[x + w, y + h, x + w - cl, y + h], width=1.2)
            Line(points=[x + w, y + h, x + w, y + h - cl], width=1.2)
