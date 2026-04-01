"""LANRenderer — LAN topology visualization."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle

from theme.colors import PRIMARY, SECONDARY, TEXT_WHITE, TEXT_DIM, ROW_ALT, PANEL_BG, SUCCESS
from widgets.hacker_button import HackerButton
from browser.renderers.base import BaseRenderer


class LANRenderer(BaseRenderer):
    """Renders LAN topology — list of LAN systems."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=4)
        self._list.bind(minimum_height=self._list.setter('height'))
        scroll = ScrollView(size_hint=(0.5, 0.65), pos_hint={'center_x': 0.5, 'center_y': 0.42})
        scroll.add_widget(self._list)
        self.add_widget(scroll)
        self._last_systems = []

    def on_state_update(self, state):
        systems = state.lan_data.get("systems", [])
        keys = [s.get("type", "") for s in systems]
        if keys == self._last_systems:
            return
        self._last_systems = keys
        self._list.clear_widgets()

        for i, sys_info in enumerate(systems):
            sys_type = sys_info.get("type", "Unknown")
            status = sys_info.get("status", "")

            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=38, spacing=8)
            with row.canvas.before:
                Color(*(ROW_ALT if i % 2 else PANEL_BG))
                bg = Rectangle(pos=row.pos, size=row.size)
            row.bind(pos=lambda w, *_, b=bg: setattr(b, 'pos', w.pos),
                     size=lambda w, *_, b=bg: setattr(b, 'size', w.size))

            idx_lbl = Label(text=f"[{i}]", font_name='AeroMatics', font_size='14sp',
                            color=SECONDARY, size_hint_x=None, width=40)
            type_lbl = Label(text=sys_type.upper(), font_name='AeroMatics', font_size='15sp',
                             color=TEXT_WHITE, halign='left')
            type_lbl.bind(size=type_lbl.setter('text_size'))
            status_lbl = Label(text=status.upper(), font_name='AeroMaticsLight', font_size='13sp',
                               color=SUCCESS if 'active' in status.lower() else TEXT_DIM,
                               size_hint_x=None, width=100)

            row.add_widget(idx_lbl)
            row.add_widget(type_lbl)
            row.add_widget(status_lbl)
            self._list.add_widget(row)
