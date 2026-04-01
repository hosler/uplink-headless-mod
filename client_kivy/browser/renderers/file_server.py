"""FileServerRenderer — file list with copy/delete operations."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle

from theme.colors import PRIMARY, SECONDARY, TEXT_WHITE, TEXT_DIM, ROW_ALT, PANEL_BG, SUCCESS, ALERT
from widgets.hacker_button import HackerButton
from browser.renderers.base import BaseRenderer


class FileRow(BoxLayout):
    def __init__(self, index, filename, size_str, encrypted, compressed,
                 on_copy=None, on_delete=None, **kwargs):
        super().__init__(orientation='horizontal', size_hint_y=None, height=36, **kwargs)

        with self.canvas.before:
            Color(*(ROW_ALT if index % 2 else PANEL_BG))
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd, size=self._upd)

        bullet = Label(text='\u25c6', font_size='10sp', color=PRIMARY,
                       size_hint_x=None, width=24)
        name = Label(text=filename, font_name='AeroMatics', font_size='15sp',
                     color=TEXT_WHITE, halign='left')
        name.bind(size=name.setter('text_size'))
        sz = Label(text=size_str, font_name='AeroMaticsLight', font_size='13sp',
                   color=TEXT_DIM, size_hint_x=None, width=80, halign='right')
        sz.bind(size=sz.setter('text_size'))
        enc = Label(text='ENC' if encrypted else '', font_name='AeroMatics',
                    font_size='12sp', color=ALERT if encrypted else TEXT_DIM,
                    size_hint_x=None, width=50)
        comp = Label(text='CMP' if compressed else '', font_name='AeroMatics',
                     font_size='12sp', color=SECONDARY if compressed else TEXT_DIM,
                     size_hint_x=None, width=50)

        copy_btn = HackerButton(text='COPY', size_hint_x=None, width=60,
                                font_size='12sp', button_color=SUCCESS)
        copy_btn.bind(on_release=lambda *_: on_copy(filename) if on_copy else None)

        del_btn = HackerButton(text='DEL', size_hint_x=None, width=50,
                               font_size='12sp', button_color=ALERT)
        del_btn.bind(on_release=lambda *_: on_delete(filename) if on_delete else None)

        for w in [bullet, name, sz, enc, comp, copy_btn, del_btn]:
            self.add_widget(w)

    def _upd(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size


class FileServerRenderer(BaseRenderer):
    """Renders GenericScreen FileServer — file table with operations."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Header
        header = BoxLayout(orientation='horizontal', size_hint=(0.7, None), height=28,
                          pos_hint={'center_x': 0.5, 'top': 0.87})
        for text, w in [('FILENAME', None), ('SIZE', 80), ('ENC', 50), ('CMP', 50), ('', 60), ('', 50)]:
            lbl = Label(text=text, font_name='AeroMatics', font_size='13sp',
                        color=PRIMARY, halign='left',
                        size_hint_x=None if w else 1, width=w or 0)
            lbl.bind(size=lbl.setter('text_size'))
            header.add_widget(lbl)
        self.add_widget(header)

        self._list = BoxLayout(orientation='vertical', size_hint_y=None)
        self._list.bind(minimum_height=self._list.setter('height'))
        scroll = ScrollView(size_hint=(0.7, 0.65), pos_hint={'center_x': 0.5, 'center_y': 0.4})
        scroll.add_widget(self._list)
        self.add_widget(scroll)
        self._last_files = []

    def on_state_update(self, state):
        files = state.remote_files
        keys = [(f.get("title", ""), f.get("size", 0)) for f in files]
        if keys == self._last_files:
            return
        self._last_files = keys
        self._list.clear_widgets()
        for i, f in enumerate(files):
            row = FileRow(
                i, f.get("title", "?"),
                f"{f.get('size', 0)} GQ",
                f.get("encrypted", False),
                f.get("compressed", False),
                on_copy=self._copy, on_delete=self._delete,
            )
            self._list.add_widget(row)

    def _copy(self, title):
        if self.net:
            self.net.copy_file(title)

    def _delete(self, title):
        if self.net:
            self.net.delete_file(title)
