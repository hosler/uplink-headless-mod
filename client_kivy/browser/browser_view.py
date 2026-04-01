"""Browser tab: bookmarks, connecting animation, server screen rendering."""
import time
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.properties import StringProperty, NumericProperty, ObjectProperty
from kivy.clock import Clock
from kivy.app import App
from kivy.graphics import Color, Rectangle, Line

from theme.colors import (PRIMARY, SECONDARY, TEXT_DIM, TEXT_WHITE, PANEL_BG,
                          ROW_ALT, ROW_HOVER, SUCCESS)
from widgets.hacker_button import HackerButton
from widgets.hacker_panel import HackerPanel
from widgets.progress_bar import HackerProgressBar


class BookmarkRow(BoxLayout):
    """Single bookmark entry in the list."""
    def __init__(self, index, ip, name="", on_click=None, **kwargs):
        super().__init__(orientation='horizontal', size_hint_y=None, height=40, **kwargs)
        self.ip = ip
        self._on_click = on_click
        self._index = index

        # Row background
        with self.canvas.before:
            self._bg_color = Color(*(ROW_ALT if index % 2 else PANEL_BG))
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        # Number shortcut
        num = Label(
            text=f"[{index + 1}]" if index < 9 else "   ",
            font_name='AeroMatics', font_size='16sp',
            color=SECONDARY, size_hint_x=None, width=50,
            halign='center',
        )
        num.bind(size=num.setter('text_size'))

        # Diamond bullet
        bullet = Label(
            text='\u25c6', font_size='10sp',
            color=PRIMARY, size_hint_x=None, width=24,
        )

        # IP
        ip_label = Label(
            text=ip, font_name='AeroMatics', font_size='18sp',
            color=TEXT_WHITE, size_hint_x=None, width=200,
            halign='left',
        )
        ip_label.bind(size=ip_label.setter('text_size'))

        # Name
        name_label = Label(
            text=name, font_name='AeroMaticsLight', font_size='16sp',
            color=TEXT_DIM, halign='left',
        )
        name_label.bind(size=name_label.setter('text_size'))

        self.add_widget(num)
        self.add_widget(bullet)
        self.add_widget(ip_label)
        self.add_widget(name_label)

    def _update_bg(self, *_args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and touch.button == 'left':
            if self._on_click:
                self._on_click(self.ip)
                return True
        return super().on_touch_down(touch)


class BookmarksView(RelativeLayout):
    """Disconnected view: list of saved server bookmarks."""

    def __init__(self, net, **kwargs):
        super().__init__(**kwargs)
        self.net = net
        self._list_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self._list_layout.bind(minimum_height=self._list_layout.setter('height'))

        scroll = ScrollView(size_hint=(0.6, 0.8), pos_hint={'center_x': 0.5, 'center_y': 0.48},
                            scroll_type=['bars', 'content'],
                            bar_width=6, bar_color=(*PRIMARY[:3], 0.4))
        scroll.add_widget(self._list_layout)

        # Title
        title = Label(
            text='BOOKMARKS',
            font_name='AeroMatics', font_size='22sp',
            color=PRIMARY, size_hint=(None, None),
            size=(300, 40), pos_hint={'center_x': 0.5, 'top': 0.95},
        )

        self.add_widget(title)
        self.add_widget(scroll)

    def refresh(self, links):
        self._list_layout.clear_widgets()
        for i, link in enumerate(links):
            ip = link.get("ip", "") if isinstance(link, dict) else str(link)
            name = link.get("name", "") if isinstance(link, dict) else ""
            row = BookmarkRow(i, ip, name, on_click=self._connect_to)
            self._list_layout.add_widget(row)

        if not links:
            empty = Label(
                text='No bookmarks yet.\nConnect to a server to add one.',
                font_name='AeroMaticsLight', font_size='16sp',
                color=TEXT_DIM, halign='center', size_hint_y=None, height=80,
            )
            empty.bind(size=empty.setter('text_size'))
            self._list_layout.add_widget(empty)

    def _connect_to(self, ip):
        app = App.get_running_app()
        browser = self.parent
        if browser and hasattr(browser, 'connect_to'):
            browser.connect_to(ip)

    def handle_number_key(self, num):
        """Handle 1-9 key press to connect to bookmark by index."""
        links = self.net.state.links
        idx = num - 1
        if 0 <= idx < len(links):
            link = links[idx]
            ip = link.get("ip", "") if isinstance(link, dict) else str(link)
            self._connect_to(ip)
            return True
        return False


class ConnectingView(RelativeLayout):
    """Connection animation overlay."""

    def __init__(self, ip="", **kwargs):
        super().__init__(**kwargs)
        self.ip = ip
        self._start = time.time()

        self._label = Label(
            text=f'ESTABLISHING LINK TO {ip}',
            font_name='AeroMatics', font_size='20sp',
            color=PRIMARY, pos_hint={'center_x': 0.5, 'center_y': 0.55},
        )
        self._progress = HackerProgressBar(
            size_hint=(0.4, None), height=20,
            pos_hint={'center_x': 0.5, 'center_y': 0.45},
            bar_color=PRIMARY,
        )
        self.add_widget(self._label)
        self.add_widget(self._progress)
        self._anim_event = Clock.schedule_interval(self._animate, 1 / 30)

    def _animate(self, _dt):
        elapsed = time.time() - self._start
        self._progress.value = min(1.0, elapsed / 1.5)

    def stop(self):
        if self._anim_event:
            self._anim_event.cancel()


class BrowserView(RelativeLayout):
    """Main browser tab: bookmarks, connecting, or server screen."""
    tab_name = StringProperty("Browser")

    def __init__(self, net, statusbar, **kwargs):
        super().__init__(**kwargs)
        self.net = net
        self.statusbar = statusbar
        self._mode = "bookmarks"  # bookmarks | connecting | screen
        self._bookmarks = BookmarksView(net)
        self._connecting_view = None
        self._screen_host = None
        self._connect_start = 0
        self._connect_ip = ""

        self.add_widget(self._bookmarks)

        # Import ScreenHost lazily to avoid circular imports
        self._screen_host_cls = None

    def _get_screen_host(self):
        if self._screen_host is None:
            from browser.screen_host import ScreenHost
            self._screen_host = ScreenHost(net=self.net, statusbar=self.statusbar)
        return self._screen_host

    def connect_to(self, ip):
        """Initiate connection to a server."""
        self._mode = "connecting"
        self._connect_ip = ip
        self._connect_start = time.time()
        self.net.add_link(ip)
        self.net.server_connect(ip)
        self._show_connecting(ip)

    def _show_connecting(self, ip):
        self.clear_widgets()
        self._connecting_view = ConnectingView(ip=ip)
        self.add_widget(self._connecting_view)

    def _show_bookmarks(self):
        self.clear_widgets()
        self._bookmarks.refresh(self.net.state.links)
        self.add_widget(self._bookmarks)

    def _show_screen(self):
        self.clear_widgets()
        host = self._get_screen_host()
        self.add_widget(host)

    def update_state(self, state):
        """Called every poll cycle from the app."""
        connected = state.player.get("connected", False)

        if self._mode == "connecting":
            if time.time() - self._connect_start > 1.5:
                self._mode = "screen"
                if self._connecting_view:
                    self._connecting_view.stop()
                self._show_screen()

        elif self._mode == "screen" and not connected:
            self._mode = "bookmarks"
            self.net.get_links()
            self._show_bookmarks()

        # Update the active sub-view
        if self._mode == "bookmarks":
            self._bookmarks.refresh(state.links)
        elif self._mode == "screen":
            host = self._get_screen_host()
            host.update_state(state)

    def handle_number_key(self, num):
        if self._mode == "bookmarks":
            return self._bookmarks.handle_number_key(num)
        elif self._mode == "screen":
            host = self._get_screen_host()
            if hasattr(host, 'handle_number_key'):
                return host.handle_number_key(num)
        return False

    def handle_enter_key(self):
        if self._mode == "screen":
            host = self._get_screen_host()
            if hasattr(host, 'handle_enter_key'):
                return host.handle_enter_key()
        return False
