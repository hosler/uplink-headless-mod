"""ScreenHost — dispatches to the correct renderer based on screen_type."""
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.label import Label
from kivy.properties import ObjectProperty

from theme.colors import TEXT_DIM


class ScreenHost(RelativeLayout):
    """Hosts the active screen renderer. Swaps widgets on screen_type change."""
    net = ObjectProperty(None, allownone=True)
    statusbar = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._current_renderer = None
        self._current_key = ""
        self._renderers = {}  # lazy-loaded cache
        self._data_requested = False
        self._fallback = Label(
            text='', font_name='AeroMaticsLight', font_size='16sp',
            color=TEXT_DIM, halign='center', valign='middle',
        )
        self._fallback.bind(size=self._fallback.setter('text_size'))

    def _get_renderer_class(self, key):
        """Lazy-import renderer classes."""
        if key in ("MenuScreen", "HighSecurityScreen"):
            from browser.renderers.menu import MenuRenderer
            return MenuRenderer
        if key in ("PasswordScreen", "UserIDScreen"):
            from browser.renderers.password import PasswordRenderer
            return PasswordRenderer
        if key == "DialogScreen":
            from browser.renderers.dialog import DialogRenderer
            return DialogRenderer
        if key == "MessageScreen":
            from browser.renderers.message import MessageRenderer
            return MessageRenderer
        if key == "LinksScreen":
            from browser.renderers.links import LinksRenderer
            return LinksRenderer
        if key == "LogScreen":
            from browser.renderers.log_viewer import LogViewerRenderer
            return LogViewerRenderer
        if key == "file_server":
            from browser.renderers.file_server import FileServerRenderer
            return FileServerRenderer
        if key == "records":
            from browser.renderers.records import RecordsRenderer
            return RecordsRenderer
        if key == "security":
            from browser.renderers.security import SecurityRenderer
            return SecurityRenderer
        if key == "console":
            from browser.renderers.console import ConsoleRenderer
            return ConsoleRenderer
        if key == "company_info":
            from browser.renderers.company_info import CompanyInfoRenderer
            return CompanyInfoRenderer
        if key == "rankings":
            from browser.renderers.rankings import RankingsRenderer
            return RankingsRenderer
        if key == "news":
            from browser.renderers.news import NewsRenderer
            return NewsRenderer
        if key == "LanScreen":
            from browser.renderers.lan import LANRenderer
            return LANRenderer
        return None

    def _compute_key(self, state):
        """Determine renderer key from state, including GenericScreen sub-dispatch."""
        st = state.screen_type
        if st in ("MenuScreen", "HighSecurityScreen", "PasswordScreen", "UserIDScreen",
                   "DialogScreen", "MessageScreen", "LinksScreen", "LogScreen", "LanScreen"):
            return st
        if st in ("GenericScreen", "unknown"):
            return self._detect_generic_subtype(state)
        if st == "none" and state.lan_data.get("systems"):
            return "LanScreen"
        return st

    def _detect_generic_subtype(self, state):
        """Detect GenericScreen subtype by button names and subtitle."""
        btn_names = [b.get("name", "") for b in state.buttons]
        subtitle = state.screen_data.get("subtitle", "").lower()
        if any(n.startswith("recordscreen_title") for n in btn_names):
            return "records"
        if any(n.startswith("securityscreen_system") for n in btn_names):
            return "security"
        if any(n == "console_typehere" for n in btn_names):
            return "console"
        if any(n.startswith("companyscreen_") for n in btn_names):
            return "company_info"
        if "ranking" in subtitle:
            return "rankings"
        if "news" in subtitle:
            return "news"
        if ("file" in subtitle or "server" in subtitle) and "news" not in subtitle:
            return "file_server"
        return "generic_fallback"

    def update_state(self, state):
        key = self._compute_key(state)
        if key != self._current_key:
            # Clear stale data from previous screen (critical for dedup)
            state.remote_files = []
            state.remote_logs = []
            state.screen_links = []
            state.news = []
            self._data_requested = False
            self._swap_renderer(key)
            self._current_key = key

        if self._current_renderer:
            self._current_renderer.update_state(state)

        # Request supplementary data (once per screen)
        if not self._data_requested:
            self._request_data(key, state)

    def _request_data(self, key, state):
        """Auto-request files/logs/links/news based on screen type."""
        self._data_requested = True
        if key == "file_server":
            self.net.get_files()
        elif key == "LogScreen":
            self.net.get_logs()
        elif key == "LinksScreen":
            self.net.get_screen_links()
        elif key == "news" and not state.news:
            self.net.get_news()
        elif key == "LanScreen" and not state.lan_data.get("systems"):
            self.net.lan_scan()

    def _swap_renderer(self, key):
        # Remove old
        if self._current_renderer:
            if hasattr(self._current_renderer, 'on_leave'):
                self._current_renderer.on_leave()
            self.remove_widget(self._current_renderer)
        self._current_renderer = None

        # Try to get/create renderer
        cls = self._get_renderer_class(key)
        if cls:
            renderer = cls(net=self.net, statusbar=self.statusbar)
            if hasattr(renderer, 'on_enter'):
                renderer.on_enter()
            self._current_renderer = renderer
            self.add_widget(renderer)
        else:
            # Fallback label
            self._fallback.text = f"[{key}]"
            self.add_widget(self._fallback)
            self._current_renderer = None

    def handle_number_key(self, num):
        if self._current_renderer and hasattr(self._current_renderer, 'handle_number_key'):
            return self._current_renderer.handle_number_key(num)
        return False

    def handle_enter_key(self):
        if self._current_renderer and hasattr(self._current_renderer, 'handle_enter_key'):
            return self._current_renderer.handle_enter_key()
        return False
