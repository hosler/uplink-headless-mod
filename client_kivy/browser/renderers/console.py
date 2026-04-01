"""ConsoleRenderer — terminal session with command input."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

from theme.colors import PRIMARY, TEXT_WHITE, TEXT_DIM, PANEL_BG
from widgets.hacker_text_input import HackerTextInput
from browser.renderers.base import BaseRenderer


class ConsoleRenderer(BaseRenderer):
    """Renders GenericScreen Console — REMOTE TERMINAL SESSION."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._output = Label(
            text='', font_name='AeroMatics', font_size='14sp',
            color=TEXT_WHITE, halign='left', valign='top',
            size_hint_y=None, markup=False,
        )
        self._output.bind(texture_size=lambda *_: setattr(
            self._output, 'height', max(200, self._output.texture_size[1])))

        scroll = ScrollView(size_hint=(0.65, 0.6), pos_hint={'center_x': 0.5, 'center_y': 0.5})
        scroll.add_widget(self._output)

        self._input = HackerTextInput(
            hint_text='Type command...', size_hint=(0.65, None), height=36,
            pos_hint={'center_x': 0.5, 'y': 0.08},
        )
        self._input.bind(on_text_validate=self._send_command)

        self.add_widget(scroll)
        self.add_widget(self._input)

    def on_enter(self):
        self._input.focus = True

    def _send_command(self, *_args):
        text = self._input.text.strip()
        if text and self.net:
            self.net.type_text(text)
            self.net.send_key(13)  # Enter
            self._input.text = ''

    def on_state_update(self, state):
        # Console output comes from buttons with console-related names
        lines = []
        for btn in state.buttons:
            name = btn.get("name", "")
            if "console" in name and name != "console_typehere":
                val = btn.get("value", btn.get("caption", ""))
                if val:
                    lines.append(val)
        if lines:
            self._output.text = '\n'.join(lines)
            self._output.text_size = (self._output.parent.width - 20 if self._output.parent else 500, None)
