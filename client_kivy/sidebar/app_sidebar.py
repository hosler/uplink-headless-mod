"""AppSidebar — software tools sidebar for hacking sessions."""
import time
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.properties import BooleanProperty, ObjectProperty
from kivy.graphics import Color, Rectangle, Line
from kivy.clock import Clock

from theme.colors import (PRIMARY, SECONDARY, ALERT, SUCCESS, TEXT_WHITE,
                          TEXT_DIM, PANEL_BG, WARNING)
from widgets.hacker_button import HackerButton

# Known software tools
TOOLS = {
    "Password_Breaker": {"icon": "PB", "color": ALERT},
    "Log_Deleter": {"icon": "LD", "color": (180/255, 140/255, 1, 1)},
    "File_Copier": {"icon": "FC", "color": SUCCESS},
    "Decrypter": {"icon": "DC", "color": WARNING},
    "Trace_Tracker": {"icon": "TT", "color": PRIMARY},
    "Firewall_Bypass": {"icon": "FB", "color": (1, 100/255, 50/255, 1)},
    "Dictionary_Hacker": {"icon": "DH", "color": ALERT},
    "Proxy_Bypass": {"icon": "PX", "color": (100/255, 200/255, 100/255, 1)},
    "Defrag": {"icon": "DF", "color": TEXT_DIM},
    "Monitor": {"icon": "MN", "color": SECONDARY},
    "HUD_ConnectionAnalysis": {"icon": "CA", "color": PRIMARY},
    "Voice_Analyser": {"icon": "VA", "color": SUCCESS},
    "IP_Probe": {"icon": "IP", "color": PRIMARY},
    "IP_Lookup": {"icon": "IL", "color": PRIMARY},
    "LAN_Scan": {"icon": "LS", "color": PRIMARY},
    "LAN_Probe": {"icon": "LP", "color": PRIMARY},
    "LAN_Spoof": {"icon": "SP", "color": (1, 100/255, 50/255, 1)},
}


class ToolSlot(BoxLayout):
    """Single tool in the sidebar."""
    def __init__(self, title, tool_info, on_run=None, **kwargs):
        super().__init__(orientation='horizontal', size_hint_y=None, height=44,
                         spacing=6, padding=[4, 2], **kwargs)
        self.title = title
        self._on_run = on_run

        icon_text = tool_info.get("icon", "??")
        color = tool_info.get("color", SECONDARY)

        with self.canvas.before:
            Color(*PANEL_BG, 0.85)
            self._bg = Rectangle(pos=self.pos, size=self.size)
            Color(*color[:3], 0.3)
            self._border = Line(rectangle=[*self.pos, *self.size], width=0.8)
        self.bind(pos=self._upd, size=self._upd)

        # Icon
        icon = Label(text=icon_text, font_name='AeroMatics', font_size='13sp',
                     color=color, size_hint_x=None, width=30,
                     halign='center', valign='middle')
        icon.bind(size=icon.setter('text_size'))

        # Name
        short_name = title.replace("_", " ")[:14]
        name = Label(text=short_name, font_name='AeroMaticsLight', font_size='12sp',
                     color=TEXT_WHITE, halign='left', valign='middle')
        name.bind(size=name.setter('text_size'))

        self.add_widget(icon)
        self.add_widget(name)

    def _upd(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._border.rectangle = [*self.pos, *self.size]

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if self._on_run:
                self._on_run(self.title)
            return True
        return super().on_touch_down(touch)


class AppSidebar(BoxLayout):
    """Sidebar showing available software tools."""
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

        with self.canvas.before:
            Color(*PANEL_BG, 0.9)
            self._bg = Rectangle(pos=self.pos, size=self.size)
            Color(*SECONDARY[:3], 0.3)
            self._border = Line(rectangle=[*self.pos, *self.size], width=1)
        self.bind(pos=self._upd_bg, size=self._upd_bg, visible=self._on_visible)

        # Title
        self._title = Label(text='TOOLS', font_name='AeroMatics', font_size='13sp',
                            color=PRIMARY, size_hint_y=None, height=22)
        self.add_widget(self._title)

        self._tool_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=2)
        self._tool_list.bind(minimum_height=self._tool_list.setter('height'))
        scroll = ScrollView(size_hint_y=1)
        scroll.add_widget(self._tool_list)
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

    def update_state(self, state):
        """Rebuild tool list from gateway files."""
        if not self.visible:
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
            for name, info in tools:
                slot = ToolSlot(name, info, on_run=self._run_tool)
                self._tool_list.add_widget(slot)

        # Adjust height
        self.height = min(len(tools) * 46 + 30, self.parent.height * 0.7 if self.parent else 400)

    def _run_tool(self, name):
        if self.on_tool_run:
            self.on_tool_run(name)
        if self.statusbar:
            self.statusbar.show(f"Running {name.replace('_', ' ')}")
