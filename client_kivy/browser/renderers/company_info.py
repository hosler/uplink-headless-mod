"""CompanyInfoRenderer — 2-column company card layout."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle

from theme.colors import PRIMARY, SECONDARY, TEXT_WHITE, TEXT_DIM, PANEL_BG, ROW_ALT
from browser.renderers.base import BaseRenderer


class CompanyInfoRenderer(BaseRenderer):
    """Renders GenericScreen CompanyInfo — 2-column cards with details."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._grid = GridLayout(cols=2, spacing=10, size_hint_y=None, padding=10)
        self._grid.bind(minimum_height=self._grid.setter('height'))
        scroll = ScrollView(size_hint=(0.7, 0.7), pos_hint={'center_x': 0.5, 'center_y': 0.4})
        scroll.add_widget(self._grid)
        self.add_widget(scroll)
        self._last_buttons = []

    def on_state_update(self, state):
        buttons = state.buttons
        keys = [(b.get("name", ""), b.get("value", "")) for b in buttons]
        if keys == self._last_buttons:
            return
        self._last_buttons = keys
        self._grid.clear_widgets()

        for btn in buttons:
            name = btn.get("name", "")
            caption = btn.get("caption", "")
            value = btn.get("value", "")
            if not name.startswith("companyscreen_"):
                continue
            label = name.replace("companyscreen_", "").replace("_", " ").upper()

            card = BoxLayout(orientation='vertical', size_hint_y=None, height=50, padding=5)
            with card.canvas.before:
                Color(*PANEL_BG, 0.8)
                bg = Rectangle(pos=card.pos, size=card.size)
            card.bind(pos=lambda w, *_, b=bg: setattr(b, 'pos', w.pos),
                      size=lambda w, *_, b=bg: setattr(b, 'size', w.size))

            key = Label(text=label, font_name='AeroMaticsLight', font_size='12sp',
                        color=SECONDARY, halign='left', size_hint_y=None, height=18)
            key.bind(size=key.setter('text_size'))
            val = Label(text=value or caption, font_name='AeroMatics', font_size='14sp',
                        color=TEXT_WHITE, halign='left', size_hint_y=None, height=24)
            val.bind(size=val.setter('text_size'))
            card.add_widget(key)
            card.add_widget(val)
            self._grid.add_widget(card)
