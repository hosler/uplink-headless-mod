"""NewsRenderer — two-panel news reader (story list + detail)."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle

from theme.colors import PRIMARY, SECONDARY, TEXT_WHITE, TEXT_DIM, ROW_ALT, PANEL_BG, ROW_HOVER
from browser.renderers.base import BaseRenderer


class NewsRenderer(BaseRenderer):
    """Renders GenericScreen News — two-panel story list + detail body."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._selected = -1
        self._stories = []

        # Two-panel layout
        panels = BoxLayout(orientation='horizontal', spacing=10,
                          size_hint=(0.8, 0.72), pos_hint={'center_x': 0.5, 'center_y': 0.4})

        # Left: story list
        self._story_list = BoxLayout(orientation='vertical', size_hint_y=None)
        self._story_list.bind(minimum_height=self._story_list.setter('height'))
        left_scroll = ScrollView(size_hint_x=0.4)
        left_scroll.add_widget(self._story_list)

        # Right: detail
        self._detail = Label(
            text='Select a story...', font_name='AeroMaticsLight', font_size='15sp',
            color=TEXT_WHITE, halign='left', valign='top', size_hint_y=None,
        )
        self._detail.bind(texture_size=lambda *_: setattr(
            self._detail, 'height', max(200, self._detail.texture_size[1])))
        right_scroll = ScrollView(size_hint_x=0.6)
        right_scroll.add_widget(self._detail)

        panels.add_widget(left_scroll)
        panels.add_widget(right_scroll)
        self.add_widget(panels)

    def on_state_update(self, state):
        stories = state.news
        if stories == self._stories:
            return
        self._stories = stories[:]
        self._story_list.clear_widgets()
        for i, story in enumerate(stories):
            headline = story.get("headline", f"Story {i + 1}")
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=36)
            with row.canvas.before:
                Color(*(ROW_ALT if i % 2 else PANEL_BG))
                bg = Rectangle(pos=row.pos, size=row.size)
            row.bind(pos=lambda w, *_, b=bg: setattr(b, 'pos', w.pos),
                     size=lambda w, *_, b=bg: setattr(b, 'size', w.size))

            bullet = Label(text='\u25c6', font_size='10sp', color=PRIMARY,
                           size_hint_x=None, width=24)
            lbl = Label(text=headline, font_name='AeroMatics', font_size='14sp',
                        color=TEXT_WHITE, halign='left')
            lbl.bind(size=lbl.setter('text_size'))

            row.add_widget(bullet)
            row.add_widget(lbl)

            idx = i
            row.bind(on_touch_down=lambda w, t, i=idx: self._select(i) if w.collide_point(*t.pos) else None)
            self._story_list.add_widget(row)

    def _select(self, idx):
        self._selected = idx
        if 0 <= idx < len(self._stories):
            story = self._stories[idx]
            body = story.get("body", story.get("details", "No content."))
            self._detail.text = body
            self._detail.text_size = (self._detail.parent.width - 20 if self._detail.parent else 400, None)
