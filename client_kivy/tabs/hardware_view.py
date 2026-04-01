"""HardwareView — hardware catalog with BUY buttons."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle

from theme.colors import (PRIMARY, SECONDARY, TEXT_WHITE, TEXT_DIM, ROW_ALT,
                          PANEL_BG, SUCCESS, ALERT)
from widgets.hacker_button import HackerButton
from tabs.base_tab import BaseTabView


class HardwareView(BaseTabView):
    tab_name = "Hardware"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._title_label.text = "H A R D W A R E   S H O P"
        self._hardware = []

        content = BoxLayout(orientation='vertical', spacing=4, padding=[20, 0, 20, 10],
                           size_hint=(1, 0.88), pos_hint={'center_x': 0.5, 'y': 0.02})

        # Header
        header = BoxLayout(size_hint_y=None, height=28, spacing=5)
        for text, w in [('COMPONENT', 0.5), ('COST', 0.25), ('', 0.25)]:
            lbl = Label(text=text, font_name='AeroMatics', font_size='13sp',
                        color=PRIMARY, size_hint_x=w, halign='left')
            lbl.bind(size=lbl.setter('text_size'))
            header.add_widget(lbl)
        content.add_widget(header)

        self._list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=2)
        self._list.bind(minimum_height=self._list.setter('height'))
        scroll = ScrollView()
        scroll.add_widget(self._list)
        content.add_widget(scroll)
        self.add_widget(content)

    def on_activate(self):
        super().on_activate()
        if self.net:
            self.net.get_hardware_list()

    def on_state_update(self, state):
        hw = state.hardware_list
        keys = [(h.get("title", ""), h.get("cost", 0)) for h in hw]
        old_keys = [(h.get("title", ""), h.get("cost", 0)) for h in self._hardware]
        if keys != old_keys or state.balance != getattr(self, '_last_bal', -1):
            self._hardware = hw[:]
            self._last_bal = state.balance
            self._rebuild(state.balance)

    def _rebuild(self, balance):
        self._list.clear_widgets()
        for i, hw in enumerate(self._hardware):
            title = hw.get("title", "?")
            desc = hw.get("description", "")[:40]
            cost = hw.get("cost", 0)
            can_afford = balance >= cost

            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=38, spacing=5)
            with row.canvas.before:
                Color(*(ROW_ALT if i % 2 else PANEL_BG))
                bg = Rectangle(pos=row.pos, size=row.size)
            row.bind(pos=lambda w, *_, b=bg: setattr(b, 'pos', w.pos),
                     size=lambda w, *_, b=bg: setattr(b, 'size', w.size))

            name_lbl = Label(text=title.upper(), font_name='AeroMatics', font_size='15sp',
                             color=TEXT_WHITE, size_hint_x=0.5, halign='left')
            name_lbl.bind(size=name_lbl.setter('text_size'))
            cost_lbl = Label(text=f"{cost:,}c", font_name='AeroMatics', font_size='15sp',
                             color=SUCCESS if can_afford else ALERT, size_hint_x=0.25,
                             halign='right')
            cost_lbl.bind(size=cost_lbl.setter('text_size'))

            buy_btn = HackerButton(text='BUY', font_size='13sp', size_hint_x=0.25,
                                   button_color=SUCCESS if can_afford else TEXT_DIM,
                                   disabled=not can_afford)
            buy_btn.bind(on_release=lambda *_, t=title: self._buy(t))

            row.add_widget(name_lbl)
            row.add_widget(cost_lbl)
            row.add_widget(buy_btn)
            self._list.add_widget(row)

    def _buy(self, title):
        if self.net:
            self.net.buy_hardware(title)
            if self.statusbar:
                self.statusbar.show(f"Purchased {title}")
