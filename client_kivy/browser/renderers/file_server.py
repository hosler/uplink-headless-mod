"""FileServerRenderer — file list with right-click context menu + progress."""
import time as _time
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle, Line
from kivy.clock import Clock
from kivy.app import App

from theme.colors import (PRIMARY, SECONDARY, TEXT_WHITE, TEXT_DIM, ROW_ALT,
                          PANEL_BG, SUCCESS, ALERT, WARNING)
from widgets.hacker_button import HackerButton
from widgets.context_menu import ContextMenu
from widgets.progress_bar import HackerProgressBar
from browser.renderers.base import BaseRenderer


class FileRow(BoxLayout):
    """Single file entry with right-click support."""
    def __init__(self, index, file_data, on_context=None, **kwargs):
        super().__init__(orientation='horizontal', size_hint_y=None, height=30,
                         spacing=0, padding=[4, 0], **kwargs)
        self.file_data = file_data
        self._on_context = on_context
        self._index = index

        with self.canvas.before:
            Color(*(ROW_ALT if index % 2 == 0 else PANEL_BG))
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd, size=self._upd)

        title = file_data.get("title", "?")
        size = file_data.get("size", 0)
        encrypted = file_data.get("encrypted", 0)
        compressed = file_data.get("compressed", 0)

        # Diamond bullet
        bullet = Label(text='\u25c6', font_size='8sp', color=PRIMARY,
                       size_hint_x=None, width=18)

        name = Label(text=title, font_name='AeroMatics', font_size='13sp',
                     color=TEXT_WHITE, halign='left', valign='middle')
        name.bind(size=name.setter('text_size'))

        sz = Label(text=f"{size} GQ", font_name='AeroMaticsLight', font_size='12sp',
                   color=TEXT_DIM, size_hint_x=None, width=60, halign='right')
        sz.bind(size=sz.setter('text_size'))

        enc = Label(text='ENC' if encrypted else '', font_name='AeroMatics',
                    font_size='11sp', color=ALERT if encrypted else TEXT_DIM,
                    size_hint_x=None, width=40)
        cmp = Label(text='CMP' if compressed else '', font_name='AeroMatics',
                    font_size='11sp', color=SECONDARY if compressed else TEXT_DIM,
                    size_hint_x=None, width=40)

        self.add_widget(bullet)
        self.add_widget(name)
        self.add_widget(sz)
        self.add_widget(enc)
        self.add_widget(cmp)

    def _upd(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and touch.button == 'right':
            if self._on_context:
                self._on_context(self.file_data, touch.pos)
            return True
        return super().on_touch_down(touch)


class FileServerRenderer(BaseRenderer):
    """Renders GenericScreen FileServer — file table with right-click context menu."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ctx_menu = None
        self._operation = None
        self._op_event = None

        container = BoxLayout(orientation='vertical', spacing=4,
                             size_hint=(0.72, 0.78),
                             pos_hint={'x': 0.16, 'top': 0.88})

        # Header
        header = BoxLayout(size_hint_y=None, height=26, spacing=0)
        for text, w in [('', 18), ('FILENAME', None), ('SIZE', 60), ('', 40), ('', 40)]:
            lbl = Label(text=text, font_name='AeroMatics', font_size='13sp',
                        color=PRIMARY, halign='left' if text else 'center',
                        size_hint_x=None if w else 1, width=w or 0)
            lbl.bind(size=lbl.setter('text_size'))
            header.add_widget(lbl)
        container.add_widget(header)

        # File list
        self._file_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=1)
        self._file_list.bind(minimum_height=self._file_list.setter('height'))
        scroll = ScrollView(scroll_type=['bars', 'content'],
                           bar_width=6, bar_color=(*PRIMARY[:3], 0.4))
        scroll.add_widget(self._file_list)
        container.add_widget(scroll)

        # Progress bar (shown during operations)
        self._progress_row = BoxLayout(size_hint_y=None, height=0, spacing=8)
        self._progress_label = Label(text='', font_name='AeroMatics', font_size='12sp',
                                     color=PRIMARY, halign='left', size_hint_x=0.5)
        self._progress_label.bind(size=self._progress_label.setter('text_size'))
        self._progress_bar = HackerProgressBar(bar_color=PRIMARY, size_hint_x=0.5,
                                                size_hint_y=None, height=14)
        self._progress_row.add_widget(self._progress_label)
        self._progress_row.add_widget(self._progress_bar)
        container.add_widget(self._progress_row)

        # Hint
        hint = Label(text='Right-click a file for options',
                    font_name='AeroMaticsLight', font_size='11sp',
                    color=TEXT_DIM, size_hint_y=None, height=20, halign='center')
        hint.bind(size=hint.setter('text_size'))
        container.add_widget(hint)

        self.add_widget(container)
        self._last_files = []

    def on_state_update(self, state):
        files = state.remote_files
        keys = [(f.get("title", ""), f.get("size", 0)) for f in files]
        if keys == self._last_files:
            return
        self._last_files = keys
        self._file_list.clear_widgets()
        for i, f in enumerate(files):
            row = FileRow(i, f, on_context=self._show_context)
            self._file_list.add_widget(row)

    def _show_context(self, file_data, pos):
        if self._ctx_menu and self._ctx_menu.parent:
            self._ctx_menu.dismiss()

        title = file_data.get("title", "?")
        size = file_data.get("size", 1)
        encrypted = file_data.get("encrypted", 0)

        copy_dur = max(0.5, size * 0.8)
        del_dur = max(0.3, size * 0.2)

        items = [
            (f"Copy '{title}'", lambda: self._start_op(
                f"Copying {title}...", copy_dur,
                lambda: self.net.copy_file(title))),
            (f"Delete '{title}'", lambda: self._start_op(
                f"Deleting {title}...", del_dur,
                lambda: self.net.delete_file(title))),
        ]
        if encrypted:
            items.insert(1, (f"Decrypt '{title}'", lambda: self._start_op(
                f"Decrypting {title}...", max(1.0, encrypted * 1.5),
                lambda: None)))

        self._ctx_menu = ContextMenu(items, pos)
        self._ctx_menu.show()

    def _start_op(self, label, duration, on_complete):
        self._progress_row.height = 24
        self._progress_label.text = label
        self._progress_bar.value = 0
        self._operation = {
            "start": _time.time(),
            "duration": duration,
            "on_complete": on_complete,
        }
        self._op_event = Clock.schedule_interval(self._tick_op, 1/20)

    def _tick_op(self, dt):
        if not self._operation:
            return
        elapsed = _time.time() - self._operation["start"]
        progress = min(1.0, elapsed / self._operation["duration"])
        self._progress_bar.value = progress
        if progress >= 1.0:
            self._operation["on_complete"]()
            self._operation = None
            if self._op_event:
                self._op_event.cancel()
            # Refresh files
            if self.net:
                self.net.get_files()
            Clock.schedule_once(lambda dt: self._hide_progress(), 1.0)

    def _hide_progress(self):
        self._progress_row.height = 0
        self._progress_label.text = ''
        self._progress_bar.value = 0
        self._last_files = []  # Force rebuild

    def on_leave(self):
        if self._op_event:
            self._op_event.cancel()
        if self._ctx_menu and self._ctx_menu.parent:
            self._ctx_menu.dismiss()
