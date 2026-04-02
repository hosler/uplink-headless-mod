"""LogViewerRenderer — access log viewer."""
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

from theme.colors import PRIMARY, TEXT_WHITE, TEXT_DIM, SECONDARY
from browser.renderers.base import BaseRenderer


class LogViewerRenderer(BaseRenderer):
    """Renders LogScreen — access logs as scrollable text."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Header row — offset right to avoid sidebar overlap
        header = Label(
            text='DATE                  FROM IP               FROM              DATA',
            font_name='AeroMatics', font_size='13sp',
            color=PRIMARY, size_hint=(0.7, None), height=24,
            pos_hint={'center_x': 0.55, 'top': 0.87}, halign='left',
        )
        header.bind(size=header.setter('text_size'))
        self.add_widget(header)

        self._log_count = Label(
            text='', font_name='AeroMaticsLight', font_size='11sp',
            color=TEXT_DIM, size_hint=(None, None), size=(100, 20),
            pos_hint={'right': 0.95, 'top': 0.87}, halign='right',
        )
        self._log_count.bind(size=self._log_count.setter('text_size'))
        self.add_widget(self._log_count)

        # Log text — offset right to clear sidebar
        self._log_text = Label(
            text='Loading logs...', font_name='AeroMatics', font_size='12sp',
            color=TEXT_WHITE, halign='left', valign='top',
            size_hint_y=None, markup=False,
        )
        self._log_text.bind(texture_size=self._resize)

        scroll = ScrollView(size_hint=(0.7, 0.75),
                           pos_hint={'center_x': 0.55, 'center_y': 0.42},
                           scroll_type=['bars', 'content'],
                           bar_width=6, bar_color=(*PRIMARY[:3], 0.4))
        scroll.add_widget(self._log_text)
        self.add_widget(scroll)

        self._last_count = -1

    def _resize(self, *_):
        self._log_text.height = max(200, self._log_text.texture_size[1] + 20)

    def on_state_update(self, state):
        logs = state.remote_logs
        if len(logs) == self._last_count:
            return
        self._last_count = len(logs)
        self._log_count.text = f"{len(logs)} entries"

        if not logs:
            self._log_text.text = "No access logs on this system."
            return

        lines = []
        for log in logs:
            date = log.get("date", "")[:18].ljust(22)
            from_ip = log.get("from_ip", "")[:20].ljust(22)
            from_name = log.get("from_name", "")[:14].ljust(16)
            data1 = log.get("data1", "")
            lines.append(f"{date}{from_ip}{from_name}{data1}")

        self._log_text.text = "\n".join(lines)
        if self._log_text.parent:
            self._log_text.text_size = (self._log_text.parent.width - 10, None)
