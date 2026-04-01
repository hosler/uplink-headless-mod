"""MapView — network topology visualization with Canvas drawing."""
import hashlib
import time
import math
from kivy.uix.widget import Widget
from kivy.properties import ObjectProperty, StringProperty
from kivy.graphics import Color, Line, Ellipse, Rectangle
from kivy.graphics.texture import Texture
from kivy.clock import Clock
from kivy.core.text import Label as CoreLabel
from kivy.app import App

from theme.colors import (PRIMARY, SECONDARY, TEXT_WHITE, TEXT_DIM, SUCCESS,
                          WARNING, ALERT, PANEL_BG)


def _ip_to_pos(ip):
    """Deterministic position from IP string (0-1 range)."""
    h = hashlib.md5(ip.encode()).digest()
    x = (h[0] + h[1] * 256) / 65535.0
    y = (h[2] + h[3] * 256) / 65535.0
    x = 0.06 + x * 0.88
    y = 0.08 + y * 0.84
    return x, y


class MapView(Widget):
    """Network topology map with server nodes, connections, and bounce paths."""
    tab_name = StringProperty("Map")
    net = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._links = []
        self._connection_nodes = []
        self._trace_pct = 0
        self._packets = []  # animated data packets along connection
        self._packet_time = 0
        self._hovered = None

        self.bind(size=self._redraw, pos=self._redraw)
        Clock.schedule_interval(self._tick, 1 / 20)

    def on_activate(self):
        if self.net:
            self.net.get_links()
            self.net.get_trace()

    def update_state(self, state):
        self._links = state.links
        self._connection_nodes = state.connection.get("nodes", [])
        trace = state.trace
        if trace.get("active"):
            self._trace_pct = trace.get("progress", 0) / max(trace.get("total", 1), 1)
        else:
            self._trace_pct = 0
        self._redraw()

    def _tick(self, dt):
        self._packet_time += dt
        if self._connection_nodes and len(self._connection_nodes) > 1:
            self._redraw()

    def _redraw(self, *_args):
        self.canvas.clear()
        w, h = self.size
        ox, oy = self.pos
        if w < 10 or h < 10:
            return

        with self.canvas:
            # Background
            Color(8 / 255, 14 / 255, 22 / 255, 1)
            Rectangle(pos=self.pos, size=self.size)

            # Grid
            Color(18 / 255, 30 / 255, 42 / 255, 0.6)
            cols = 8
            rows = 6
            for i in range(cols + 1):
                gx = ox + w * i / cols
                Line(points=[gx, oy, gx, oy + h], width=0.5)
            for i in range(rows + 1):
                gy = oy + h * i / rows
                Line(points=[ox, gy, ox + w, gy], width=0.5)

            # Connection path
            if len(self._connection_nodes) > 1:
                for i in range(len(self._connection_nodes) - 1):
                    ip1 = self._connection_nodes[i]
                    ip2 = self._connection_nodes[i + 1]
                    x1, y1 = _ip_to_pos(ip1)
                    x2, y2 = _ip_to_pos(ip2)
                    px1, py1 = ox + x1 * w, oy + y1 * h
                    px2, py2 = ox + x2 * w, oy + y2 * h

                    # Color based on trace progress
                    if self._trace_pct < 0.4:
                        Color(*SUCCESS)
                    elif self._trace_pct < 0.7:
                        Color(*WARNING)
                    else:
                        Color(*ALERT)
                    Line(points=[px1, py1, px2, py2], width=1.5)

                # Animated packet
                t = (self._packet_time * 0.5) % 1.0
                total = len(self._connection_nodes) - 1
                seg = int(t * total)
                frac = (t * total) - seg
                if seg < total:
                    ip1 = self._connection_nodes[seg]
                    ip2 = self._connection_nodes[seg + 1]
                    x1, y1 = _ip_to_pos(ip1)
                    x2, y2 = _ip_to_pos(ip2)
                    px = ox + (x1 + (x2 - x1) * frac) * w
                    py = oy + (y1 + (y2 - y1) * frac) * h
                    Color(*PRIMARY)
                    Ellipse(pos=(px - 4, py - 4), size=(8, 8))

            # Server nodes
            for link in self._links:
                ip = link.get("ip", "") if isinstance(link, dict) else str(link)
                name = link.get("name", "") if isinstance(link, dict) else ""
                x, y = _ip_to_pos(ip)
                px, py = ox + x * w, oy + y * h

                is_connected = ip in self._connection_nodes
                if is_connected:
                    # Pulsing ring
                    pulse = 0.5 + 0.5 * math.sin(time.time() * 3)
                    Color(*PRIMARY[:3], pulse * 0.3)
                    Ellipse(pos=(px - 14, py - 14), size=(28, 28))
                    Color(*PRIMARY[:3], pulse * 0.15)
                    Ellipse(pos=(px - 20, py - 20), size=(40, 40))

                # Diamond node shape (rotated square)
                color = PRIMARY if is_connected else SECONDARY
                sz = 7
                Color(*color)
                Line(points=[px, py + sz, px + sz, py, px, py - sz, px - sz, py, px, py + sz],
                     width=1.3)
                # Inner fill
                Color(*color[:3], 0.4)
                Ellipse(pos=(px - 3, py - 3), size=(6, 6))

                # Crosshair lines
                Color(*color[:3], 0.15)
                Line(points=[px - 18, py, px + 18, py], width=0.7)
                Line(points=[px, py - 18, px, py + 18], width=0.7)

            # Node labels
            for link in self._links:
                ip = link.get("ip", "") if isinstance(link, dict) else str(link)
                name = link.get("name", "") if isinstance(link, dict) else ""
                x, y = _ip_to_pos(ip)
                px, py = ox + x * w, oy + y * h

                is_connected = ip in self._connection_nodes
                label_text = name[:20] if name else ip
                label_color = TEXT_WHITE if is_connected else TEXT_DIM
                cl = CoreLabel(text=label_text, font_size=11,
                               color=(*label_color[:3], 0.9))
                cl.refresh()
                tex = cl.texture
                if tex:
                    Color(1, 1, 1, 1)
                    Rectangle(texture=tex,
                              pos=(px - tex.width / 2, py - 20),
                              size=tex.size)
                # IP label below name
                if name:
                    cl2 = CoreLabel(text=ip, font_size=9,
                                    color=(*TEXT_DIM[:3], 0.5))
                    cl2.refresh()
                    tex2 = cl2.texture
                    if tex2:
                        Color(1, 1, 1, 1)
                        Rectangle(texture=tex2,
                                  pos=(px - tex2.width / 2, py - 32),
                                  size=tex2.size)

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        if touch.button == 'right':
            return self._handle_right_click(touch)
        if touch.button == 'left':
            return self._handle_left_click(touch)
        return super().on_touch_down(touch)

    def _find_node_at(self, pos):
        """Find the link/IP closest to the given screen position."""
        w, h = self.size
        ox, oy = self.pos
        for link in self._links:
            ip = link.get("ip", "") if isinstance(link, dict) else str(link)
            x, y = _ip_to_pos(ip)
            px, py = ox + x * w, oy + y * h
            if abs(pos[0] - px) < 18 and abs(pos[1] - py) < 18:
                return ip, link
        return None, None

    def _handle_left_click(self, touch):
        """Click a server node to connect to it."""
        ip, link = self._find_node_at(touch.pos)
        if ip:
            app = App.get_running_app()
            if app._game and app._game._browser:
                # Switch to browser tab and connect
                if app._game.tabbar:
                    app._game.tabbar.switch_to(0)  # Browser tab
                app._game._browser.connect_to(ip)
            return True
        return False

    def _handle_right_click(self, touch):
        """Add clicked node to bounce route (TODO)."""
        ip, link = self._find_node_at(touch.pos)
        if ip:
            # TODO: add to bounce route
            return True
        return False
