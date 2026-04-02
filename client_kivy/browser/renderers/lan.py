"""LANRenderer — LAN topology visualization with Canvas node graph."""
import math
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line, Ellipse, Rectangle
from kivy.core.text import Label as CoreLabel
from kivy.clock import Clock

from theme.colors import (PRIMARY, SECONDARY, TEXT_WHITE, TEXT_DIM, PANEL_BG,
                          ALERT, SUCCESS, WARNING)
from widgets.hacker_button import HackerButton
from browser.renderers.base import BaseRenderer

# Node type colors
TYPE_COLORS = {
    "Router": PRIMARY,
    "Hub": SECONDARY,
    "Terminal": (140/255, 170/255, 200/255, 1),
    "MainServer": WARNING,
    "MailServer": SUCCESS,
    "FileServer": SUCCESS,
    "Authentication": ALERT,
    "Lock": ALERT,
    "IsolationBridge": (1, 100/255, 50/255, 1),
    "Modem": (100/255, 200/255, 100/255, 1),
    "LogServer": (180/255, 140/255, 1, 1),
}


class LANGraph(Widget):
    """Canvas-drawn LAN topology."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._systems = []
        self._links = []
        self._selected = -1
        self._on_select = None
        self.bind(size=self._redraw, pos=self._redraw)

    def set_data(self, systems, links):
        self._systems = systems
        self._links = links
        self._redraw()

    def set_selected(self, idx):
        self._selected = idx
        self._redraw()

    def _redraw(self, *_args):
        self.canvas.clear()
        w, h = self.size
        ox, oy = self.pos
        if w < 10 or h < 10 or not self._systems:
            return

        with self.canvas:
            # Background
            Color(8/255, 14/255, 22/255, 1)
            Rectangle(pos=self.pos, size=self.size)

            # Grid
            Color(18/255, 30/255, 42/255, 0.4)
            for i in range(9):
                gx = ox + w * i / 8
                Line(points=[gx, oy, gx, oy + h], width=0.5)
            for i in range(7):
                gy = oy + h * i / 6
                Line(points=[ox, gy, ox + w, gy], width=0.5)

            # Links between systems
            for link in self._links:
                fi = link.get("from", -1)
                ti = link.get("to", -1)
                sec = link.get("security", 0)
                sys_from = next((s for s in self._systems if s.get("index") == fi), None)
                sys_to = next((s for s in self._systems if s.get("index") == ti), None)
                if sys_from and sys_to:
                    x1 = ox + sys_from.get("x", 0.5) * w
                    y1 = oy + (1 - sys_from.get("y", 0.5)) * h
                    x2 = ox + sys_to.get("x", 0.5) * w
                    y2 = oy + (1 - sys_to.get("y", 0.5)) * h
                    if sec > 1:
                        Color(*ALERT[:3], 0.6)
                        lw = 2
                    elif sec == 1:
                        Color(*SECONDARY[:3], 0.4)
                        lw = 1.5
                    else:
                        Color(20/255, 30/255, 40/255, 0.5)
                        lw = 1
                    Line(points=[x1, y1, x2, y2], width=lw)

            # Nodes
            for sys_info in self._systems:
                idx = sys_info.get("index", -1)
                x = sys_info.get("x", 0.5)
                y = sys_info.get("y", 0.5)
                type_name = sys_info.get("typeName", "Unknown")
                sec = sys_info.get("security", 0)
                visible = sys_info.get("visible", 1)
                screen_idx = sys_info.get("screenIndex", -1)

                px = ox + x * w
                py = oy + (1 - y) * h  # flip Y

                color = TYPE_COLORS.get(type_name, SECONDARY)
                is_selected = idx == self._selected

                # Selection glow
                if is_selected:
                    Color(*color[:3], 0.25)
                    Ellipse(pos=(px - 18, py - 18), size=(36, 36))

                # Node diamond
                sz = 8
                Color(*color)
                Line(points=[px, py + sz, px + sz, py, px, py - sz, px - sz, py, px, py + sz],
                     width=1.5 if is_selected else 1)
                # Inner dot
                Color(*color[:3], 0.5)
                Ellipse(pos=(px - 3, py - 3), size=(6, 6))

                # Security indicator
                if sec > 0:
                    Color(*ALERT[:3], 0.3)
                    Ellipse(pos=(px - 12, py - 12), size=(24, 24))

                # Label
                label_color = TEXT_WHITE if is_selected else (*TEXT_DIM[:3], 0.8)
                cl = CoreLabel(text=type_name, font_size=10, color=label_color)
                cl.refresh()
                tex = cl.texture
                if tex:
                    Color(1, 1, 1, 1)
                    Rectangle(texture=tex,
                              pos=(px - tex.width / 2, py - 18),
                              size=tex.size)

                # Navigable indicator
                if screen_idx >= 0:
                    Color(*SUCCESS[:3], 0.5)
                    Ellipse(pos=(px + 8, py + 6), size=(5, 5))

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos) or touch.button != 'left':
            return False
        w, h = self.size
        ox, oy = self.pos
        for sys_info in self._systems:
            x = sys_info.get("x", 0.5)
            y = sys_info.get("y", 0.5)
            px = ox + x * w
            py = oy + (1 - y) * h
            if abs(touch.pos[0] - px) < 18 and abs(touch.pos[1] - py) < 18:
                self._selected = sys_info.get("index", -1)
                if self._on_select:
                    self._on_select(sys_info)
                self._redraw()
                return True
        # Click empty = deselect
        self._selected = -1
        if self._on_select:
            self._on_select(None)
        self._redraw()
        return True


class LANRenderer(BaseRenderer):
    """Renders LAN topology — interactive node graph with connect-to-node."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._title_label.text = "WIRELESS LAN RECEIVER"

        # Signal strength meter (decorative)
        signal = BoxLayout(size_hint=(None, None), size=(80, 20),
                          pos_hint={'right': 0.95, 'top': 0.93}, spacing=3)
        for i in range(5):
            bar = Label(text='\u2588', font_size=f'{8 + i * 2}sp',
                        color=(*PRIMARY[:3], 0.3 + i * 0.15),
                        size_hint_x=None, width=14)
            signal.add_widget(bar)
        self.add_widget(signal)

        # Graph widget
        self._graph = LANGraph(size_hint=(0.9, 0.6),
                               pos_hint={'center_x': 0.5, 'center_y': 0.52})
        self._graph._on_select = self._on_node_select
        self.add_widget(self._graph)

        # Info panel
        self._info_box = BoxLayout(orientation='horizontal', spacing=10,
                                   size_hint=(0.7, None), height=40,
                                   pos_hint={'center_x': 0.5, 'y': 0.05})
        self._info_label = Label(text='Click a node to inspect',
                                 font_name='AeroMaticsLight', font_size='14sp',
                                 color=TEXT_DIM, halign='left')
        self._info_label.bind(size=self._info_label.setter('text_size'))
        self._connect_btn = HackerButton(text='CONNECT TO NODE',
                                         size_hint_x=None, width=180,
                                         font_size='13sp', button_color=SUCCESS)
        self._connect_btn.bind(on_release=lambda *_: self._connect_to_node())
        self._connect_btn.opacity = 0
        self._info_box.add_widget(self._info_label)
        self._info_box.add_widget(self._connect_btn)
        self.add_widget(self._info_box)

        self._selected_sys = None
        self._last_systems = []

    def on_state_update(self, state):
        systems = state.lan_data.get("systems", [])
        links = state.lan_data.get("links", [])
        keys = [s.get("index", 0) for s in systems]
        if keys != self._last_systems:
            self._last_systems = keys
            self._graph.set_data(systems, links)

    def _on_node_select(self, sys_info):
        self._selected_sys = sys_info
        if sys_info:
            type_name = sys_info.get("typeName", "Unknown")
            sec = sys_info.get("security", 0)
            idx = sys_info.get("index", -1)
            screen_idx = sys_info.get("screenIndex", -1)
            self._info_label.text = f"{type_name}  |  Security: {sec}  |  Node #{idx}"
            self._connect_btn.opacity = 1 if screen_idx >= 0 else 0
            self._connect_btn.disabled = screen_idx < 0
        else:
            self._info_label.text = "Click a node to inspect"
            self._connect_btn.opacity = 0

    def _connect_to_node(self):
        if self._selected_sys and self.net:
            screen_idx = self._selected_sys.get("screenIndex", -1)
            if screen_idx >= 0:
                self.net.navigate(screen_idx)
