"""ConsoleRenderer — terminal session with command input."""
import time
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, Rectangle, Line, Ellipse
from kivy.core.text import Label as CoreLabel
from kivy.clock import Clock
from kivy.properties import BooleanProperty

from theme.colors import PRIMARY, SECONDARY, TEXT_WHITE, TEXT_DIM, PANEL_BG, SUCCESS, ALERT, WARNING
from browser.renderers.base import BaseRenderer


class TerminalOutput(Widget):
    """Canvas-drawn terminal output area with colored lines."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._lines = []  # list of (text, color)
        self.bind(size=self._redraw, pos=self._redraw)

    def set_lines(self, lines):
        if lines != self._lines:
            self._lines = lines
            self._redraw()

    def _redraw(self, *_args):
        self.canvas.clear()
        w, h = self.size
        ox, oy = self.pos
        if w < 10 or h < 10:
            return

        line_h = 20
        # Draw from bottom up (newest at bottom), but iterate top-down
        visible = self._lines[-(int(h / line_h)):]
        self.height = max(h, len(self._lines) * line_h + 10)

        with self.canvas:
            for i, (text, color) in enumerate(visible):
                ly = oy + h - (i + 1) * line_h - 6
                if ly < oy - line_h:
                    break
                cl = CoreLabel(text=text, font_size=14, font_name='AeroMatics',
                               color=color, halign='left')
                cl.refresh()
                tex = cl.texture
                if tex:
                    Color(1, 1, 1, 1)
                    Rectangle(texture=tex, pos=(ox + 10, ly), size=tex.size)


class TerminalInput(TextInput):
    """Console-style text input — no border, green text, block cursor."""

    def __init__(self, **kwargs):
        kwargs['font_name'] = 'AeroMatics'
        kwargs['font_size'] = '15sp'
        kwargs['multiline'] = False
        kwargs['background_color'] = (0, 0, 0, 0)
        kwargs['foreground_color'] = SUCCESS
        kwargs['cursor_color'] = SUCCESS
        kwargs['padding'] = [0, 6]
        kwargs['background_normal'] = ''
        kwargs['background_active'] = ''
        kwargs['hint_text'] = ''
        kwargs['write_tab'] = False
        super().__init__(**kwargs)

    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        from kivy.app import App
        key = keycode[0] if isinstance(keycode, tuple) else keycode
        # Enter triggers validate
        if key == 13:
            result = super().keyboard_on_key_down(window, keycode, text, modifiers)
            return result
        # Up arrow: previous command
        if key == 273 and hasattr(self, '_console') and self._console:
            hist = self._console._cmd_history
            if hist:
                idx = self._console._cmd_idx
                if idx == -1:
                    idx = len(hist) - 1
                elif idx > 0:
                    idx -= 1
                self._console._cmd_idx = idx
                self.text = hist[idx]
                self.cursor = (len(self.text), 0)
            return True
        # Down arrow: next command
        if key == 274 and hasattr(self, '_console') and self._console:
            hist = self._console._cmd_history
            idx = self._console._cmd_idx
            if idx >= 0 and idx < len(hist) - 1:
                idx += 1
                self._console._cmd_idx = idx
                self.text = hist[idx]
                self.cursor = (len(self.text), 0)
            elif idx >= 0:
                self._console._cmd_idx = -1
                self.text = ''
            return True
        # Escape: unfocus and forward
        if key == 27:
            self.focus = False
            app = App.get_running_app()
            if app and hasattr(app, '_on_key_down'):
                app._on_key_down(window, key, 0, '', modifiers)
            return True
        # F-keys: forward
        if 282 <= key <= 289:
            app = App.get_running_app()
            if app and hasattr(app, '_on_key_down'):
                app._on_key_down(window, key, 0, '', modifiers)
            return True
        return super().keyboard_on_key_down(window, keycode, text, modifiers)


class ConsoleRenderer(BaseRenderer):
    """Renders GenericScreen Console — full terminal emulator look."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._history = []  # list of (text, color) for all output
        self._cmd_history = []  # typed commands for up-arrow recall
        self._cmd_idx = -1
        self._prompt_prefix = "root@uplink:/# "
        self._cursor_blink = True
        self._blink_event = None

        # Remove the base title/subtitle since we draw our own header
        self._title_label.opacity = 0
        self._title_label.height = 0
        self._subtitle_label.opacity = 0
        self._subtitle_label.height = 0

        # Main terminal container
        self._terminal = BoxLayout(orientation='vertical',
                                    size_hint=(0.85, 0.78),
                                    pos_hint={'center_x': 0.52, 'center_y': 0.46})
        # Header bar
        self._header = TerminalHeader()
        self._header.size_hint_y = None
        self._header.height = 28

        # Output area with scroll
        self._output_scroll = ScrollView(size_hint=(1, 1), bar_width=6,
                                          bar_color=(*SUCCESS[:3], 0.3),
                                          scroll_type=['bars', 'content'])
        self._output_widget = TerminalOutput(size_hint_y=None)
        self._output_scroll.add_widget(self._output_widget)

        # Prompt row: prefix label + input
        self._prompt_row = BoxLayout(orientation='horizontal',
                                      size_hint_y=None, height=32)
        self._prefix_label = Label(text=self._prompt_prefix,
                                    font_name='AeroMatics', font_size='15sp',
                                    color=SUCCESS, size_hint_x=None, width=180,
                                    halign='left', valign='middle')
        self._prefix_label.bind(size=self._prefix_label.setter('text_size'))

        self._input = TerminalInput(size_hint_x=1)
        self._input.bind(on_text_validate=self._send_command)
        self._input._console = self  # back-ref for history recall

        self._prompt_row.add_widget(self._prefix_label)
        self._prompt_row.add_widget(self._input)

        # Assemble terminal
        self._terminal.add_widget(self._header)
        self._terminal.add_widget(self._output_scroll)
        self._terminal.add_widget(self._prompt_row)

        # Terminal background and border (drawn via canvas)
        self._terminal.bind(pos=self._draw_terminal_bg, size=self._draw_terminal_bg)

        self.add_widget(self._terminal)

    def on_enter(self):
        self._input.focus = True
        # Start cursor blink
        if self._blink_event:
            self._blink_event.cancel()
        self._blink_event = Clock.schedule_interval(self._blink_cursor, 0.5)

    def on_leave(self):
        if self._blink_event:
            self._blink_event.cancel()
            self._blink_event = None

    def _blink_cursor(self, _dt):
        self._cursor_blink = not self._cursor_blink

    def _draw_terminal_bg(self, *_args):
        self._terminal.canvas.before.clear()
        x, y = self._terminal.pos
        w, h = self._terminal.size
        with self._terminal.canvas.before:
            # Dark terminal background
            Color(2 / 255, 8 / 255, 12 / 255, 1)
            Rectangle(pos=(x, y), size=(w, h))
            # Subtle green inner glow
            for i in range(6):
                alpha = 0.03 * (1 - i / 6)
                Color(*SUCCESS[:3], alpha)
                Line(rectangle=[x + i, y + i, w - 2 * i, h - 2 * i], width=1)
            # Border
            Color(*SECONDARY[:3], 0.4)
            Line(rectangle=[x, y, w, h], width=1.2)
            # Scanline effect
            Color(0, 0, 0, 0.06)
            for sy in range(int(y), int(y + h), 3):
                Rectangle(pos=(x, sy), size=(w, 1))

    def _send_command(self, *_args):
        text = self._input.text.strip()
        if text and self.net:
            # Add to local history display
            self._history.append((f"{self._prompt_prefix}{text}", SUCCESS))
            self._cmd_history.append(text)
            self._cmd_idx = -1
            # Send to server
            self.net.type_text(text)
            self.net.send_key(13)  # Enter
            self._input.text = ''
            self._update_output()

    def _update_output(self):
        self._output_widget.set_lines(self._history)
        # Scroll to bottom
        self._output_scroll.scroll_y = 0

    def on_state_update(self, state):
        # Extract prompt prefix from console_typehere button
        for b in state.buttons:
            if b.get("name", "") == "console_typehere":
                cap = b.get("caption", "").strip()
                if cap:
                    self._prompt_prefix = cap + " "
                    self._prefix_label.text = self._prompt_prefix
                    # Resize prefix to fit
                    cl = CoreLabel(text=self._prompt_prefix, font_size=15,
                                    font_name='AeroMatics')
                    cl.refresh()
                    self._prefix_label.width = cl.texture.width + 8 if cl.texture else 180

        # Gather console output lines from server state
        server_lines = []
        for btn in state.buttons:
            name = btn.get("name", "")
            if ("console" in name and
                    name not in ("console_typehere", "console_post", "console_title")):
                val = btn.get("value", btn.get("caption", ""))
                if val:
                    server_lines.append(val.strip())

        # Colorize and merge with history
        if server_lines:
            new_lines = []
            for line in server_lines:
                color = self._colorize(line)
                new_lines.append((line, color))
            # Replace server-sourced lines (keep user commands interspersed)
            self._history = new_lines
            self._update_output()

    def _colorize(self, line):
        """Determine line color based on content."""
        upper = line.upper()
        if any(k in upper for k in ("ERROR", "DENIED", "FAILED", "INVALID", "REFUSED")):
            return ALERT
        if any(k in upper for k in ("WARNING", "CAUTION")):
            return WARNING
        if line.startswith(">") or line.startswith("/") or line.startswith("./"):
            return TEXT_WHITE
        if any(k in upper for k in ("OK", "SUCCESS", "COMPLETE", "GRANTED")):
            return (*SUCCESS[:3], 1.0)
        return (*SUCCESS[:3], 0.85)


class TerminalHeader(Widget):
    """Terminal title bar with window dots."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *_args):
        self.canvas.clear()
        x, y = self.pos
        w, h = self.size
        with self.canvas:
            # Dark header background
            Color(15 / 255, 25 / 255, 35 / 255, 1)
            Rectangle(pos=(x, y), size=(w, h))
            # Bottom border
            Color(*SECONDARY[:3], 0.5)
            Line(points=[x, y, x + w, y], width=0.7)

            # Title text
            cl = CoreLabel(text='REMOTE TERMINAL SESSION', font_size=13,
                            font_name='AeroMatics', color=(*PRIMARY[:3], 0.9), bold=True)
            cl.refresh()
            tex = cl.texture
            if tex:
                Color(1, 1, 1, 1)
                Rectangle(texture=tex,
                          pos=(x + 10, y + (h - tex.height) / 2),
                          size=tex.size)

            # Window control dots (right side)
            dot_y = y + h / 2
            for i, col in enumerate([ALERT, WARNING, SUCCESS]):
                Color(*col[:3], 0.9)
                dx = x + w - 15 - i * 14
                Ellipse(pos=(dx - 3, dot_y - 3), size=(6, 6))
