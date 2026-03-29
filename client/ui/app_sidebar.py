"""App Sidebar: running software tools during hacking sessions."""
import time
import pygame
from ui.theme import (Scale, get_font, PRIMARY, SECONDARY, ALERT, SUCCESS,
                      TEXT_WHITE, TEXT_DIM, PANEL_BG, TOPBAR_H, TAB_H,
                      STATUSBAR_H, DESIGN_W, DESIGN_H)
import audio

# Sidebar layout
SIDEBAR_X = 10
SIDEBAR_Y = TOPBAR_H + TAB_H + 20
SIDEBAR_W = 180
SLOT_H = 52

# Known software tools and their properties
TOOLS = {
    "Password_Breaker": {"icon": "PB", "color": ALERT, "auto": True, "target": "password"},
    "Log_Deleter": {"icon": "LD", "color": (180, 140, 255), "auto": False, "target": "log"},
    "File_Copier": {"icon": "FC", "color": SUCCESS, "auto": False, "target": "file"},
    "Decrypter": {"icon": "DC", "color": (255, 200, 50), "auto": True, "target": "file"},
    "Trace_Tracker": {"icon": "TT", "color": PRIMARY, "auto": True, "target": None},
    "Firewall_Bypass": {"icon": "FB", "color": (255, 100, 50), "auto": True, "target": None},
    "Dictionary_Hacker": {"icon": "DH", "color": ALERT, "auto": True, "target": "password"},
    "Proxy_Bypass": {"icon": "PX", "color": (100, 200, 100), "auto": True, "target": None},
    "Defrag": {"icon": "DF", "color": TEXT_DIM, "auto": True, "target": None},
    "Monitor": {"icon": "MN", "color": SECONDARY, "auto": True, "target": None},
    "HUD_ConnectionAnalysis": {"icon": "CA", "color": PRIMARY, "auto": True, "target": None},
    "Voice_Analyser": {"icon": "VA", "color": (43, 255, 209), "auto": True, "target": None},
    "IP_Probe": {"icon": "IP", "color": PRIMARY, "auto": True, "target": None},
    "IP_Lookup": {"icon": "IL", "color": PRIMARY, "auto": True, "target": None},
    "LAN_Scan": {"icon": "LS", "color": PRIMARY, "auto": True, "target": None},
    "LAN_Probe": {"icon": "LP", "color": PRIMARY, "auto": True, "target": None},
    "LAN_Spoof": {"icon": "LS", "color": (255, 100, 50), "auto": True, "target": None},
    "LAN_Force": {"icon": "LF", "color": ALERT, "auto": True, "target": None},
}


class RunningApp:
    """A software tool currently running."""
    def __init__(self, title, version, tool_info):
        self.title = title
        self.version = version
        self.tool_info = tool_info
        self.start_time = time.time()
        self.progress = 0.0
        self.duration = 0.0  # 0 = instant/persistent
        self.active = True
        self.waiting_target = False  # True if tool needs user to click a target

    @property
    def icon(self):
        return self.tool_info.get("icon", "??")

    @property
    def color(self):
        return self.tool_info.get("color", SECONDARY)


class AppSidebar:
    """Sidebar showing available and running software tools."""
    def __init__(self, net, statusbar):
        self.net = net
        self.statusbar = statusbar
        self.running = []  # list of RunningApp
        self.visible = False  # only show when connected to a server
        self._scroll = 0
        self.on_tool_run = None  # callback(tool_name) from browser

    def get_available_tools(self, gateway_files):
        """Return list of (title, version, tool_info) for software on gateway."""
        tools = []
        seen = set()
        for f in gateway_files:
            title = f.get("title", "")
            # Match against known tools (handle underscores and spaces)
            for tool_name, tool_info in TOOLS.items():
                # Match by prefix (e.g. "Password_Breaker" matches "Password_Breaker v1.0")
                if title.startswith(tool_name) or title.replace(" ", "_").startswith(tool_name):
                    key = tool_name
                    if key not in seen:
                        seen.add(key)
                        # Extract version from title or default
                        version = 1.0
                        tools.append((tool_name, version, tool_info))
                    break
        return tools

    def is_running(self, tool_name):
        return any(a.title == tool_name and a.active for a in self.running)

    def get_running(self, tool_name):
        for a in self.running:
            if a.title == tool_name and a.active:
                return a
        return None

    def run_tool(self, title, version, tool_info):
        """Start running a software tool."""
        # Don't double-run
        if self.is_running(title):
            self.statusbar.show(f"{title} already running")
            return None

        app = RunningApp(title, version, tool_info)

        if tool_info.get("target") and not tool_info.get("auto"):
            # Tool needs user to click a target
            app.waiting_target = True
            self.statusbar.show(f"{title}: click a target")
        else:
            self.statusbar.show(f"{title} running")

        # Notify browser of tool launch
        if self.on_tool_run:
            self.on_tool_run(title)

        self.running.append(app)
        audio.play_sfx("popup")
        return app

    def stop_tool(self, title):
        for app in self.running:
            if app.title == title:
                app.active = False
                self.running.remove(app)
                return

    def clear_all(self):
        self.running.clear()

    def draw(self, surface, scale, state):
        if not self.visible:
            return

        gateway_files = state.gateway_files
        tools = self.get_available_tools(gateway_files)
        if not tools and not self.running:
            return

        mouse = pygame.mouse.get_pos()
        f_title = get_font(scale.fs(11))
        f_icon = get_font(scale.fs(16))
        f_status = get_font(scale.fs(10), light=True)

        # Sidebar panel
        n_slots = max(len(tools), len(self.running) + 1)
        sidebar_h = min(n_slots * SLOT_H + 35, 650)
        from ui.widgets import HackerPanel
        HackerPanel(SIDEBAR_X, SIDEBAR_Y, SIDEBAR_W, sidebar_h, title="Software").draw(surface, scale)
        
        sidebar_rect = scale.rect(SIDEBAR_X, SIDEBAR_Y, SIDEBAR_W, sidebar_h)
        sy = sidebar_rect.y + scale.h(4) # HackerPanel handles title height

        # Running apps first
        for app in self.running:
            if not app.active:
                continue
            
            # Use absolute scaled coordinates for the slot
            slot_rect = pygame.Rect(scale.x(SIDEBAR_X + 4), sy, scale.w(SIDEBAR_W - 8), scale.h(SLOT_H - 4))
            hovered = slot_rect.collidepoint(mouse)

            # Background & Glow
            slot_bg = pygame.Surface((slot_rect.w, slot_rect.h), pygame.SRCALPHA)
            slot_bg.fill((*app.color, 40 if hovered else 25))
            surface.blit(slot_bg, slot_rect.topleft)
            pygame.draw.rect(surface, app.color, slot_rect, 1)

            # Active diamond (pulsing)
            pulse = (time.time() * 3) % 1.0
            dot_x = slot_rect.x + scale.w(14)
            dot_y = slot_rect.y + scale.h(14)
            ds = scale.w(6)
            pts = [(dot_x, dot_y - ds), (dot_x + ds, dot_y), (dot_x, dot_y + ds), (dot_x - ds, dot_y)]
            pygame.draw.polygon(surface, app.color, pts)
            if pulse < 0.5:
                pygame.draw.polygon(surface, TEXT_WHITE, pts, 1)

            # Icon text
            txt = f_icon.render(app.icon, True, TEXT_WHITE if hovered else app.color)
            surface.blit(txt, (slot_rect.x + scale.w(28), slot_rect.y + scale.h(4)))

            # Title
            txt = f_title.render(app.title[:16].upper(), True, TEXT_WHITE)
            surface.blit(txt, (slot_rect.x + scale.w(58), slot_rect.y + scale.h(4)))

            # Status
            if app.waiting_target:
                txt = f_status.render("WAITING TARGET", True, app.color)
            elif app.duration > 0:
                elapsed = time.time() - app.start_time
                app.progress = min(1.0, elapsed / app.duration)
                pct = int(app.progress * 100)
                txt = f_status.render(f"RUNNING {pct}%", True, app.color)
                # Progress bar
                bar_y = slot_rect.y + slot_rect.h - scale.h(6)
                bar_w = slot_rect.w - scale.w(12)
                pygame.draw.rect(surface, (20, 35, 50), (slot_rect.x + scale.w(6), bar_y, bar_w, scale.h(4)))
                pygame.draw.rect(surface, app.color, (slot_rect.x + scale.w(6), bar_y, int(bar_w * app.progress), scale.h(4)))
            else:
                txt = f_status.render("ACTIVE", True, SUCCESS)
            surface.blit(txt, (slot_rect.x + scale.w(58), slot_rect.y + scale.h(18)))

            # Stop button (X)
            if hovered:
                stop_rect = pygame.Rect(slot_rect.right - scale.w(18), slot_rect.y + scale.h(4), scale.w(14), scale.h(14))
                pygame.draw.rect(surface, ALERT, stop_rect, 1)
                txt = f_status.render("X", True, ALERT)
                surface.blit(txt, (stop_rect.x + scale.w(3), stop_rect.y + scale.h(1)))

            sy += scale.h(SLOT_H)

        # Separator
        if self.running:
            pygame.draw.line(surface, (*SECONDARY, 100), (sidebar_rect.x + 8, sy + 2), (sidebar_rect.right - 8, sy + 2), 1)
            sy += scale.h(8)

        # Available (not running) tools
        for title, version, tool_info in tools:
            if self.is_running(title):
                continue
            if sy + scale.h(SLOT_H) > sidebar_rect.bottom:
                break

            slot_rect = pygame.Rect(scale.x(SIDEBAR_X + 4), sy, scale.w(SIDEBAR_W - 8), scale.h(SLOT_H - 4))
            hovered = slot_rect.collidepoint(mouse)

            if hovered:
                slot_bg = pygame.Surface((slot_rect.w, slot_rect.h), pygame.SRCALPHA)
                slot_bg.fill((*PRIMARY, 30))
                surface.blit(slot_bg, slot_rect.topleft)
                pygame.draw.rect(surface, (*PRIMARY, 100), slot_rect, 1)
            else:
                pygame.draw.rect(surface, (*SECONDARY, 60), slot_rect, 1)

            color = tool_info.get("color", SECONDARY)
            # Icon
            txt = f_icon.render(tool_info.get("icon", "??"), True, color if hovered else TEXT_DIM)
            surface.blit(txt, (slot_rect.x + scale.w(28), slot_rect.y + scale.h(4)))

            # Title
            txt = f_title.render(title[:16].upper(), True, TEXT_WHITE if hovered else TEXT_DIM)
            surface.blit(txt, (slot_rect.x + scale.w(58), slot_rect.y + scale.h(4)))

            # Version
            txt = f_status.render(f"v{version}", True, TEXT_DIM)
            surface.blit(txt, (slot_rect.x + scale.w(58), slot_rect.y + scale.h(18)))

            sy += scale.h(SLOT_H)

    def handle_event(self, event, scale, state):
        if not self.visible:
            return False

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return False

        gateway_files = state.gateway_files
        tools = self.get_available_tools(gateway_files)
        mouse = event.pos

        sidebar_h = min(max(len(tools), len(self.running) + 1) * SLOT_H + 30, 600)
        sidebar_rect = scale.rect(SIDEBAR_X, SIDEBAR_Y, SIDEBAR_W, sidebar_h)
        if not sidebar_rect.collidepoint(mouse):
            return False

        sy = sidebar_rect.y + scale.h(20)

        # Check running apps (stop button)
        for app in list(self.running):
            if not app.active:
                continue
            slot_rect = pygame.Rect(sidebar_rect.x + 4, sy, sidebar_rect.w - 8, scale.h(SLOT_H - 4))
            if slot_rect.collidepoint(mouse):
                # Stop button area (top-right)
                stop_rect = pygame.Rect(slot_rect.right - scale.w(16), slot_rect.y + scale.h(2), scale.w(14), scale.h(14))
                if stop_rect.collidepoint(mouse):
                    self.stop_tool(app.title)
                    audio.play_sfx("popup")
                    return True
            sy += scale.h(SLOT_H)

        if self.running:
            sy += scale.h(8)

        # Check available tools
        for title, version, tool_info in tools:
            if self.is_running(title):
                continue
            if sy + scale.h(SLOT_H) > sidebar_rect.bottom:
                break
            slot_rect = pygame.Rect(sidebar_rect.x + 4, sy, sidebar_rect.w - 8, scale.h(SLOT_H - 4))
            if slot_rect.collidepoint(mouse):
                self.run_tool(title, version, tool_info)
                return True
            sy += scale.h(SLOT_H)

        return True  # consume click inside sidebar
