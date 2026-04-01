"""BBSView — mission board with ACCEPT buttons."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle

from theme.colors import (PRIMARY, SECONDARY, TEXT_WHITE, TEXT_DIM, ROW_ALT,
                          PANEL_BG, SUCCESS, WARNING)
from widgets.hacker_button import HackerButton
from tabs.base_tab import BaseTabView


class BBSView(BaseTabView):
    tab_name = "BBS"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._title_label.text = "B U L L E T I N   B O A R D"
        self._missions = []
        self._selected = -1

        content = BoxLayout(orientation='vertical', spacing=4, padding=[20, 0, 20, 10],
                           size_hint=(1, 0.88), pos_hint={'center_x': 0.5, 'y': 0.02})

        # Header
        header = BoxLayout(size_hint_y=None, height=28, spacing=5)
        for text, w in [('DESCRIPTION', 0.4), ('EMPLOYER', 0.2), ('REWARD', 0.15),
                        ('DIFFICULTY', 0.1), ('', 0.15)]:
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

        # Detail panel
        self._detail = Label(text='', font_name='AeroMaticsLight', font_size='14sp',
                             color=TEXT_WHITE, size_hint_y=None, height=80, halign='left',
                             valign='top', padding=[10, 5])
        self._detail.bind(size=self._detail.setter('text_size'))
        content.add_widget(self._detail)

        self.add_widget(content)

    def on_activate(self):
        super().on_activate()
        if self.net:
            self.net.get_bbs()

    def on_state_update(self, state):
        missions = state.bbs_missions
        if missions != self._missions:
            self._missions = missions[:]
            self._rebuild()

    def _rebuild(self):
        self._list.clear_widgets()
        for i, m in enumerate(self._missions):
            desc = m.get("description", f"Mission {i+1}")[:35]
            employer = m.get("employer", "")[:20]
            reward = f"{m.get('payment', 0):,}c"
            diff = str(m.get("difficulty", "?"))

            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=36, spacing=5)
            with row.canvas.before:
                Color(*(ROW_ALT if i % 2 else PANEL_BG))
                bg = Rectangle(pos=row.pos, size=row.size)
            row.bind(pos=lambda w, *_, b=bg: setattr(b, 'pos', w.pos),
                     size=lambda w, *_, b=bg: setattr(b, 'size', w.size))

            desc_lbl = Label(text=desc, font_name='AeroMatics', font_size='14sp',
                             color=TEXT_WHITE, size_hint_x=0.4, halign='left')
            desc_lbl.bind(size=desc_lbl.setter('text_size'))
            emp_lbl = Label(text=employer, font_name='AeroMaticsLight', font_size='13sp',
                            color=TEXT_DIM, size_hint_x=0.2, halign='left')
            emp_lbl.bind(size=emp_lbl.setter('text_size'))
            rew_lbl = Label(text=reward, font_name='AeroMatics', font_size='13sp',
                            color=SUCCESS, size_hint_x=0.15)
            diff_lbl = Label(text=diff, font_name='AeroMatics', font_size='13sp',
                             color=WARNING, size_hint_x=0.1)

            accept_btn = HackerButton(text='ACCEPT', size_hint_x=0.15,
                                      font_size='12sp', button_color=SUCCESS)
            idx = i
            accept_btn.bind(on_release=lambda *_, i=idx: self._accept(i))

            # Click row to see details
            row.bind(on_touch_down=lambda w, t, i=idx: self._show_detail(i) if w.collide_point(*t.pos) else False)

            row.add_widget(desc_lbl)
            row.add_widget(emp_lbl)
            row.add_widget(rew_lbl)
            row.add_widget(diff_lbl)
            row.add_widget(accept_btn)
            self._list.add_widget(row)

    def _show_detail(self, idx):
        self._selected = idx
        if 0 <= idx < len(self._missions):
            m = self._missions[idx]
            self._detail.text = m.get("details", m.get("description", ""))

    def _accept(self, idx):
        if self.net:
            self.net.accept_mission(idx)
            if self.statusbar:
                self.statusbar.show("Mission accepted!")
