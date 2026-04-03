"""LogViewerRenderer — access log table with right-click delete context menu."""
import time as _time
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock

from theme.colors import PRIMARY, TEXT_WHITE, TEXT_DIM, SECONDARY, ROW_ALT, PANEL_BG, ALERT
from widgets.context_menu import ContextMenu
from widgets.progress_bar import HackerProgressBar
from browser.renderers.base import BaseRenderer


class LogRow(BoxLayout):
    """Single log entry with right-click support."""
    def __init__(self, index, log_data, on_context=None, **kwargs):
        super().__init__(size_hint_y=None, height=24, spacing=0, **kwargs)
        self.log_data = log_data
        self._on_context = on_context

        with self.canvas.before:
            Color(*(ROW_ALT if index % 2 == 0 else PANEL_BG))
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=lambda *_: setattr(self._bg, 'pos', self.pos),
                  size=lambda *_: setattr(self._bg, 'size', self.size))

        date = log_data.get("date", "")
        from_ip = log_data.get("from_ip", "")
        from_name = log_data.get("from_name", "")
        data1 = log_data.get("data1", "")

        for text, w, color in [
            (date, 0.25, TEXT_DIM),
            (from_ip, 0.25, TEXT_WHITE),
            (from_name, 0.2, TEXT_WHITE),
            (data1 if data1 else "-", 0.3, TEXT_DIM),
        ]:
            lbl = Label(text=text, font_name='AeroMatics', font_size='12sp',
                        color=color, size_hint_x=w, halign='left', valign='middle')
            lbl.bind(size=lbl.setter('text_size'))
            self.add_widget(lbl)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and touch.button == 'right':
            if self._on_context:
                self._on_context(self.log_data, touch.pos)
            return True
        return super().on_touch_down(touch)


class LogViewerRenderer(BaseRenderer):
    """Renders LogScreen — access logs with right-click delete."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ctx_menu = None
        self._operation = None
        self._op_event = None

        container = BoxLayout(orientation='vertical', spacing=4,
                             size_hint=(0.72, 0.78),
                             pos_hint={'x': 0.16, 'top': 0.88})

        # Header row
        header = BoxLayout(size_hint_y=None, height=26, spacing=0)
        for text, w in [('DATE', 0.25), ('FROM IP', 0.25), ('FROM', 0.2), ('DATA', 0.3)]:
            lbl = Label(text=text, font_name='AeroMatics', font_size='13sp',
                        color=PRIMARY, size_hint_x=w, halign='left', valign='middle')
            lbl.bind(size=lbl.setter('text_size'))
            header.add_widget(lbl)
        container.add_widget(header)

        # Separator
        sep = BoxLayout(size_hint_y=None, height=2)
        with sep.canvas:
            Color(*SECONDARY[:3], 0.4)
            sep._line = Rectangle(pos=sep.pos, size=sep.size)
        sep.bind(pos=lambda w, *_: setattr(w._line, 'pos', w.pos),
                 size=lambda w, *_: setattr(w._line, 'size', w.size))
        container.add_widget(sep)

        # Log list
        self._log_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=1)
        self._log_list.bind(minimum_height=self._log_list.setter('height'))
        scroll = ScrollView(scroll_type=['bars', 'content'],
                           bar_width=6, bar_color=(*PRIMARY[:3], 0.4))
        scroll.add_widget(self._log_list)
        container.add_widget(scroll)

        # Progress bar
        self._progress_row = BoxLayout(size_hint_y=None, height=0, spacing=8)
        self._progress_label = Label(text='', font_name='AeroMatics', font_size='12sp',
                                     color=PRIMARY, halign='left', size_hint_x=0.5)
        self._progress_label.bind(size=self._progress_label.setter('text_size'))
        self._progress_bar = HackerProgressBar(bar_color=ALERT, size_hint_x=0.5,
                                                size_hint_y=None, height=14)
        self._progress_row.add_widget(self._progress_label)
        self._progress_row.add_widget(self._progress_bar)
        container.add_widget(self._progress_row)

        # Footer
        footer = BoxLayout(size_hint_y=None, height=20, spacing=10)
        hint = Label(text='Right-click a log entry to delete',
                    font_name='AeroMaticsLight', font_size='11sp',
                    color=TEXT_DIM, halign='left')
        hint.bind(size=hint.setter('text_size'))
        self._count_label = Label(text='', font_name='AeroMaticsLight', font_size='11sp',
                                  color=TEXT_DIM, halign='right', size_hint_x=None, width=100)
        self._count_label.bind(size=self._count_label.setter('text_size'))
        footer.add_widget(hint)
        footer.add_widget(self._count_label)
        container.add_widget(footer)

        self.add_widget(container)
        self._last_count = -1

    def on_state_update(self, state):
        logs = state.remote_logs
        if len(logs) == self._last_count:
            return
        self._last_count = len(logs)
        self._count_label.text = f"{len(logs)} entries"

        self._log_list.clear_widgets()
        if not logs:
            empty = Label(text='No access logs on this system.',
                         font_name='AeroMaticsLight', font_size='14sp',
                         color=TEXT_DIM, size_hint_y=None, height=40)
            self._log_list.add_widget(empty)
            return

        for i, log in enumerate(logs):
            row = LogRow(i, log, on_context=self._show_context)
            self._log_list.add_widget(row)

    def _show_context(self, log_data, pos):
        if self._ctx_menu and self._ctx_menu.parent:
            self._ctx_menu.dismiss()

        log_index = log_data.get("index", -1)

        items = [
            ("Delete This Log", lambda: self._start_op(
                "Deleting log entry...", 0.8,
                lambda: (self.net.delete_log(log_index), self.net.get_logs()))),
        ]

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
            self._last_count = -1  # Force rebuild
            Clock.schedule_once(lambda dt: self._hide_progress(), 1.0)

    def _hide_progress(self):
        self._progress_row.height = 0
        self._progress_label.text = ''
        self._progress_bar.value = 0

    def on_leave(self):
        if self._op_event:
            self._op_event.cancel()
        if self._ctx_menu and self._ctx_menu.parent:
            self._ctx_menu.parent.remove_widget(self._ctx_menu)
