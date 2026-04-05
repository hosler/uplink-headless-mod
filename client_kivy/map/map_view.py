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
        self.bounce_ips = []  # planned bounce route IPs
        self._clear_btn_x = -100
        self._clear_btn_w = 0

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

        # Reserve space for bottom bar
        bar_h = 28
        map_h = h - bar_h

        with self.canvas:
            # Background
            Color(8 / 255, 14 / 255, 22 / 255, 1)
            Rectangle(pos=self.pos, size=self.size)

            # Title
            title_cl = CoreLabel(text='W O R L D   M A P', font_size=18,
                                 color=(*PRIMARY[:3], 0.7))
            title_cl.refresh()
            ttex = title_cl.texture
            if ttex:
                Color(1, 1, 1, 1)
                Rectangle(texture=ttex,
                          pos=(ox + w / 2 - ttex.width / 2, oy + map_h + bar_h - ttex.height - 8),
                          size=ttex.size)

            # Grid
            Color(18 / 255, 30 / 255, 42 / 255, 0.6)
            cols = 8
            rows = 6
            for i in range(cols + 1):
                gx = ox + w * i / cols
                Line(points=[gx, oy + bar_h, gx, oy + bar_h + map_h], width=0.5)
            for i in range(rows + 1):
                gy = oy + bar_h + map_h * i / rows
                Line(points=[ox, gy, ox + w, gy], width=0.5)

            # Connection path
            if len(self._connection_nodes) > 1:
                for i in range(len(self._connection_nodes) - 1):
                    ip1 = self._connection_nodes[i]
                    ip2 = self._connection_nodes[i + 1]
                    x1, y1 = _ip_to_pos(ip1)
                    x2, y2 = _ip_to_pos(ip2)
                    px1, py1 = ox + x1 * w, oy + bar_h + y1 * map_h
                    px2, py2 = ox + x2 * w, oy + bar_h + y2 * map_h

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
                    py = oy + bar_h + (y1 + (y2 - y1) * frac) * map_h
                    Color(*PRIMARY)
                    Ellipse(pos=(px - 4, py - 4), size=(8, 8))

            # Planned bounce path (dashed green lines + numbered markers)
            if self.bounce_ips:
                bounce_pts = []
                for ip in self.bounce_ips:
                    bx, by = _ip_to_pos(ip)
                    bounce_pts.append((ox + bx * w, oy + bar_h + by * map_h))

                # Dashed lines between bounce hops
                for i in range(len(bounce_pts) - 1):
                    x1, y1 = bounce_pts[i]
                    x2, y2 = bounce_pts[i + 1]
                    dx, dy = x2 - x1, y2 - y1
                    length = max(1, (dx ** 2 + dy ** 2) ** 0.5)
                    # Draw dashes
                    Color(*SUCCESS)
                    d = 0
                    while d < length:
                        t1 = d / length
                        t2 = min(1.0, (d + 8) / length)
                        Line(points=[x1 + dx * t1, y1 + dy * t1,
                                     x1 + dx * t2, y1 + dy * t2], width=1.8)
                        d += 14

                # Numbered hop markers
                for i, (bx, by) in enumerate(bounce_pts):
                    Color(*SUCCESS[:3], 0.3)
                    Ellipse(pos=(bx - 12, by - 12), size=(24, 24))
                    Color(*SUCCESS)
                    Ellipse(pos=(bx - 9, by - 9), size=(18, 18))
                    # Number label
                    num_cl = CoreLabel(text=str(i + 1), font_size=12,
                                       color=(0, 0, 0, 1), bold=True)
                    num_cl.refresh()
                    ntex = num_cl.texture
                    if ntex:
                        Color(1, 1, 1, 1)
                        Rectangle(texture=ntex,
                                  pos=(bx - ntex.width / 2, by - ntex.height / 2),
                                  size=ntex.size)

            # Server nodes
            for link in self._links:
                ip = link.get("ip", "") if isinstance(link, dict) else str(link)
                name = link.get("name", "") if isinstance(link, dict) else ""
                x, y = _ip_to_pos(ip)
                px, py = ox + x * w, oy + bar_h + y * map_h

                is_connected = ip in self._connection_nodes
                in_bounce = ip in self.bounce_ips
                if is_connected:
                    # Pulsing ring
                    pulse = 0.5 + 0.5 * math.sin(time.time() * 3)
                    Color(*PRIMARY[:3], pulse * 0.3)
                    Ellipse(pos=(px - 14, py - 14), size=(28, 28))
                    Color(*PRIMARY[:3], pulse * 0.15)
                    Ellipse(pos=(px - 20, py - 20), size=(40, 40))

                # Diamond node shape (rotated square)
                if in_bounce:
                    color = SUCCESS
                elif is_connected:
                    color = PRIMARY
                else:
                    color = SECONDARY
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
                px, py = ox + x * w, oy + bar_h + y * map_h

                is_connected = ip in self._connection_nodes
                in_bounce = ip in self.bounce_ips
                label_text = name[:20] if name else ip

                if in_bounce:
                    label_color = (*SUCCESS[:3], 1.0)
                elif is_connected:
                    label_color = (0.9, 0.95, 1, 1)
                else:
                    label_color = (0.6, 0.75, 0.9, 1)

                # Dark background behind label for readability
                cl = CoreLabel(text=label_text, font_size=12, color=label_color)
                cl.refresh()
                tex = cl.texture
                if tex:
                    # Shadow/bg behind text
                    Color(0.02, 0.04, 0.08, 0.8)
                    Rectangle(pos=(px - tex.width / 2 - 3, py - 22),
                              size=(tex.width + 6, tex.height + 2))
                    Color(1, 1, 1, 1)
                    Rectangle(texture=tex,
                              pos=(px - tex.width / 2, py - 20),
                              size=tex.size)
                # IP label below name
                if name:
                    cl2 = CoreLabel(text=ip, font_size=10,
                                    color=(0.4, 0.55, 0.7, 0.8))
                    cl2.refresh()
                    tex2 = cl2.texture
                    if tex2:
                        Color(0.02, 0.04, 0.08, 0.7)
                        Rectangle(pos=(px - tex2.width / 2 - 2, py - 34),
                                  size=(tex2.width + 4, tex2.height + 2))
                        Color(1, 1, 1, 1)
                        Rectangle(texture=tex2,
                                  pos=(px - tex2.width / 2, py - 32),
                                  size=tex2.size)

            # Bottom bar
            Color(8 / 255, 14 / 255, 22 / 255, 0.9)
            Rectangle(pos=(ox, oy), size=(w, bar_h))
            Color(*SECONDARY[:3], 0.4)
            Line(points=[ox, oy + bar_h, ox + w, oy + bar_h], width=0.7)

            if self.bounce_ips:
                # Route display
                route_parts = [ip.split(".")[-1] for ip in self.bounce_ips]
                route_txt = " > ".join(route_parts) + " > [TARGET]"
                route_cl = CoreLabel(text=f"ROUTE: {route_txt}", font_size=12,
                                      color=(*SUCCESS[:3], 1.0))
                route_cl.refresh()
                rtex = route_cl.texture
                if rtex:
                    Color(1, 1, 1, 1)
                    Rectangle(texture=rtex,
                              pos=(ox + 8, oy + (bar_h - rtex.height) / 2),
                              size=rtex.size)

                # CLEAR button
                clr_cl = CoreLabel(text='[CLEAR]', font_size=12,
                                    color=(*ALERT[:3], 1.0))
                clr_cl.refresh()
                ctex = clr_cl.texture
                if ctex:
                    self._clear_btn_x = ox + w - ctex.width - 12
                    self._clear_btn_w = ctex.width + 8
                    Color(1, 1, 1, 1)
                    Rectangle(texture=ctex,
                              pos=(self._clear_btn_x, oy + (bar_h - ctex.height) / 2),
                              size=ctex.size)
            else:
                self._clear_btn_x = -100
                self._clear_btn_w = 0
                # Controls hint
                hint_cl = CoreLabel(text='LEFT CLICK: CONNECT    RIGHT CLICK: ADD BOUNCE',
                                     font_size=11, color=(*TEXT_DIM[:3], 0.7))
                hint_cl.refresh()
                htex = hint_cl.texture
                if htex:
                    Color(1, 1, 1, 1)
                    Rectangle(texture=htex,
                              pos=(ox + 8, oy + (bar_h - htex.height) / 2),
                              size=htex.size)

                # Server count
                cnt_cl = CoreLabel(text=f'{len(self._links)} SERVERS', font_size=11,
                                    color=(*TEXT_DIM[:3], 0.7))
                cnt_cl.refresh()
                cnt_tex = cnt_cl.texture
                if cnt_tex:
                    Color(1, 1, 1, 1)
                    Rectangle(texture=cnt_tex,
                              pos=(ox + w - cnt_tex.width - 8, oy + (bar_h - cnt_tex.height) / 2),
                              size=cnt_tex.size)

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        # Check CLEAR button click
        if touch.button == 'left' and self.bounce_ips:
            bar_h = 28
            if (touch.pos[1] < self.pos[1] + bar_h and
                    abs(touch.pos[0] - self._clear_btn_x - self._clear_btn_w / 2) < self._clear_btn_w / 2 + 4):
                self.bounce_ips = []
                self._redraw()
                return True
        if touch.button == 'right':
            return self._handle_right_click(touch)
        if touch.button == 'left':
            return self._handle_left_click(touch)
        return super().on_touch_down(touch)

    def _find_node_at(self, pos):
        """Find the link/IP closest to the given screen position."""
        w, h = self.size
        ox, oy = self.pos
        bar_h = 28
        map_h = h - bar_h
        for link in self._links:
            ip = link.get("ip", "") if isinstance(link, dict) else str(link)
            x, y = _ip_to_pos(ip)
            px, py = ox + x * w, oy + bar_h + y * map_h
            if abs(pos[0] - px) < 18 and abs(pos[1] - py) < 18:
                return ip, link
        return None, None

    def _handle_left_click(self, touch):
        """Click a server node: bounce-connect if route planned, else direct connect."""
        ip, link = self._find_node_at(touch.pos)
        if ip:
            app = App.get_running_app()
            if app._game and app._game._browser:
                if app._game.tabbar:
                    app._game.tabbar.switch_to(0)  # Browser tab
                if self.bounce_ips:
                    # Connect through bounce route
                    self.net.connect_bounce(ip, self.bounce_ips)
                    app._game._browser._mode = "connecting"
                    app._game._browser._connect_ip = ip
                    import time as _time
                    app._game._browser._connect_start = _time.time()
                    app._game._browser._show_connecting(ip)
                    self.bounce_ips = []
                else:
                    app._game._browser.connect_to(ip)
            return True
        return False

    def _handle_right_click(self, touch):
        """Toggle clicked node in bounce route."""
        ip, link = self._find_node_at(touch.pos)
        if ip:
            if ip in self.bounce_ips:
                self.bounce_ips.remove(ip)
            else:
                self.bounce_ips.append(ip)
            try:
                from audio import play_sfx
                play_sfx("popup")
            except Exception:
                pass
            self._redraw()
            return True
        return False
