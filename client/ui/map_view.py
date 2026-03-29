"""Map tab: visual server map with clickable nodes and connection path."""
import hashlib
import pygame
import time
from ui.theme import (Scale, get_font, PRIMARY, SECONDARY, TEXT_WHITE, TEXT_DIM,
                      PANEL_BG, ALERT, SUCCESS, TOPBAR_H, TAB_H, STATUSBAR_H,
                      DESIGN_W, DESIGN_H, BG_DARK)
from ui.widgets import HackerPanel

# Map area in design coordinates
MAP_X = 40
MAP_Y = TOPBAR_H + TAB_H + 40
MAP_W = DESIGN_W - 80
MAP_H = DESIGN_H - TOPBAR_H - TAB_H - STATUSBAR_H - 60

DOT_RADIUS = 8
HOVER_RADIUS = 14


def _ip_to_pos(ip: str) -> tuple[float, float]:
    """Deterministic position from IP string (0-1 range)."""
    h = hashlib.md5(ip.encode()).digest()
    x = (h[0] + h[1] * 256) / 65535.0
    y = (h[2] + h[3] * 256) / 65535.0
    # Keep away from edges
    x = 0.05 + x * 0.9
    y = 0.05 + y * 0.9
    return x, y


class MapView:
    def __init__(self, net):
        self.net = net
        self.hovered_link = None  # index into links
        self._tooltip = ""
        self._tooltip_pos = (0, 0)
        self.bounce_ips = []  # planned bounce route (list of IPs)
        self.panel = HackerPanel(MAP_X, MAP_Y, MAP_W, MAP_H, title="Global Server Topology")
        self._scanline_surf = None

    def on_activate(self):
        self.net.get_links()
        self.net.get_trace()

    def _draw_scanlines(self, surface, rect):
        if self._scanline_surf is None or self._scanline_surf.get_size() != (rect.w, rect.h):
            self._scanline_surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            for y in range(0, rect.h, 3):
                pygame.draw.line(self._scanline_surf, (0, 0, 0, 40), (0, y), (rect.w, y))
        surface.blit(self._scanline_surf, rect.topleft)

    def draw(self, surface, scale: Scale, state):
        links = state.links
        conn_nodes = state.connection.get("nodes", [])
        trace = state.trace

        # Panel
        self.panel.draw(surface, scale)
        map_rect = scale.rect(MAP_X, MAP_Y, MAP_W, MAP_H)

        # Grid lines (subtle)
        grid_color = (15, 25, 35)
        for gx in range(10):
            x = map_rect.x + int(map_rect.w * gx / 10)
            pygame.draw.line(surface, grid_color, (x, map_rect.y), (x, map_rect.bottom))
        for gy in range(8):
            y = map_rect.y + int(map_rect.h * gy / 8)
            pygame.draw.line(surface, grid_color, (map_rect.x, y), (map_rect.right, y))

        # Scanlines
        self._draw_scanlines(surface, map_rect)

        # Connection path lines
        if len(conn_nodes) >= 2:
            points = []
            for ip in conn_nodes:
                px, py = _ip_to_pos(ip)
                sx = map_rect.x + int(px * map_rect.w)
                sy = map_rect.y + int(py * map_rect.h)
                points.append((sx, sy))

            # Draw bounce path
            trace_progress = trace.get("progress", 0) if trace.get("active") else 0
            for i in range(len(points) - 1):
                # Color: traced hops in red, safe hops in blue
                hop_idx = len(points) - 1 - i  # trace goes backwards
                if trace.get("active") and hop_idx <= trace_progress:
                    color = ALERT
                    width = 3
                else:
                    color = PRIMARY
                    width = 2
                pygame.draw.line(surface, color, points[i], points[i + 1], width)

            # Data packets (moving dots)
            t = (time.time() * 1.5) % 1.0
            for i in range(len(points) - 1):
                p1 = points[i]
                p2 = points[i+1]
                # Multiple packets per segment
                for offset in [0, 0.33, 0.66]:
                    pt = (t + offset) % 1.0
                    px = p1[0] + (p2[0] - p1[0]) * pt
                    py = p1[1] + (p2[1] - p1[1]) * pt
                    pygame.draw.circle(surface, PRIMARY, (int(px), int(py)), 3)
                    # Glow for packet
                    ps = pygame.Surface((12, 12), pygame.SRCALPHA)
                    pygame.draw.circle(ps, (*PRIMARY, 80), (6, 6), 6)
                    surface.blit(ps, (int(px)-6, int(py)-6))

        # Planned bounce path (dashed cyan lines)
        if self.bounce_ips:
            bounce_points = []
            for ip in self.bounce_ips:
                px, py = _ip_to_pos(ip)
                sx = map_rect.x + int(px * map_rect.w)
                sy = map_rect.y + int(py * map_rect.h)
                bounce_points.append((sx, sy))
            for i in range(len(bounce_points) - 1):
                # Dashed line effect
                x1, y1 = bounce_points[i]
                x2, y2 = bounce_points[i + 1]
                dx = x2 - x1
                dy = y2 - y1
                length = max(1, int((dx**2 + dy**2) ** 0.5))
                dash_len = 8
                for d in range(0, length, dash_len * 2):
                    t1 = d / length
                    t2 = min(1.0, (d + dash_len) / length)
                    p1 = (int(x1 + dx * t1), int(y1 + dy * t1))
                    p2 = (int(x1 + dx * t2), int(y1 + dy * t2))
                    pygame.draw.line(surface, (43, 255, 209), p1, p2, 2)
            # Number labels on bounce nodes
            font_num = get_font(scale.fs(12))
            for i, (bx, by) in enumerate(bounce_points):
                txt = font_num.render(str(i + 1), True, (0, 0, 0))
                pygame.draw.circle(surface, (43, 255, 209), (bx, by), scale.w(10))
                surface.blit(txt, (bx - txt.get_width() // 2, by - txt.get_height() // 2))

        # Server dots
        font_small = get_font(scale.fs(13), light=True)
        mouse_pos = pygame.mouse.get_pos()
        self.hovered_link = None
        self._tooltip = ""

        for i, link in enumerate(links):
            ip = link.get("ip", "")
            name = link.get("name", "")
            px, py = _ip_to_pos(ip)
            sx = map_rect.x + int(px * map_rect.w)
            sy = map_rect.y + int(py * map_rect.h)

            # Check if in connection
            in_conn = ip in conn_nodes
            is_target = conn_nodes and ip == conn_nodes[-1]

            # Check hover
            dist = ((mouse_pos[0] - sx) ** 2 + (mouse_pos[1] - sy) ** 2) ** 0.5
            hovered = dist < scale.w(20)
            if hovered:
                self.hovered_link = i
                self._tooltip = f"{name}\n{ip}"
                self._tooltip_pos = (sx + 15, sy - 10)

            # Dot color
            in_bounce = ip in self.bounce_ips
            if is_target:
                color = SUCCESS
                radius = scale.w(DOT_RADIUS + 3)
            elif in_bounce:
                color = (43, 255, 209)  # teal for bounce nodes
                radius = scale.w(DOT_RADIUS + 2)
            elif in_conn:
                color = PRIMARY
                radius = scale.w(DOT_RADIUS + 1)
            elif hovered:
                color = TEXT_WHITE
                radius = scale.w(HOVER_RADIUS)
            else:
                color = SECONDARY
                radius = scale.w(DOT_RADIUS)

            # Glow effect for active/target/hovered/bounce
            if hovered or is_target or in_conn or in_bounce:
                glow_radius = int(radius * 2.5)
                glow = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
                alpha = 70 if is_target else (45 if (in_conn or in_bounce) else 30)
                pygame.draw.circle(glow, (*color, alpha), (glow_radius, glow_radius), glow_radius)
                surface.blit(glow, (sx - glow_radius, sy - glow_radius))

            pygame.draw.circle(surface, color, (sx, sy), radius)

            # Label — always visible for readability
            display_name = name[:25] if len(name) > 25 else name
            if hovered or in_conn:
                label_color = TEXT_WHITE
            else:
                label_color = TEXT_DIM
            txt = font_small.render(display_name, True, label_color)
            
            # Label background for better contrast
            tr = txt.get_rect(topleft=(sx + scale.w(14), sy - txt.get_height() // 2))
            bg_surf = pygame.Surface((tr.w + 4, tr.h), pygame.SRCALPHA)
            bg_surf.fill((10, 20, 30, 180))
            surface.blit(bg_surf, (tr.x - 2, tr.y))
            
            surface.blit(txt, tr.topleft)

        # Tooltip
        if self._tooltip:
            font_tip = get_font(scale.fs(14))
            lines = self._tooltip.split("\n")
            ty = self._tooltip_pos[1]
            max_tw = 0
            rendered = []
            for line in lines:
                txt = font_tip.render(line, True, TEXT_WHITE)
                rendered.append(txt)
                max_tw = max(max_tw, txt.get_width())

            # Background
            tip_rect = pygame.Rect(self._tooltip_pos[0] - 4, ty - 2,
                                   max_tw + 12, len(rendered) * 18 + 6)
            tip_bg = pygame.Surface((tip_rect.w, tip_rect.h), pygame.SRCALPHA)
            tip_bg.fill((11, 21, 32, 220))
            surface.blit(tip_bg, tip_rect.topleft)
            pygame.draw.rect(surface, SECONDARY, tip_rect, 1)

            for txt in rendered:
                surface.blit(txt, (self._tooltip_pos[0], ty))
                ty += 18

        # Legend
        font_leg = get_font(scale.fs(15), light=True)
        lx = scale.x(MAP_X + 20)
        ly = scale.y(MAP_Y + MAP_H - 40)
        
        # Background for legend (translucent with hacker frame)
        leg_rect = scale.rect(MAP_X + 10, MAP_Y + MAP_H - 50, 700, 40)
        leg_bg = pygame.Surface((leg_rect.w, leg_rect.h), pygame.SRCALPHA)
        leg_bg.fill((10, 20, 30, 220))
        surface.blit(leg_bg, leg_rect.topleft)
        pygame.draw.rect(surface, (*SECONDARY, 150), leg_rect, 1)
        # Corner accents for legend
        pygame.draw.line(surface, SECONDARY, (leg_rect.x, leg_rect.y), (leg_rect.x+10, leg_rect.y), 2)
        pygame.draw.line(surface, SECONDARY, (leg_rect.x, leg_rect.y), (leg_rect.x, leg_rect.y+10), 2)

        txt = font_leg.render("MOUSE: LEFT CONNECT, RIGHT BOUNCE |", True, TEXT_DIM)
        surface.blit(txt, (lx, ly + 4))
        lx += txt.get_width() + 10
        
        # Legend items
        items = [
            (SUCCESS, "TARGET"),
            ((43, 255, 209), "BOUNCE"),
            (PRIMARY, "ACTIVE"),
            (SECONDARY, "KNOWN")
        ]
        for color, label in items:
            pygame.draw.circle(surface, color, (lx + scale.w(8), ly + scale.h(12)), scale.w(5))
            # Glow for legend dots
            glow = pygame.Surface((scale.w(16), scale.w(16)), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*color, 100), (scale.w(8), scale.w(8)), scale.w(8))
            surface.blit(glow, (lx, ly + scale.h(4)))
            
            txt = font_leg.render(label, True, TEXT_WHITE)
            surface.blit(txt, (lx + scale.w(20), ly + scale.h(4)))
            lx += txt.get_width() + scale.w(35)

        # Bounce route status
        if self.bounce_ips:
            font_bounce = get_font(scale.fs(14))
            route_txt = " > ".join(self.bounce_ips) + " > [target]"
            txt = font_bounce.render(f"Route: {route_txt}", True, (43, 255, 209))
            surface.blit(txt, (scale.x(MAP_X + 10), scale.y(MAP_Y + MAP_H - 55)))

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
            # Left-click: connect (with bounce route if set)
            if self.bounce_ips:
                self.net.connect_bounce(ip, self.bounce_ips)
                audio.play_sfx("bounce")
                self.bounce_ips = []  # clear after connecting
            else:
                self.net.server_connect(ip)
                audio.play_sfx("bounce")
            return True

        elif event.button == 3:
            # Right-click: toggle server in bounce list
            if ip in self.bounce_ips:
                self.bounce_ips.remove(ip)
                audio.play_sfx("popup")
            else:
                self.bounce_ips.append(ip)
                audio.play_sfx("popup")
            return True

        return False
