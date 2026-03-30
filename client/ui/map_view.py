"""Map tab: visual server map with clickable nodes and connection path."""
import hashlib
import math
import pygame
import time
from ui.theme import (Scale, get_font, PRIMARY, SECONDARY, TEXT_WHITE, TEXT_DIM,
                      PANEL_BG, ALERT, SUCCESS, TOPBAR_H, TAB_H, STATUSBAR_H,
                      DESIGN_W, DESIGN_H, BG_DARK, draw_scanlines)

# Map area in design coordinates
MAP_X = 20
MAP_Y = TOPBAR_H + TAB_H + 10
MAP_W = DESIGN_W - 40
MAP_H = DESIGN_H - TOPBAR_H - TAB_H - STATUSBAR_H - 30

DOT_RADIUS = 6
HOVER_RADIUS = 10


def _ip_to_pos(ip: str) -> tuple[float, float]:
    """Deterministic position from IP string (0-1 range)."""
    h = hashlib.md5(ip.encode()).digest()
    x = (h[0] + h[1] * 256) / 65535.0
    y = (h[2] + h[3] * 256) / 65535.0
    # Keep away from edges
    x = 0.06 + x * 0.88
    y = 0.08 + y * 0.84
    return x, y


class MapView:
    def __init__(self, net):
        self.net = net
        self.hovered_link = None
        self._tooltip = ""
        self._tooltip_pos = (0, 0)
        self.bounce_ips = []
        self._bg_cache = None
        self._bg_size = (0, 0)

    def on_activate(self):
        self.net.get_links()
        self.net.get_trace()

    def _draw_map_bg(self, surface, rect):
        """Draw the map background with grid and atmosphere."""
        if self._bg_cache is None or self._bg_size != (rect.w, rect.h):
            self._bg_cache = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            bg = self._bg_cache

            # Dark background
            bg.fill((8, 14, 22))

            # Subtle radial gradient (brighter center)
            cx, cy = rect.w // 2, rect.h // 2
            max_r = max(rect.w, rect.h) // 2
            for r in range(max_r, 0, -20):
                alpha = int(12 * (1 - r / max_r))
                if alpha > 0:
                    pygame.draw.circle(bg, (20, 40, 60, alpha), (cx, cy), r)

            # Grid lines
            grid_color = (18, 30, 42)
            grid_fine = (14, 24, 34)
            # Major grid
            for gx in range(0, rect.w, rect.w // 8):
                pygame.draw.line(bg, grid_color, (gx, 0), (gx, rect.h))
            for gy in range(0, rect.h, rect.h // 6):
                pygame.draw.line(bg, grid_color, (0, gy), (rect.w, gy))
            # Fine grid
            for gx in range(0, rect.w, rect.w // 24):
                pygame.draw.line(bg, grid_fine, (gx, 0), (gx, rect.h))
            for gy in range(0, rect.h, rect.h // 18):
                pygame.draw.line(bg, grid_fine, (0, gy), (rect.w, gy))

            # Horizontal "latitude" lines with slight curve feel
            for i in range(5):
                y = int(rect.h * (0.15 + i * 0.175))
                pygame.draw.line(bg, (20, 35, 50), (0, y), (rect.w, y), 1)

            # Scanline overlay
            for y in range(0, rect.h, 3):
                pygame.draw.line(bg, (0, 0, 0, 12), (0, y), (rect.w, y))

            self._bg_size = (rect.w, rect.h)

        surface.blit(self._bg_cache, rect.topleft)

    def draw(self, surface, scale: Scale, state):
        links = state.links
        conn_nodes = state.connection.get("nodes", [])
        trace = state.trace

        map_rect = scale.rect(MAP_X, MAP_Y, MAP_W, MAP_H)

        # Map background
        self._draw_map_bg(surface, map_rect)

        # Border
        pygame.draw.rect(surface, (*SECONDARY, 100), map_rect, 1)

        # Title overlay (top-left)
        f_title = get_font(scale.fs(12))
        title_txt = f_title.render("GLOBAL SERVER TOPOLOGY", True, (*SECONDARY, 180))
        surface.blit(title_txt, (map_rect.x + 8, map_rect.y + 4))

        # Connection path lines
        if len(conn_nodes) >= 2:
            points = []
            for ip in conn_nodes:
                px, py = _ip_to_pos(ip)
                sx = map_rect.x + int(px * map_rect.w)
                sy = map_rect.y + int(py * map_rect.h)
                points.append((sx, sy))

            trace_progress = trace.get("progress", 0) if trace.get("active") else 0
            for i in range(len(points) - 1):
                hop_idx = len(points) - 1 - i
                if trace.get("active") and hop_idx <= trace_progress:
                    color = ALERT
                    width = 3
                else:
                    color = PRIMARY
                    width = 2
                pygame.draw.line(surface, color, points[i], points[i + 1], width)
                # Glow along path
                glow = pygame.Surface((abs(points[i+1][0]-points[i][0])+20, abs(points[i+1][1]-points[i][1])+20), pygame.SRCALPHA)
                # Skip glow for simplicity — just the line is enough

            # Data packets
            t = (time.time() * 1.2) % 1.0
            for i in range(len(points) - 1):
                p1, p2 = points[i], points[i + 1]
                for offset in [0, 0.5]:
                    pt = (t + offset) % 1.0
                    px = p1[0] + (p2[0] - p1[0]) * pt
                    py = p1[1] + (p2[1] - p1[1]) * pt
                    pygame.draw.circle(surface, PRIMARY, (int(px), int(py)), 2)

        # Planned bounce path (dashed teal)
        if self.bounce_ips:
            bounce_pts = []
            for ip in self.bounce_ips:
                px, py = _ip_to_pos(ip)
                bounce_pts.append((map_rect.x + int(px * map_rect.w),
                                   map_rect.y + int(py * map_rect.h)))
            for i in range(len(bounce_pts) - 1):
                x1, y1 = bounce_pts[i]
                x2, y2 = bounce_pts[i + 1]
                dx, dy = x2 - x1, y2 - y1
                length = max(1, int((dx**2 + dy**2) ** 0.5))
                for d in range(0, length, 12):
                    t1 = d / length
                    t2 = min(1.0, (d + 6) / length)
                    p1 = (int(x1 + dx * t1), int(y1 + dy * t1))
                    p2 = (int(x1 + dx * t2), int(y1 + dy * t2))
                    pygame.draw.line(surface, SUCCESS, p1, p2, 2)
            # Numbered markers
            f_num = get_font(scale.fs(11))
            for i, (bx, by) in enumerate(bounce_pts):
                pygame.draw.circle(surface, SUCCESS, (bx, by), scale.w(9))
                txt = f_num.render(str(i + 1), True, (0, 0, 0))
                surface.blit(txt, (bx - txt.get_width() // 2, by - txt.get_height() // 2))

        # Server nodes
        f_label = get_font(scale.fs(12), light=True)
        f_label_bold = get_font(scale.fs(13))
        mouse_pos = pygame.mouse.get_pos()
        self.hovered_link = None
        self._tooltip = ""

        for i, link in enumerate(links):
            ip = link.get("ip", "")
            name = link.get("name", "")
            px, py = _ip_to_pos(ip)
            sx = map_rect.x + int(px * map_rect.w)
            sy = map_rect.y + int(py * map_rect.h)

            in_conn = ip in conn_nodes
            is_target = conn_nodes and ip == conn_nodes[-1]
            in_bounce = ip in self.bounce_ips

            dist = ((mouse_pos[0] - sx) ** 2 + (mouse_pos[1] - sy) ** 2) ** 0.5
            hovered = dist < scale.w(18)
            if hovered:
                self.hovered_link = i
                self._tooltip = f"{name}\n{ip}"
                self._tooltip_pos = (sx + 12, sy - 8)

            # Node appearance
            if is_target:
                color = SUCCESS
                radius = scale.w(DOT_RADIUS + 4)
                glow_alpha = 80
            elif in_bounce:
                color = SUCCESS
                radius = scale.w(DOT_RADIUS + 3)
                glow_alpha = 60
            elif in_conn:
                color = PRIMARY
                radius = scale.w(DOT_RADIUS + 2)
                glow_alpha = 50
            elif hovered:
                color = TEXT_WHITE
                radius = scale.w(HOVER_RADIUS)
                glow_alpha = 40
            else:
                color = SECONDARY
                radius = scale.w(DOT_RADIUS)
                glow_alpha = 0

            # Glow
            if glow_alpha > 0:
                gr = int(radius * 3)
                glow = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow, (*color, glow_alpha), (gr, gr), gr)
                surface.blit(glow, (sx - gr, sy - gr))

            # Pulsing ring for target
            if is_target:
                pulse = (math.sin(time.time() * 4) + 1) / 2
                ring_r = int(radius + scale.w(4) + scale.w(3) * pulse)
                pygame.draw.circle(surface, (*SUCCESS, int(120 + 80 * pulse)), (sx, sy), ring_r, 2)

            # Draw node
            pygame.draw.circle(surface, color, (sx, sy), radius)
            # Inner highlight
            if radius > scale.w(4):
                pygame.draw.circle(surface, (*TEXT_WHITE, 60), (sx - 1, sy - 1), max(1, radius // 3))

            # Label
            display_name = name[:22] if len(name) > 22 else name
            if is_target or hovered or in_conn:
                label_font = f_label_bold
                label_color = TEXT_WHITE
            else:
                label_font = f_label
                label_color = (*TEXT_DIM, 200)

            txt = label_font.render(display_name, True, label_color)
            lx = sx + scale.w(12)
            ly = sy - txt.get_height() // 2

            # Keep label on screen
            if lx + txt.get_width() > map_rect.right - 5:
                lx = sx - scale.w(12) - txt.get_width()

            # Label background
            bg = pygame.Surface((txt.get_width() + 6, txt.get_height() + 2), pygame.SRCALPHA)
            bg.fill((8, 14, 22, 180))
            surface.blit(bg, (lx - 3, ly - 1))
            surface.blit(txt, (lx, ly))

        # Tooltip
        if self._tooltip:
            f_tip = get_font(scale.fs(14))
            f_tip_sm = get_font(scale.fs(12), light=True)
            lines = self._tooltip.split("\n")
            tx, ty = self._tooltip_pos

            # Calculate size
            w = max(f_tip.size(lines[0])[0], f_tip_sm.size(lines[1])[0] if len(lines) > 1 else 0) + 16
            h = 38

            # Background
            tip_rect = pygame.Rect(tx - 2, ty - 2, w, h)
            if tip_rect.right > map_rect.right:
                tip_rect.x = tx - w - 20
            bg = pygame.Surface((tip_rect.w, tip_rect.h), pygame.SRCALPHA)
            bg.fill((11, 21, 32, 240))
            surface.blit(bg, tip_rect.topleft)
            pygame.draw.rect(surface, PRIMARY, tip_rect, 1)

            txt = f_tip.render(lines[0], True, TEXT_WHITE)
            surface.blit(txt, (tip_rect.x + 6, tip_rect.y + 2))
            if len(lines) > 1:
                txt = f_tip_sm.render(lines[1], True, SECONDARY)
                surface.blit(txt, (tip_rect.x + 6, tip_rect.y + 20))

        # Bottom bar: legend + controls
        bar_y = map_rect.bottom - scale.h(28)
        bar_rect = pygame.Rect(map_rect.x, bar_y, map_rect.w, scale.h(28))
        bg = pygame.Surface((bar_rect.w, bar_rect.h), pygame.SRCALPHA)
        bg.fill((8, 14, 22, 220))
        surface.blit(bg, bar_rect.topleft)
        pygame.draw.line(surface, (*SECONDARY, 100), (bar_rect.x, bar_rect.y),
                         (bar_rect.right, bar_rect.y), 1)

        f_leg = get_font(scale.fs(12), light=True)
        lx = bar_rect.x + 8

        # Controls hint
        txt = f_leg.render("LEFT: CONNECT  RIGHT: BOUNCE", True, TEXT_DIM)
        surface.blit(txt, (lx, bar_rect.y + 6))
        lx += txt.get_width() + 20

        # Separator
        pygame.draw.line(surface, (*SECONDARY, 80), (lx, bar_rect.y + 4), (lx, bar_rect.bottom - 4), 1)
        lx += 12

        # Legend items
        items = [(SUCCESS, "TARGET"), ((43, 255, 209), "BOUNCE"),
                 (PRIMARY, "ACTIVE"), (SECONDARY, "KNOWN")]
        for color, label in items:
            pygame.draw.circle(surface, color, (lx + 4, bar_rect.y + 14), 4)
            txt = f_leg.render(label, True, color)
            surface.blit(txt, (lx + 14, bar_rect.y + 6))
            lx += txt.get_width() + 28

        # Server count
        txt = f_leg.render(f"{len(links)} SERVERS", True, TEXT_DIM)
        surface.blit(txt, (bar_rect.right - txt.get_width() - 8, bar_rect.y + 6))

        # Bounce route status
        if self.bounce_ips:
            f_route = get_font(scale.fs(13))
            route_txt = " → ".join([ip.split(".")[-1] for ip in self.bounce_ips]) + " → [target]"
            txt = f_route.render(f"ROUTE: {route_txt}", True, SUCCESS)
            surface.blit(txt, (map_rect.x + 8, bar_y - scale.h(22)))

    def handle_event(self, event, scale: Scale, state):
        import audio
        if event.type != pygame.MOUSEBUTTONDOWN:
            return False
        if self.hovered_link is None:
            return False

        links = state.links
        if not (0 <= self.hovered_link < len(links)):
            return False

        ip = links[self.hovered_link]["ip"]

        if event.button == 1:
            if self.bounce_ips:
                self.net.connect_bounce(ip, self.bounce_ips)
                audio.play_sfx("bounce")
                self.bounce_ips = []
            else:
                self.net.server_connect(ip)
                audio.play_sfx("bounce")
            return True

        elif event.button == 3:
            if ip in self.bounce_ips:
                self.bounce_ips.remove(ip)
                audio.play_sfx("popup")
            else:
                self.bounce_ips.append(ip)
                audio.play_sfx("popup")
            return True

        return False
