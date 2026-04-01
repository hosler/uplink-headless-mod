"""MissionsView — two-panel mission list + details."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle

from theme.colors import (PRIMARY, SECONDARY, TEXT_WHITE, TEXT_DIM, ROW_ALT,
                          PANEL_BG, SUCCESS, WARNING, ALERT)
from widgets.hacker_button import HackerButton
from tabs.base_tab import BaseTabView


class MissionsView(BaseTabView):
    tab_name = "Missions"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._title_label.text = "M I S S I O N S"
        self._selected = -1
        self._missions = []

        panels = BoxLayout(orientation='horizontal', spacing=10, padding=[20, 0, 20, 10],
                          size_hint=(1, 0.88), pos_hint={'center_x': 0.5, 'y': 0.02})

        # Left: mission list
        left = BoxLayout(orientation='vertical', size_hint_x=0.45, spacing=4)
        header = BoxLayout(size_hint_y=None, height=28)
        for text, w in [('MISSION', 0.6), ('REWARD', 0.2), ('DIFF', 0.2)]:
            lbl = Label(text=text, font_name='AeroMatics', font_size='13sp',
                        color=PRIMARY, size_hint_x=w, halign='left')
            lbl.bind(size=lbl.setter('text_size'))
            header.add_widget(lbl)
        left.add_widget(header)

        self._mission_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=2)
        self._mission_list.bind(minimum_height=self._mission_list.setter('height'))
        scroll = ScrollView()
        scroll.add_widget(self._mission_list)
        left.add_widget(scroll)

        # Right: details
        right = BoxLayout(orientation='vertical', size_hint_x=0.55, padding=[10, 0], spacing=6)
        self._detail_title = Label(text='Select a mission', font_name='AeroMatics',
                                   font_size='18sp', color=PRIMARY, size_hint_y=None, height=30,
                                   halign='left')
        self._detail_title.bind(size=self._detail_title.setter('text_size'))
        self._detail_body = Label(text='', font_name='AeroMaticsLight', font_size='15sp',
                                  color=TEXT_WHITE, halign='left', valign='top',
                                  size_hint_y=None, markup=False)
        self._detail_body.bind(texture_size=lambda *_: setattr(
            self._detail_body, 'height', max(200, self._detail_body.texture_size[1])))

        detail_scroll = ScrollView()
        detail_scroll.add_widget(self._detail_body)

        self._complete_btn = HackerButton(
            text='SEND COMPLETION', size_hint=(None, None), size=(200, 36),
            button_color=SUCCESS,
        )
        self._complete_btn.bind(on_release=lambda *_: self._check_mission())
        self._complete_btn.opacity = 0

        right.add_widget(self._detail_title)
        right.add_widget(detail_scroll)
        right.add_widget(self._complete_btn)

        panels.add_widget(left)
        panels.add_widget(right)
        self.add_widget(panels)

    def on_activate(self):
        super().on_activate()
        if self.net:
            self.net.get_missions()

    def on_state_update(self, state):
        missions = state.missions
        if missions != self._missions:
            self._missions = missions[:]
            self._rebuild()

    def _rebuild(self):
        self._mission_list.clear_widgets()
        for i, m in enumerate(self._missions):
            desc = m.get("description", m.get("title", f"Mission {i+1}"))[:40]
            reward = f"{m.get('payment', 0):,}c"
            diff = m.get("difficulty", "?")

            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=34)
            with row.canvas.before:
                Color(*(ROW_ALT if i % 2 else PANEL_BG))
                bg = Rectangle(pos=row.pos, size=row.size)
            row.bind(pos=lambda w, *_, b=bg: setattr(b, 'pos', w.pos),
                     size=lambda w, *_, b=bg: setattr(b, 'size', w.size))

            desc_lbl = Label(text=desc, font_name='AeroMatics', font_size='14sp',
                             color=TEXT_WHITE, size_hint_x=0.6, halign='left')
            desc_lbl.bind(size=desc_lbl.setter('text_size'))
            reward_lbl = Label(text=reward, font_name='AeroMatics', font_size='13sp',
                               color=SUCCESS, size_hint_x=0.2)
            diff_lbl = Label(text=str(diff), font_name='AeroMatics', font_size='13sp',
                             color=WARNING, size_hint_x=0.2)

            row.add_widget(desc_lbl)
            row.add_widget(reward_lbl)
            row.add_widget(diff_lbl)

            idx = i
            row.bind(on_touch_down=lambda w, t, i=idx: self._select(i) if w.collide_point(*t.pos) else False)
            self._mission_list.add_widget(row)

    def _select(self, idx):
        self._selected = idx
        if 0 <= idx < len(self._missions):
            m = self._missions[idx]
            self._detail_title.text = m.get("description", m.get("title", ""))
            details = []
            if m.get("employer"):
                details.append(f"Employer: {m['employer']}")
            if m.get("target"):
                details.append(f"Target: {m['target']}")
            if m.get("payment"):
                details.append(f"Payment: {m['payment']:,}c")
            if m.get("details"):
                details.append(f"\n{m['details']}")
            self._detail_body.text = "\n".join(details)
            if self._detail_body.parent:
                self._detail_body.text_size = (self._detail_body.parent.width - 20, None)
            self._complete_btn.opacity = 1

    def _check_mission(self):
        if self.net:
            self.net.check_mission()
