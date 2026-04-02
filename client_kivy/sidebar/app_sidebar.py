"""AppSidebar — software tools sidebar with running tool tracking."""
import time
import math
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.properties import BooleanProperty, ObjectProperty
from kivy.graphics import Color, Rectangle, Line, Ellipse
from kivy.clock import Clock

from theme.colors import (PRIMARY, SECONDARY, ALERT, SUCCESS, TEXT_WHITE,
                          TEXT_DIM, PANEL_BG, WARNING)
from widgets.hacker_button import HackerButton
from widgets.progress_bar import HackerProgressBar

# Known software tools with properties
TOOLS = {
    "Password_Breaker": {"icon": "PB", "color": ALERT, "auto": True},
    "Log_Deleter": {"icon": "LD", "color": (180/255, 140/255, 1, 1), "auto": False},
    "File_Copier": {"icon": "FC", "color": SUCCESS, "auto": False},
    "Decrypter": {"icon": "DC", "color": WARNING, "auto": True},
    "Trace_Tracker": {"icon": "TT", "color": PRIMARY, "auto": True},
    "Firewall_Bypass": {"icon": "FB", "color": (1, 100/255, 50/255, 1), "auto": True},
    "Dictionary_Hacker": {"icon": "DH", "color": ALERT, "auto": True},
    "Proxy_Bypass": {"icon": "PX", "color": (100/255, 200/255, 100/255, 1), "auto": True},
    "Defrag": {"icon": "DF", "color": TEXT_DIM, "auto": True},
    "Monitor": {"icon": "MN", "color": SECONDARY, "auto": True},
    "HUD_ConnectionAnalysis": {"icon": "CA", "color": PRIMARY, "auto": True},
    "Voice_Analyser": {"icon": "VA", "color": SUCCESS, "auto": True},
    "IP_Probe": {"icon": "IP", "color": PRIMARY, "auto": True},
    "IP_Lookup": {"icon": "IL", "color": PRIMARY, "auto": True},
    "LAN_Scan": {"icon": "LS", "color": PRIMARY, "auto": True},
    "LAN_Probe": {"icon": "LP", "color": PRIMARY, "auto": True},
    "LAN_Spoof": {"icon": "SP", "color": (1, 100/255, 50/255, 1), "auto": True},
}


class RunningApp:
    """Tracks a running software tool."""
    def __init__(self, title, tool_info):
        self.title = title
        self.tool_info = tool_info
        self.start_time = time.time()
        self.duration = 0  # 0 = persistent, >0 = timed
        self.active = True

    @property
    def icon(self):
        return self.tool_info.get("icon", "??")

    @property
    def color(self):
        return self.tool_info.get("color", SECONDARY)

    @property
    def elapsed(self):
        return time.time() - self.start_time

    @property
    def progress(self):
        if self.duration <= 0:
            return 0
        return min(1.0, self.elapsed / self.duration)


class RunningSlot(BoxLayout):
    """UI for a running tool — shows pulsing indicator, name, stop button."""
    def __init__(self, running_app, on_stop=None, **kwargs):
        super().__init__(orientation='horizontal', size_hint_y=None, height=38,
                         spacing=4, padding=[4, 2], **kwargs)
        self.running_app = running_app
        self._on_stop = on_stop
        color = running_app.color

        with self.canvas.before:
            Color(*PANEL_BG, 0.9)
            self._bg = Rectangle(pos=self.pos, size=self.size)
            Color(*color[:3], 0.5)
            self._border = Line(rectangle=[*self.pos, *self.size], width=1)
        self.bind(pos=self._upd, size=self._upd)

        # Pulsing indicator
        self._indicator = Label(text='\u25c6', font_size='10sp', color=color,
                                size_hint_x=None, width=18)
        # Name
        name = Label(text=running_app.title.replace("_", " ")[:12],
                     font_name='AeroMaticsLight', font_size='11sp',
                     color=TEXT_WHITE, halign='left', valign='middle')
        name.bind(size=name.setter('text_size'))
        # Status
        self._status = Label(text='ACTIVE', font_name='AeroMatics', font_size='9sp',
                             color=SUCCESS, size_hint_x=None, width=50)
        # Stop
        stop_btn = Label(text='X', font_name='AeroMatics', font_size='12sp',
                         color=ALERT, size_hint_x=None, width=20)

        self.add_widget(self._indicator)
        self.add_widget(name)
        self.add_widget(self._status)
        self.add_widget(stop_btn)

    def _upd(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._border.rectangle = [*self.pos, *self.size]

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            # Click on X to stop
            if self._on_stop:
                self._on_stop(self.running_app)
            return True
        return super().on_touch_down(touch)


class ToolSlot(BoxLayout):
    """Available tool in the sidebar."""
    def __init__(self, title, tool_info, on_run=None, **kwargs):
        super().__init__(orientation='horizontal', size_hint_y=None, height=38,
                         spacing=6, padding=[4, 2], **kwargs)
        self.title = title
        self._on_run = on_run

        icon_text = tool_info.get("icon", "??")
        color = tool_info.get("color", SECONDARY)

        with self.canvas.before:
            Color(*PANEL_BG, 0.85)
            self._bg = Rectangle(pos=self.pos, size=self.size)
            Color(*color[:3], 0.2)
            self._border = Line(rectangle=[*self.pos, *self.size], width=0.8)
        self.bind(pos=self._upd, size=self._upd)

        icon = Label(text=icon_text, font_name='AeroMatics', font_size='12sp',
                     color=color, size_hint_x=None, width=28,
                     halign='center', valign='middle')
        icon.bind(size=icon.setter('text_size'))

        short_name = title.replace("_", " ")[:14]
        name = Label(text=short_name, font_name='AeroMaticsLight', font_size='11sp',
                     color=TEXT_WHITE, halign='left', valign='middle')
        name.bind(size=name.setter('text_size'))

        self.add_widget(icon)
        self.add_widget(name)

    def _upd(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._border.rectangle = [*self.pos, *self.size]

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and touch.button == 'left':
            if self._on_run:
                self._on_run(self.title)
                return True
        return super().on_touch_down(touch)


class AppSidebar(BoxLayout):
    """Sidebar showing running + available software tools."""
    visible = BooleanProperty(False)
    net = ObjectProperty(None, allownone=True)
    statusbar = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.size_hint = (None, None)
        self.width = 170
        self.padding = [4, 4]
        self.spacing = 2
        self.on_tool_run = None  # callback(tool_name)
        self.running = []  # list of RunningApp

        with self.canvas.before:
            Color(*PANEL_BG, 0.92)
            self._bg = Rectangle(pos=self.pos, size=self.size)
            Color(*SECONDARY[:3], 0.3)
            self._border = Line(rectangle=[*self.pos, *self.size], width=1)
        self.bind(pos=self._upd_bg, size=self._upd_bg, visible=self._on_visible)

        # Title
        self._title = Label(text='TOOLS', font_name='AeroMatics', font_size='13sp',
                            color=PRIMARY, size_hint_y=None, height=20)
        self.add_widget(self._title)

        # Running section
        self._running_label = Label(text='RUNNING', font_name='AeroMatics', font_size='10sp',
                                    color=SUCCESS, size_hint_y=None, height=16, halign='left')
        self._running_label.bind(size=self._running_label.setter('text_size'))
        self._running_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=2)
        self._running_list.bind(minimum_height=self._running_list.setter('height'))

        # Separator
        self._sep = Label(text='AVAILABLE', font_name='AeroMatics', font_size='10sp',
                          color=TEXT_DIM, size_hint_y=None, height=16, halign='left')
        self._sep.bind(size=self._sep.setter('text_size'))

        # Available tools
        self._tool_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=2)
        self._tool_list.bind(minimum_height=self._tool_list.setter('height'))
        scroll = ScrollView(size_hint_y=1)
        inner = BoxLayout(orientation='vertical', size_hint_y=None, spacing=2)
        inner.bind(minimum_height=inner.setter('height'))
        inner.add_widget(self._running_label)
        inner.add_widget(self._running_list)
        inner.add_widget(self._sep)
        inner.add_widget(self._tool_list)
        scroll.add_widget(inner)
        self.add_widget(scroll)

        self._last_tools = []
        self.opacity = 0

    def _upd_bg(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._border.rectangle = [*self.pos, *self.size]

    def _on_visible(self, *_):
        self.opacity = 1 if self.visible else 0
        self.disabled = not self.visible

    def clear_all(self):
        """Clear running tools when disconnected."""
        self.running.clear()
        self._running_list.clear_widgets()

    def update_state(self, state):
        """Rebuild tool list from gateway files."""
        if not self.visible:
            return
        try:
            self._do_update(state)
        except Exception:
            pass  # Sidebar updates are non-critical

    def _do_update(self, state):
        if not state.gateway_files:
            return
        gateway_files = state.gateway_files
        tools = []
        seen = set()
        for f in gateway_files:
            title = f.get("title", "")
            for tool_name, tool_info in TOOLS.items():
                if title.startswith(tool_name) or title.replace(" ", "_").startswith(tool_name):
                    if tool_name not in seen:
                        seen.add(tool_name)
                        tools.append((tool_name, tool_info))
                    break

        keys = [t[0] for t in tools]
        if keys != self._last_tools:
            self._last_tools = keys
            self._tool_list.clear_widgets()
            running_names = {r.title for r in self.running}
            for name, info in tools:
                if name not in running_names:
                    slot = ToolSlot(name, info, on_run=self._run_tool)
                    self._tool_list.add_widget(slot)

        # Update running list
        self._running_list.clear_widgets()
        for ra in self.running:
            slot = RunningSlot(ra, on_stop=self._stop_tool)
            self._running_list.add_widget(slot)

        # Show/hide labels
        self._running_label.opacity = 1 if self.running else 0
        self._running_label.height = 16 if self.running else 0

        # Adjust height
        total = len(tools) + len(self.running)
        self.height = min(total * 42 + 60, self.parent.height * 0.7 if self.parent else 400)

    def _run_tool(self, name):
        # Check not already running
        if any(r.title == name for r in self.running):
            return
        tool_info = TOOLS.get(name, {})
        ra = RunningApp(name, tool_info)
        self.running.append(ra)

        if self.on_tool_run:
            self.on_tool_run(name)
        if self.statusbar:
            self.statusbar.show(f"Running {name.replace('_', ' ')}")

    def _stop_tool(self, ra):
        if ra in self.running:
            self.running.remove(ra)
