#!/usr/bin/env python3
"""Uplink Kivy Client — connects to headless game server."""
import sys
import os
import argparse

# Ensure client_kivy/ is in path for imports, and parent for network.py access
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'client'))

# Set kivy config before importing kivy
os.environ['KIVY_NO_ARGS'] = '1'
os.environ.setdefault('KIVY_NO_CONSOLELOG', '0')

from kivy.config import Config
Config.set('graphics', 'width', '1280')
Config.set('graphics', 'height', '720')
Config.set('graphics', 'resizable', 'True')
Config.set('graphics', 'minimum_width', '800')
Config.set('graphics', 'minimum_height', '500')
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')
# Disable all extra input providers that create phantom touches
Config.set('input', 'hid_%(name)s', '')
Config.remove_option('input', 'hid_%(name)s')
for key in list(Config.options('input')):
    if key != 'mouse':
        Config.remove_option('input', key)

from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.properties import ObjectProperty, ListProperty

from theme import register_fonts
from theme.colors import (PRIMARY, SECONDARY, ALERT, SUCCESS, WARNING,
                          TEXT_DIM, TEXT_WHITE, TOPBAR_BG, PANEL_BG)
from network import Network


# Load KV files
KV_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kv')


class UplinkApp(App):
    title = 'UPLINK'

    # Theme color properties — accessible from KV as app.c_primary etc.
    c_primary = ListProperty(list(PRIMARY))
    c_secondary = ListProperty(list(SECONDARY))
    c_alert = ListProperty(list(ALERT))
    c_success = ListProperty(list(SUCCESS))
    c_warning = ListProperty(list(WARNING))
    c_text_dim = ListProperty(list(TEXT_DIM))
    c_text_white = ListProperty(list(TEXT_WHITE))
    c_topbar_bg = ListProperty(list(TOPBAR_BG))
    c_panel_bg = ListProperty(list(PANEL_BG))

    net = ObjectProperty(None, allownone=True)

    def __init__(self, host='127.0.0.1', port=9090, no_music=False,
                 debug_log='', auto_join='', auto_connect='', auto_crack=False,
                 **kwargs):
        super().__init__(**kwargs)
        self._host = host
        self._port = port
        self._no_music = no_music
        self._debug_log = debug_log
        self._auto_join = auto_join
        self._auto_connect = auto_connect
        self._auto_crack = auto_crack
        self._sm = None
        self._login = None
        self._game = None
        self._last_trace_poll = 0
        self._trace_warned = False
        self._prev_screen_key = ""

    def build(self):
        register_fonts()

        # Import widgets BEFORE loading KV so Factory knows about them
        from widgets.gradient_bg import GradientBg  # noqa: F401
        from widgets.hacker_button import HackerButton  # noqa: F401
        from widgets.hacker_text_input import HackerTextInput  # noqa: F401
        from widgets.hacker_panel import HackerPanel  # noqa: F401
        from widgets.crt_overlay import CRTOverlay  # noqa: F401
        from widgets.progress_bar import HackerProgressBar  # noqa: F401
        from screens.login_screen import LoginScreen  # noqa: F401
        from screens.game_screen import GameScreen, TopBar, TabBar, StatusBar  # noqa: F401

        # Load KV files
        for kv_file in ['main.kv', 'login.kv']:
            Builder.load_file(os.path.join(KV_DIR, kv_file))

        self._sm = ScreenManager(transition=FadeTransition(duration=0.3))
        self._login = LoginScreen(name='login')
        self._game = GameScreen(name='game')
        self._sm.add_widget(self._login)
        self._sm.add_widget(self._game)

        # Initialize network
        self.net = Network(self._host, self._port)
        if self._debug_log:
            self.net.enable_debug_log(self._debug_log)

        # Auto-join (skip login)
        if self._auto_join:
            Clock.schedule_once(lambda dt: self._do_auto_join(), 0.5)

        # Audio
        if not self._no_music:
            import audio as _audio
            _audio.init()
            _audio.play_music()
        else:
            import audio as _audio
            _audio.init()

        Window.bind(on_key_down=self._on_key_down)

        # Set window background
        Window.clearcolor = (11 / 255, 11 / 255, 11 / 255, 1)

        # Network polling at 30Hz
        Clock.schedule_interval(self._poll_network, 1 / 30)

        # Trace polling every 2s
        Clock.schedule_interval(self._poll_trace, 2.0)

        return self._sm

    def _do_auto_join(self):
        """Auto-join, optionally auto-connect and auto-crack."""
        import time as _t
        if not self.net.connect():
            print(f"Auto-join: cannot connect to {self._host}:{self._port}")
            return
        self.net.join(self._auto_join, "auto")
        _t.sleep(2)
        self.net.poll()
        self._sm.current = 'game'
        self.net.joined = True
        self.net.request_state()
        self.net.get_links()
        self.net.get_balance()
        self.net.get_gateway_files()

        if self._auto_connect:
            _t.sleep(0.5)
            self.net.poll()
            self.net.server_connect(self._auto_connect)
            _t.sleep(1)
            self.net.poll()
            if self._game._browser:
                self._game._browser._mode = "screen"
                self._game._browser._show_screen()

            if self._auto_crack:
                self.net.send({"cmd": "crack_password"})
                _t.sleep(1)
                self.net.poll()
                creds = self.net.state.credentials
                admin = [c for c in creds if c.get("name") == "admin"]
                if admin:
                    pw = admin[0]["password"]
                    print(f"Auto-crack: admin/{pw}")
                    self.net.submit_password(pw, "admin")
                    _t.sleep(1)
                    self.net.poll()

    def attempt_join(self, handle, password=""):
        """Called from login screen."""
        if not self.net.connected:
            if not self.net.connect():
                self._login.set_error(f"Cannot connect to {self._host}:{self._port}")
                return
        self.net.join(handle, password)

    def _poll_network(self, _dt):
        if not self.net or not self.net.connected:
            return
        responses = self.net.poll()
        for r in responses:
            self._handle_response(r)
        # Update game screen state
        if self._sm.current == 'game':
            self._update_game_state()

    def _poll_trace(self, _dt):
        if not self.net or not self.net.connected:
            return
        if self._sm.current != 'game':
            return
        state = self.net.state
        if state.player.get("connected"):
            self.net.get_trace()
            trace = state.trace
            if trace.get("active"):
                pct = trace.get("progress", 0) / max(trace.get("total", 1), 1)
                if pct > 0.8 and not self._trace_warned:
                    self._trace_warned = True
                    self._game.statusbar.show("WARNING: Trace almost complete!")
            else:
                self._trace_warned = False

    def _update_game_state(self):
        """Push network state to game screen widgets."""
        state = self.net.state
        tb = self._game.topbar
        if tb:
            tb.agent_handle = state.player.get("handle", "")
            tb.remote_host = state.player.get("remotehost", "")
            tb.screen_title = state.screen_data.get("maintitle", "")
            tb.balance = state.balance
            tb.speed = state.speed
            tb.game_date = state.date

        sb = self._game.statusbar
        if sb:
            nodes = state.connection.get("nodes", [])
            sb.chain_text = " > ".join(nodes)
            trace = state.trace
            if trace.get("active"):
                sb.trace_active = True
                sb.trace_progress = trace.get("progress", 0) / max(trace.get("total", 1), 1)
            else:
                sb.trace_active = False
                sb.trace_progress = 0

        # Update active content view + sidebar
        self._game.update_views(state)

    def _on_tool_run(self, tool_name):
        """Called when a software tool is launched from the sidebar."""
        import audio as _audio
        st = self.net.state.screen_type if self.net else ""
        if tool_name in ("Password_Breaker", "Dictionary_Hacker"):
            if st in ("PasswordScreen", "UserIDScreen"):
                self.net.crack_password()
                _audio.play_sfx("short_whoosh6")
                # Trigger crack animation in password renderer
                host = self._game._browser._get_screen_host() if self._game._browser else None
                if host and host._current_renderer and hasattr(host._current_renderer, 'start_crack'):
                    host._current_renderer.start_crack()
        elif tool_name == "Trace_Tracker":
            self.net.get_trace()
        elif tool_name == "Log_Deleter":
            self.net.delete_logs()
            _audio.play_sfx("success")
        _audio.play_sfx("popup")

    def _handle_response(self, r):
        import audio as _audio
        status = r.get("status", "")
        detail = r.get("detail", "")
        if status == "ok" and "session" in detail:
            # Join success
            self._sm.current = 'game'
            self.net.joined = True
            self.net.request_state()
            self.net.get_links()
            self.net.get_balance()
            self.net.get_gateway_files()  # for sidebar tools
            _audio.play_sfx("login")
            if self._game.statusbar:
                self._game.statusbar.show(
                    f"Welcome, Agent {self.net.state.player.get('handle', '')}")
        elif status == "error" and self._sm.current == 'login':
            self._login.set_error(detail)
        elif status == "ok":
            if not any(x in detail for x in ["screen_", "button", "hd_", "ecl"]):
                if self._game.statusbar:
                    self._game.statusbar.show(detail)
            # SFX based on response content
            if "authenticated" in detail:
                _audio.play_sfx("login")
            elif "completed" in detail:
                _audio.play_sfx("missionSuccess")
            elif "copied" in detail.lower() or "file" in detail.lower():
                _audio.play_sfx("success")
            elif "$" in detail:
                _audio.play_sfx("buy")
        elif status == "error":
            if self._game.statusbar:
                self._game.statusbar.show(f"Error: {detail}")
            _audio.play_sfx("error")

    def on_tab_switch(self, tab_name):
        """Called when tab bar selection changes."""
        data_requests = {
            "Map": lambda: self.net.get_links(),
            "Email": lambda: self.net.get_inbox(),
            "Gateway": lambda: (self.net.get_gateway_info(), self.net.get_gateway_files()),
            "Missions": lambda: self.net.get_missions(),
            "BBS": lambda: self.net.get_bbs(),
            "Software": lambda: self.net.get_software_list(),
            "Hardware": lambda: self.net.get_hardware_list(),
        }
        req = data_requests.get(tab_name)
        if req:
            req()
        self.net.get_balance()

        # Show the selected tab
        self._game.show_tab(tab_name)

    def _any_textinput_focused(self):
        """Check if any TextInput in the app currently has focus."""
        from kivy.uix.textinput import TextInput
        for widget in Window.children:
            for w in widget.walk():
                if isinstance(w, TextInput) and w.focus:
                    return True
        return False

    def _on_key_down(self, _window, key, _scancode=0, codepoint='', modifiers=None):
        if modifiers is None:
            modifiers = []
        if self._sm.current != 'game':
            return False

        # If a TextInput has focus, let it handle all keys except F-keys
        text_focused = self._any_textinput_focused()

        # F1-F8 tab switching (always works)
        if 282 <= key <= 289:
            idx = key - 282
            if self._game.tabbar and idx < 8:
                self._game.tabbar.switch_to(idx)
            return True

        # Enter: progress through dialogs/messages
        if key == 13:
            if self.net and self.net.state.player.get("connected"):
                st = self.net.state.screen_type
                if st == "DialogScreen":
                    self.net.dialog_ok()
                    return True
                if st == "MessageScreen":
                    # MessageScreen needs a click on the continue button
                    for btn in self.net.state.buttons:
                        if "messagescreen_click" in btn.get("name", ""):
                            self.net.send({"cmd": "click", "button": btn["name"]}, refresh_state=True)
                            return True
                    # Fallback
                    self.net.back()
                    return True

        # Don't intercept other keys when typing in a text field
        if text_focused:
            return False

        # Escape: disconnect
        if key == 27:
            if self.net and self.net.state.player.get("connected"):
                self.net.server_disconnect()
                return True

        # Backspace: go back
        if key == 8:
            if self.net and self.net.state.player.get("connected"):
                self.net.back()
                return True

        # Number keys 1-9: menu select
        if codepoint and '1' <= codepoint <= '9' and not modifiers:
            content = self._game.content_area
            if content:
                for child in content.children:
                    if hasattr(child, 'handle_number_key'):
                        if child.handle_number_key(int(codepoint)):
                            return True

        # P: run password breaker
        if codepoint == 'p' and not modifiers:
            st = self.net.state.screen_type if self.net else ""
            if st in ("PasswordScreen", "UserIDScreen"):
                self.net.crack_password()
                return True

        return False


def main():
    parser = argparse.ArgumentParser(description="Uplink Kivy Client")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9090)
    parser.add_argument("--no-music", action="store_true")
    parser.add_argument("--debug-log", default="")
    parser.add_argument("--auto-join", default="")
    parser.add_argument("--auto-connect", default="")
    parser.add_argument("--auto-crack", action="store_true")
    args = parser.parse_args()

    app = UplinkApp(
        host=args.host, port=args.port, no_music=args.no_music,
        debug_log=args.debug_log, auto_join=args.auto_join,
        auto_connect=args.auto_connect, auto_crack=args.auto_crack,
    )
    app.run()


if __name__ == '__main__':
    main()
