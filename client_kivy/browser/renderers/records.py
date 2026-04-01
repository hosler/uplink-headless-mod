"""RecordsRenderer — key-value database record view."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle

from theme.colors import PRIMARY, SECONDARY, TEXT_WHITE, TEXT_DIM, ROW_ALT, PANEL_BG
from browser.renderers.base import BaseRenderer


class RecordsRenderer(BaseRenderer):
    """Renders GenericScreen Records — DATABASE RECORD VIEW with key-value pairs."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=4)
        self._list.bind(minimum_height=self._list.setter('height'))
        scroll = ScrollView(size_hint=(0.55, 0.7), pos_hint={'center_x': 0.5, 'center_y': 0.42})
        scroll.add_widget(self._list)
        self.add_widget(scroll)
        self._last_buttons = []

    def on_state_update(self, state):
        buttons = state.buttons
        keys = [(b.get("name", ""), b.get("caption", "")) for b in buttons]
        if keys == self._last_buttons:
            return
        self._last_buttons = keys
        self._list.clear_widgets()

        for i, btn in enumerate(buttons):
            name = btn.get("name", "")
            caption = btn.get("caption", "")
            value = btn.get("value", "")
            if not name or name.startswith("_"):
                continue

            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=34)
            with row.canvas.before:
                Color(*(ROW_ALT if i % 2 else PANEL_BG))
                bg = Rectangle(pos=row.pos, size=row.size)
            row.bind(pos=lambda w, *_, b=bg: setattr(b, 'pos', w.pos),
                     size=lambda w, *_, b=bg: setattr(b, 'size', w.size))

            key_lbl = Label(text=(caption or name).upper(), font_name='AeroMatics',
                            font_size='14sp', color=SECONDARY, size_hint_x=0.4, halign='right')
            key_lbl.bind(size=key_lbl.setter('text_size'))
            val_lbl = Label(text=value, font_name='AeroMatics', font_size='14sp',
                            color=TEXT_WHITE, halign='left')
            val_lbl.bind(size=val_lbl.setter('text_size'))
            row.add_widget(key_lbl)
            row.add_widget(val_lbl)
            self._list.add_widget(row)
