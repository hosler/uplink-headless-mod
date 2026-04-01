"""HackerPanel — decorative panel with corner accents and optional title tab."""
from kivy.uix.relativelayout import RelativeLayout
from kivy.properties import StringProperty, ColorProperty
from kivy.graphics import Color, Rectangle, Line
from theme.colors import PANEL_BG, SECONDARY, PRIMARY


class HackerPanel(RelativeLayout):
    title = StringProperty("")
    border_color = ColorProperty(SECONDARY)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._redraw, size=self._redraw,
                  title=self._redraw, border_color=self._redraw)
        self._title_label = None
        self._redraw()

    def _redraw(self, *_args):
        self.canvas.before.clear()
        x, y = self.pos
        w, h = self.size
        cl = min(15, w * 0.05, h * 0.05)  # corner accent length
        bc = self.border_color

        with self.canvas.before:
            # Background fill
            Color(*PANEL_BG, 0.78)
            Rectangle(pos=(x, y), size=(w, h))
            # Border
            Color(*bc[:3], 0.31)
            Line(rectangle=[x, y, w, h], width=1)
            # Corner accents
            Color(*bc)
            # Bottom-left (Kivy y=0 at bottom)
            Line(points=[x, y, x + cl, y], width=1.2)
            Line(points=[x, y, x, y + cl], width=1.2)
            # Bottom-right
            Line(points=[x + w, y, x + w - cl, y], width=1.2)
            Line(points=[x + w, y, x + w, y + cl], width=1.2)
            # Top-left
            Line(points=[x, y + h, x + cl, y + h], width=1.2)
            Line(points=[x, y + h, x, y + h - cl], width=1.2)
            # Top-right
            Line(points=[x + w, y + h, x + w - cl, y + h], width=1.2)
            Line(points=[x + w, y + h, x + w, y + h - cl], width=1.2)

        # Title tab (drawn above top-left corner)
        if self.title:
            if not self._title_label:
                from kivy.uix.label import Label
                self._title_label = Label(
                    text=self.title.upper(),
                    font_name="AeroMatics",
                    font_size='14sp',
                    color=PRIMARY,
                    size_hint=(None, None),
                    halign='left',
                )
                self._title_label.bind(texture_size=self._title_label.setter('size'))
                self.add_widget(self._title_label)
            self._title_label.text = self.title.upper()
            self._title_label.pos = (8, h - self._title_label.height - 8)
