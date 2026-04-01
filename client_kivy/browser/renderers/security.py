"""SecurityRenderer — system security levels display."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle

from theme.colors import PRIMARY, SECONDARY, TEXT_WHITE, TEXT_DIM, ROW_ALT, PANEL_BG, SUCCESS, ALERT
from widgets.progress_bar import HackerProgressBar
from browser.renderers.base import BaseRenderer


class SecurityRenderer(BaseRenderer):
    """Renders GenericScreen Security — system security level indicators."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=8)
        self._list.bind(minimum_height=self._list.setter('height'))
        self._list.size_hint = (0.5, None)
        self._list.pos_hint = {'center_x': 0.5, 'top': 0.82}
        self.add_widget(self._list)
        self._last_buttons = []

    def on_state_update(self, state):
        buttons = state.buttons
        keys = [(b.get("name", ""), b.get("value", "")) for b in buttons]
        if keys == self._last_buttons:
            return
        self._last_buttons = keys
        self._list.clear_widgets()

        for btn in buttons:
            name = btn.get("name", "")
            caption = btn.get("caption", name)
            value = btn.get("value", "")
            if not name.startswith("securityscreen_"):
                continue
            label_text = caption.replace("securityscreen_", "").replace("_", " ").upper()

            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=32, spacing=10)
            lbl = Label(text=label_text, font_name='AeroMatics', font_size='14sp',
                        color=SECONDARY, size_hint_x=0.4, halign='right')
            lbl.bind(size=lbl.setter('text_size'))
            val = Label(text=value.upper(), font_name='AeroMatics', font_size='14sp',
                        color=SUCCESS if 'disabled' in value.lower() else ALERT,
                        halign='left')
            val.bind(size=val.setter('text_size'))
            row.add_widget(lbl)
            row.add_widget(val)
            self._list.add_widget(row)

        self._list.height = len(self._list.children) * 40
