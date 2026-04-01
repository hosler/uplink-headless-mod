"""LogViewerRenderer — log table with delete button."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle

from theme.colors import PRIMARY, TEXT_WHITE, TEXT_DIM, ROW_ALT, PANEL_BG, ALERT
from widgets.hacker_button import HackerButton
from browser.renderers.base import BaseRenderer


class LogViewerRenderer(BaseRenderer):
    """Renders LogScreen — access log table with delete-all."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Header
        header = BoxLayout(orientation='horizontal', size_hint=(0.7, None), height=28,
                          pos_hint={'center_x': 0.5, 'top': 0.87})
        for text, w in [('DATE', 160), ('HOST', 180), ('USER', 120), ('ACTION', None)]:
            lbl = Label(text=text, font_name='AeroMatics', font_size='13sp',
                        color=PRIMARY, halign='left',
                        size_hint_x=None if w else 1, width=w or 0)
            lbl.bind(size=lbl.setter('text_size'))
            header.add_widget(lbl)
        self.add_widget(header)

        self._list = BoxLayout(orientation='vertical', size_hint_y=None)
        self._list.bind(minimum_height=self._list.setter('height'))
        scroll = ScrollView(size_hint=(0.7, 0.6), pos_hint={'center_x': 0.5, 'center_y': 0.42})
        scroll.add_widget(self._list)
        self.add_widget(scroll)

        self._del_btn = HackerButton(
            text='DELETE ALL LOGS', size_hint=(0.25, None), height=38,
            pos_hint={'center_x': 0.5, 'y': 0.06}, button_color=ALERT,
        )
        self._del_btn.bind(on_release=lambda *_: self._delete_logs())
        self.add_widget(self._del_btn)
        self._last_logs = []

    def on_state_update(self, state):
        logs = state.remote_logs
        if len(logs) == len(self._last_logs):
            return
        self._last_logs = logs[:]
        self._list.clear_widgets()
        for i, log in enumerate(logs):
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=32)
            with row.canvas.before:
                Color(*(ROW_ALT if i % 2 else PANEL_BG))
                bg = Rectangle(pos=row.pos, size=row.size)
            row.bind(pos=lambda w, *_, b=bg: setattr(b, 'pos', w.pos),
                     size=lambda w, *_, b=bg: setattr(b, 'size', w.size))

            date = Label(text=log.get("date", ""), font_name='AeroMaticsLight',
                         font_size='13sp', color=TEXT_DIM, size_hint_x=None, width=160,
                         halign='left')
            date.bind(size=date.setter('text_size'))
            host = Label(text=log.get("host", ""), font_name='AeroMatics',
                         font_size='13sp', color=TEXT_WHITE, size_hint_x=None, width=180,
                         halign='left')
            host.bind(size=host.setter('text_size'))
            user = Label(text=log.get("user", ""), font_name='AeroMaticsLight',
                         font_size='13sp', color=TEXT_DIM, size_hint_x=None, width=120,
                         halign='left')
            user.bind(size=user.setter('text_size'))
            action = Label(text=log.get("action", ""), font_name='AeroMaticsLight',
                           font_size='13sp', color=TEXT_DIM, halign='left')
            action.bind(size=action.setter('text_size'))

            row.add_widget(date)
            row.add_widget(host)
            row.add_widget(user)
            row.add_widget(action)
            self._list.add_widget(row)

    def _delete_logs(self):
        if self.net:
            self.net.delete_logs()
