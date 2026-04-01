"""LinksRenderer — LinksScreen (filterable server list)."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.app import App
from kivy.graphics import Color, Rectangle

from theme.colors import PRIMARY, SECONDARY, TEXT_WHITE, TEXT_DIM, ROW_ALT, PANEL_BG
from widgets.hacker_text_input import HackerTextInput
from browser.renderers.base import BaseRenderer


class LinkRow(BoxLayout):
    def __init__(self, index, ip, name="", on_click=None, **kwargs):
        super().__init__(orientation='horizontal', size_hint_y=None, height=38, **kwargs)
        self.ip = ip
        self._on_click = on_click

        with self.canvas.before:
            Color(*(ROW_ALT if index % 2 else PANEL_BG))
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd, size=self._upd)

        bullet = Label(text='\u25c6', font_size='10sp', color=PRIMARY,
                       size_hint_x=None, width=24)
        ip_lbl = Label(text=ip, font_name='AeroMatics', font_size='16sp',
                       color=TEXT_WHITE, size_hint_x=None, width=180, halign='left')
        ip_lbl.bind(size=ip_lbl.setter('text_size'))
        name_lbl = Label(text=name, font_name='AeroMaticsLight', font_size='14sp',
                         color=TEXT_DIM, halign='left')
        name_lbl.bind(size=name_lbl.setter('text_size'))

        self.add_widget(bullet)
        self.add_widget(ip_lbl)
        self.add_widget(name_lbl)

    def _upd(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if self._on_click:
                self._on_click(self.ip)
            return True
        return super().on_touch_down(touch)


class LinksRenderer(BaseRenderer):
    """Renders LinksScreen — list of servers with search filter."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._search = HackerTextInput(
            hint_text='Search InterNIC...',
            size_hint=(0.4, None), height=36,
            pos_hint={'center_x': 0.5, 'top': 0.88},
        )
        self._search.bind(text=self._on_filter)

        self._list_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self._list_layout.bind(minimum_height=self._list_layout.setter('height'))
        scroll = ScrollView(
            size_hint=(0.6, 0.7),
            pos_hint={'center_x': 0.5, 'center_y': 0.4},
        )
        scroll.add_widget(self._list_layout)

        self.add_widget(self._search)
        self.add_widget(scroll)
        self._links = []

    def on_state_update(self, state):
        new_links = state.screen_links or []
        if new_links != self._links:
            self._links = new_links
            self._rebuild()

    def _on_filter(self, *_):
        self._rebuild()

    def _rebuild(self):
        self._list_layout.clear_widgets()
        filt = self._search.text.lower()
        for i, link in enumerate(self._links):
            ip = link.get("ip", "") if isinstance(link, dict) else str(link)
            name = link.get("name", "") if isinstance(link, dict) else ""
            if filt and filt not in ip.lower() and filt not in name.lower():
                continue
            row = LinkRow(i, ip, name, on_click=self._connect)
            self._list_layout.add_widget(row)

    def _connect(self, ip):
        # Navigate back to bookmarks-level and connect
        app = App.get_running_app()
        if self.net:
            self.net.add_link(ip)
        # Find the browser view and tell it to connect
        if app._game._browser:
            app._game._browser.connect_to(ip)
