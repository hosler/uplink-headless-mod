"""RankingsRenderer — ranked list of hackers/organizations."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle

from theme.colors import (PRIMARY, SECONDARY, TEXT_WHITE, TEXT_DIM, ROW_ALT,
                          PANEL_BG, SUCCESS, WARNING)
from browser.renderers.base import BaseRenderer


class RankingsRenderer(BaseRenderer):
    """Renders Rankings screen — table of ranked entries."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Header
        header = BoxLayout(orientation='horizontal', size_hint=(0.7, None), height=28,
                          pos_hint={'center_x': 0.5, 'top': 0.87})
        for text, w in [('#', 40), ('NAME', None), ('SCORE', 100), ('STATUS', 100)]:
            lbl = Label(text=text, font_name='AeroMatics', font_size='13sp',
                        color=PRIMARY, halign='left' if text != '#' else 'center',
                        size_hint_x=None if w else 1, width=w or 0)
            lbl.bind(size=lbl.setter('text_size'))
            header.add_widget(lbl)
        self.add_widget(header)

        self._list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=2)
        self._list.bind(minimum_height=self._list.setter('height'))
        scroll = ScrollView(size_hint=(0.7, 0.68), pos_hint={'center_x': 0.5, 'center_y': 0.4})
        scroll.add_widget(self._list)
        self.add_widget(scroll)
        self._last_buttons = []

    def on_state_update(self, state):
        buttons = state.buttons
        keys = [(b.get("name", ""), b.get("value", "")) for b in buttons]
        if keys == self._last_buttons:
            return
        self._last_buttons = keys
        self._list.clear_widgets()

        rank = 1
        for btn in buttons:
            name = btn.get("name", "")
            caption = btn.get("caption", "")
            value = btn.get("value", "")
            if not name or name.startswith("_"):
                continue

            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=34)
            with row.canvas.before:
                Color(*(ROW_ALT if rank % 2 else PANEL_BG))
                bg = Rectangle(pos=row.pos, size=row.size)
            row.bind(pos=lambda w, *_, b=bg: setattr(b, 'pos', w.pos),
                     size=lambda w, *_, b=bg: setattr(b, 'size', w.size))

            # Rank number with color (gold for top 3)
            rank_color = WARNING if rank <= 3 else TEXT_DIM
            rank_lbl = Label(text=str(rank), font_name='AeroMatics', font_size='15sp',
                             color=rank_color, size_hint_x=None, width=40, halign='center')
            rank_lbl.bind(size=rank_lbl.setter('text_size'))

            # Name
            display_name = caption or name.replace("_", " ")
            name_lbl = Label(text=display_name, font_name='AeroMatics', font_size='14sp',
                             color=TEXT_WHITE, halign='left')
            name_lbl.bind(size=name_lbl.setter('text_size'))

            # Score
            score_lbl = Label(text=value, font_name='AeroMatics', font_size='14sp',
                              color=SUCCESS, size_hint_x=None, width=100, halign='right')
            score_lbl.bind(size=score_lbl.setter('text_size'))

            # Status indicator
            status_lbl = Label(text='ACTIVE', font_name='AeroMaticsLight', font_size='12sp',
                               color=PRIMARY, size_hint_x=None, width=100, halign='center')

            row.add_widget(rank_lbl)
            row.add_widget(name_lbl)
            row.add_widget(score_lbl)
            row.add_widget(status_lbl)
            self._list.add_widget(row)
            rank += 1
