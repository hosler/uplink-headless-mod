"""Game screen — topbar, tabs, content area, statusbar."""
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.properties import (ObjectProperty, StringProperty, NumericProperty,
                              ListProperty, BooleanProperty)
from kivy.clock import Clock
from kivy.app import App

from theme.colors import PRIMARY, SECONDARY, TEXT_DIM, TEXT_WHITE, SUCCESS, WARNING, ALERT
from widgets.hacker_button import HackerButton


TAB_NAMES = ["Browser", "Map", "Email", "Gateway", "Missions", "BBS", "Software", "Hardware"]


class TopBar(BoxLayout):
    agent_handle = StringProperty("")
    remote_host = StringProperty("")
    screen_title = StringProperty("")
    balance = NumericProperty(0)
    speed = NumericProperty(0)
    game_date = StringProperty("")

    def set_speed(self, val):
        app = App.get_running_app()
        if app.net:
            app.net.set_speed(val)


class TabBar(BoxLayout):
    active_tab = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._buttons = []

    def build_tabs(self):
        self.clear_widgets()
        self._buttons = []
        for i, name in enumerate(TAB_NAMES):
            btn = HackerButton(
                text=name.upper(),
                size_hint_x=1,
                font_size='15sp',
            )
            btn.bind(on_release=lambda _, idx=i: self.switch_to(idx))
            self._buttons.append(btn)
            self.add_widget(btn)
        self._update_highlight()

    def switch_to(self, idx):
        if idx != self.active_tab:
            self.active_tab = idx
            self._update_highlight()
            app = App.get_running_app()
            app.on_tab_switch(TAB_NAMES[idx])

    def _update_highlight(self):
        for i, btn in enumerate(self._buttons):
            if i == self.active_tab:
                btn.button_color = PRIMARY
                btn.bold = True
            else:
                btn.button_color = TEXT_DIM
                btn.bold = False


class StatusBar(BoxLayout):
    chain_text = StringProperty("")
    status_message = StringProperty("")
    trace_progress = NumericProperty(0)
    trace_active = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._msg_timer = None

    def show(self, msg):
        self.status_message = msg
        if self._msg_timer:
            self._msg_timer.cancel()
        self._msg_timer = Clock.schedule_once(self._clear_message, 4.0)

    def _clear_message(self, _dt):
        self.status_message = ""


class GameScreen(Screen):
    topbar = ObjectProperty(None)
    tabbar = ObjectProperty(None)
    statusbar = ObjectProperty(None)
    content_area = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._browser = None
        self._tab_views = {}

    def on_enter(self, *_args):
        if self.tabbar:
            self.tabbar.build_tabs()
        self._init_views()

    def _init_views(self):
        """Create all tab views and sidebar."""
        if self._browser is not None:
            return
        app = App.get_running_app()
        net = app.net
        sb = self.statusbar

        # Browser
        from browser.browser_view import BrowserView
        self._browser = BrowserView(net=net, statusbar=sb)
        self._browser.size_hint = (1, 1)
        self._tab_views["Browser"] = self._browser

        # Map
        from map.map_view import MapView
        self._map = MapView(net=net)
        self._map.size_hint = (1, 1)
        self._tab_views["Map"] = self._map

        # Content tabs
        from tabs.email_view import EmailView
        from tabs.gateway_view import GatewayView
        from tabs.missions_view import MissionsView
        from tabs.bbs_view import BBSView
        from tabs.software_view import SoftwareView
        from tabs.hardware_view import HardwareView

        for cls in [EmailView, GatewayView, MissionsView, BBSView, SoftwareView, HardwareView]:
            view = cls(net=net, statusbar=sb)
            view.size_hint = (1, 1)
            self._tab_views[view.tab_name] = view

        # Sidebar
        from sidebar.app_sidebar import AppSidebar
        self._sidebar = AppSidebar(net=net, statusbar=sb)
        self._sidebar.pos_hint = {'x': 0, 'top': 1}
        self._sidebar.on_tool_run = app._on_tool_run

        # Task manager overlay
        from widgets.task_manager import TaskManager
        self._task_mgr = TaskManager(size_hint=(1, 1), sidebar=self._sidebar)

        # CRT overlay
        from widgets.crt_overlay import CRTOverlay
        self._crt = CRTOverlay(size_hint=(1, 1))

        # Show initial tab
        self.content_area.add_widget(self._browser)

    def get_active_view(self):
        """Return the currently visible tab view."""
        tab_name = TAB_NAMES[self.tabbar.active_tab] if self.tabbar else "Browser"
        return self._tab_views.get(tab_name)

    def show_tab(self, tab_name):
        """Show the given tab's view, hide others."""
        # Remove overlays before clearing (so they're not destroyed)
        if hasattr(self, '_sidebar') and self._sidebar.parent == self.content_area:
            self.content_area.remove_widget(self._sidebar)
        if hasattr(self, '_task_mgr') and self._task_mgr.parent == self.content_area:
            self.content_area.remove_widget(self._task_mgr)

        self.content_area.clear_widgets()
        view = self._tab_views.get(tab_name)
        if view:
            self.content_area.add_widget(view)
            if hasattr(view, 'on_activate'):
                view.on_activate()

        # Sidebar only on browser when connected
        if hasattr(self, '_sidebar'):
            app = App.get_running_app()
            connected = app.net.state.player.get("connected", False) if app.net else False
            self._sidebar.visible = tab_name == "Browser" and connected
            if self._sidebar.visible:
                self.content_area.add_widget(self._sidebar)
            else:
                self._sidebar.clear_all()

    def update_views(self, state):
        """Update the active content view with fresh state."""
        try:
            tab_name = TAB_NAMES[self.tabbar.active_tab] if self.tabbar else "Browser"
            view = self._tab_views.get(tab_name)
            if view and hasattr(view, 'update_state'):
                view.update_state(state)

            # Sidebar: show/hide based on connection + tab
            if hasattr(self, '_sidebar'):
                connected = state.player.get("connected", False)
                should_show = tab_name == "Browser" and connected
                if should_show and not self._sidebar.visible:
                    self._sidebar.visible = True
                    if self._sidebar.parent != self.content_area:
                        self.content_area.add_widget(self._sidebar)
                    # Request gateway files for tool list (once per second max)
                    app = App.get_running_app()
                    now = __import__('time').time()
                    last_req = getattr(self, '_gw_last_req', 0)
                    if app.net and not state.gateway_files and now - last_req > 1.0:
                        self._gw_last_req = now
                        app.net.get_gateway_files()
                elif not should_show and self._sidebar.visible:
                    self._sidebar.visible = False
                    self._gw_last_req = 0
                    if self._sidebar.parent:
                        self._sidebar.parent.remove_widget(self._sidebar)
                    self._sidebar.clear_all()

                if self._sidebar.visible:
                    self._sidebar.update_state(state)

            # Task manager
            if hasattr(self, '_task_mgr'):
                self._task_mgr.update_state(state)
                if self._task_mgr.visible and self._task_mgr.parent != self.content_area:
                    self.content_area.add_widget(self._task_mgr)
                elif not self._task_mgr.visible and self._task_mgr.parent == self.content_area:
                    self.content_area.remove_widget(self._task_mgr)
        except Exception:
            pass  # Don't crash on state update errors
