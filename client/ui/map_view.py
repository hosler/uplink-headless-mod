"""Map tab: visual server map with clickable nodes and connection path."""
import hashlib
import pygame
from ui.theme import (Scale, get_font, PRIMARY, SECONDARY, TEXT_WHITE, TEXT_DIM,
                      PANEL_BG, ALERT, SUCCESS, TOPBAR_H, TAB_H, STATUSBAR_H,
                      DESIGN_W, DESIGN_H, BG_DARK)


# Map area in design coordinates
MAP_X = 40
MAP_Y = TOPBAR_H + TAB_H + 10
MAP_W = DESIGN_W - 80
MAP_H = DESIGN_H - TOPBAR_H - TAB_H - STATUSBAR_H - 30

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

    def on_activate(self):
        self.net.get_links()
        self.net.get_trace()

    def draw(self, surface, scale: Scale, state):
        links = state.links
        conn_nodes = state.connection.get("nodes", [])
        trace = state.trace

        # Map background
        map_rect = scale.rect(MAP_X, MAP_Y, MAP_W, MAP_H)
        pygame.draw.rect(surface, (8, 14, 22), map_rect, border_radius=4)
        pygame.draw.rect(surface, SECONDARY, map_rect, 1, border_radius=4)

        # Grid lines (subtle)
        grid_color = (15, 25, 35)
        for gx in range(10):
            x = map_rect.x + int(map_rect.w * gx / 10)
            pygame.draw.line(surface, grid_color, (x, map_rect.y), (x, map_rect.bottom))
        for gy in range(8):
            y = map_rect.y + int(map_rect.h * gy / 8)
            pygame.draw.line(surface, grid_color, (map_rect.x, y), (map_rect.right, y))

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

            # Arrows along path
            for i in range(len(points) - 1):
                mx = (points[i][0] + points[i + 1][0]) // 2
                my = (points[i][1] + points[i + 1][1]) // 2
                pygame.draw.circle(surface, PRIMARY, (mx, my), 3)

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

            # Glow effect for hovered
            if hovered:
                glow = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
                pygame.draw.circle(glow, (*PRIMARY, 40), (radius * 2, radius * 2), radius * 2)
                surface.blit(glow, (sx - radius * 2, sy - radius * 2))

            pygame.draw.circle(surface, color, (sx, sy), radius)

            # Label — always visible for readability
            display_name = name[:25] if len(name) > 25 else name
            if hovered or in_conn:
                label_color = TEXT_WHITE
            else:
                label_color = TEXT_DIM
            txt = font_small.render(display_name, True, label_color)
            surface.blit(txt, (sx + scale.w(14), sy - txt.get_height() // 2))

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
        font_leg = get_font(scale.fs(14), light=True)
        lx = scale.x(MAP_X + 10)
        ly = scale.y(MAP_Y + MAP_H - 30)
        txt = font_leg.render("Left-click: connect  Right-click: add bounce  |  ", True, TEXT_DIM)
        surface.blit(txt, (lx, ly))
        lx += txt.get_width()
        pygame.draw.circle(surface, SUCCESS, (lx + 5, ly + 8), 5)
        txt = font_leg.render("  Target  ", True, TEXT_DIM)
        surface.blit(txt, (lx + 12, ly))
        lx += txt.get_width() + 12
        pygame.draw.circle(surface, (43, 255, 209), (lx + 5, ly + 8), 5)
        txt = font_leg.render("  Bounce  ", True, TEXT_DIM)
        surface.blit(txt, (lx + 12, ly))
        lx += txt.get_width() + 12
        pygame.draw.circle(surface, PRIMARY, (lx + 5, ly + 8), 5)
        txt = font_leg.render("  Active  ", True, TEXT_DIM)
        surface.blit(txt, (lx + 12, ly))
        lx += txt.get_width() + 12
        pygame.draw.circle(surface, SECONDARY, (lx + 5, ly + 8), 4)
        txt = font_leg.render("  Known", True, TEXT_DIM)
        surface.blit(txt, (lx + 12, ly))

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
