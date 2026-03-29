#!/usr/bin/env python3
"""
Uplink Pygame Client — connects to headless game server.
Usage: python3 uplink_client.py [--host HOST] [--port PORT] [--no-music]
"""
import sys
import os
import argparse

# Ensure client/ is in path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
from network import Network
from ui.theme import Scale, draw_gradient, invalidate_gradient, PRIMARY, SECONDARY, ALERT, \
    TEXT_WHITE, TEXT_DIM, PANEL_BG, TOPBAR_H, TAB_H, STATUSBAR_H, DESIGN_W, DESIGN_H, get_font, draw_scanlines
from ui.login_screen import LoginScreen
from ui.widgets import Label, Button
from ui.map_view import MapView
from ui.browser import BrowserView
from ui.content_tabs import EmailView, GatewayView, MissionsView, BBSView, SoftwareView, HardwareView
from ui.app_sidebar import AppSidebar
import audio


class TopBar:
    """Minimal top bar showing player info."""
    def __init__(self, net):
        self.net = net
        self._speed_rects = []  # populated during draw for click detection

    def handle_event(self, event, scale, state):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self._speed_rects):
                if rect.collidepoint(event.pos):
                    self.net.set_speed(i)
                    audio.play_sfx("popup")
                    return

    def draw(self, surface, scale: Scale, state):
        rect = scale.rect(0, 0, DESIGN_W, TOPBAR_H)
        # Gradient dark background
        pygame.draw.rect(surface, (10, 22, 34), rect)
        pygame.draw.line(surface, (*SECONDARY, 150), (rect.x, rect.bottom), (rect.right, rect.bottom), 1)
        # Decorative accents at ends
        pygame.draw.line(surface, SECONDARY, (rect.x, rect.y), (rect.x, rect.bottom), 4)
        pygame.draw.line(surface, SECONDARY, (rect.right-4, rect.y), (rect.right-4, rect.bottom), 4)

        p = state.player
        if not p:
            return

        font = get_font(scale.fs(18))
        small = get_font(scale.fs(14), light=True)
        tiny = get_font(scale.fs(11), light=True)

        # Vertical centering helpers
        def vc(txt_surface):
            """Return design-y that vertically centers text in TOPBAR_H."""
            return (TOPBAR_H - txt_surface.get_height() / scale.factor) / 2

        # Player handle (with tech prefix)
        lbl = tiny.render("AGENT:", True, SECONDARY)
        surface.blit(lbl, (scale.x(15), scale.y(vc(lbl))))
        txt = font.render(p.get("handle", "").upper(), True, PRIMARY)
        surface.blit(txt, (scale.x(65), scale.y(vc(txt))))

        # Remote host
        rh = p.get("remotehost", "")
        if rh:
            lbl = tiny.render("HOST:", True, SECONDARY)
            surface.blit(lbl, (scale.x(600), scale.y(vc(lbl))))
            txt = font.render(rh, True, TEXT_WHITE)
            surface.blit(txt, (scale.x(645), scale.y(vc(txt))))

        # Screen name
        mt = state.screen_data.get("maintitle", "")
        if mt:
            txt = small.render(mt.upper(), True, TEXT_DIM)
            surface.blit(txt, (scale.x(850), scale.y(vc(txt))))

        # Balance
        bal = state.balance
        lbl = tiny.render("CREDITS:", True, SECONDARY)
        surface.blit(lbl, (scale.x(1340), scale.y(vc(lbl))))
        txt = font.render(f"{bal:,}c", True, (43, 255, 209))
        surface.blit(txt, (scale.x(1410), scale.y(vc(txt))))

        # Speed (clickable)
        speeds = ["PAUSE", ">", ">>", ">>>"]
        self._speed_rects = []
        sx = 1530
        for i, s in enumerate(speeds):
            is_active = state.speed == i
            color = PRIMARY if is_active else TEXT_DIM
            txt = small.render(s, True, color)
            tx = scale.x(sx)
            ty = scale.y(vc(txt))
            if is_active:
                # High-fidelity active speed indicator
                glow = pygame.Surface((scale.w(60), rect.h-4), pygame.SRCALPHA)
                glow.fill((*PRIMARY, 35))
                surface.blit(glow, (tx - scale.w(10), rect.y + 2))
                pygame.draw.rect(surface, PRIMARY, (tx - scale.w(10), rect.y+2, scale.w(60), rect.h-4), 1)

            surface.blit(txt, (tx, ty))
            self._speed_rects.append(pygame.Rect(tx - 10, rect.y, scale.w(60), rect.h))
            sx += 65

        # Date
        txt = small.render(state.date.upper(), True, TEXT_DIM)
        surface.blit(txt, (scale.x(1760), scale.y(vc(txt))))


class StatusBar:
    """Bottom status bar with connection chain and trace tracker."""
    def __init__(self):
        self.message = ""
        self.msg_time = 0

    def show(self, msg):
        self.message = msg
        self.msg_time = pygame.time.get_ticks()

    def draw(self, surface, scale: Scale, state):
        rect = scale.rect(0, DESIGN_H - STATUSBAR_H, DESIGN_W, STATUSBAR_H)
        pygame.draw.rect(surface, (10, 22, 34), rect)
        pygame.draw.line(surface, (*SECONDARY, 150), (rect.x, rect.y), (rect.right, rect.y), 1)

        font = get_font(scale.fs(14), light=True)
        tiny = get_font(scale.fs(11), light=True)

        # Connection chain
        nodes = state.connection.get("nodes", [])
        if nodes:
            lbl = tiny.render("CHAIN:", True, SECONDARY)
            surface.blit(lbl, (scale.x(15), rect.y + 10))
            chain = " > ".join(nodes)
            txt = font.render(chain, True, TEXT_DIM)
            surface.blit(txt, (scale.x(70), rect.y + 8))

        # Status message (fades after 4s)
        if self.message:
            elapsed = pygame.time.get_ticks() - self.msg_time
            if elapsed < 4000:
                alpha = 255 if elapsed < 3000 else int(255 * (4000 - elapsed) / 1000)
                # Add DATA: prefix for tech look
                msg_txt = f"DATA: {self.message.upper()}"
                txt = font.render(msg_txt, True, PRIMARY)
                txt.set_alpha(alpha)
                cx = scale.x(960) - txt.get_width() // 2
                surface.blit(txt, (cx, rect.y + 8))

        # Version info (bottom right)
        ver_txt = tiny.render("UPLINK HEADLESS MOD v2.0", True, (SECONDARY[0], SECONDARY[1], SECONDARY[2], 120))
        surface.blit(ver_txt, (rect.right - ver_txt.get_width() - 15, rect.y + 10))

        # Trace Tracker (high-fidelity)
        trace = state.trace
        if trace.get("active"):
            prog = trace.get("progress", 0)
            total = trace.get("total", 1)
            pct = prog / max(total, 1)
            
            bx = scale.x(1650)
            by = rect.y + scale.h(6)
            bw = scale.w(250)
            bh = scale.h(20)
            
            # Trace track
            pygame.draw.rect(surface, (20, 10, 10), (bx, by, bw, bh))
            if pct > 0:
                fill_w = int(bw * pct)
                # Multi-stage color (green -> yellow -> red)
                color = SUCCESS if pct < 0.4 else ((255, 200, 50) if pct < 0.7 else ALERT)
                fill_surf = pygame.Surface((fill_w, bh), pygame.SRCALPHA)
                fill_surf.fill((*color, 180))
                surface.blit(fill_surf, (bx, by))
                # Segments
                seg_w = scale.w(8)
                gap = scale.w(2)
                for sx in range(seg_w, fill_w, seg_w + gap):
                    pygame.draw.line(surface, (10, 22, 34), (bx + sx, by), (bx + sx, by + bh), max(1, gap))

            pygame.draw.rect(surface, color if pct > 0.7 else SECONDARY, (bx, by, bw, bh), 1)
            
            lbl = tiny.render("TRACE ANALYZER:", True, color if pct > 0.7 else SECONDARY)
            surface.blit(lbl, (bx - lbl.get_width() - 10, rect.y + 10))


class TabBar:
    TABS = ["Browser", "Map", "Email", "Gateway", "Missions", "BBS", "Software", "Hardware"]

    def __init__(self, on_switch):
        self.active = 0
        self.on_switch = on_switch

    def draw(self, surface, scale: Scale):
        rect = scale.rect(0, TOPBAR_H, DESIGN_W, TAB_H)
        pygame.draw.rect(surface, (11, 24, 38), rect)
        pygame.draw.line(surface, (*SECONDARY, 100), (rect.x, rect.bottom), (rect.right, rect.bottom), 1)

        font = get_font(scale.fs(16))
        tx = 20
        tab_spacing = 240
        for i, name in enumerate(self.TABS):
            is_active = i == self.active
            color = PRIMARY if is_active else TEXT_DIM
            txt = font.render(name.upper(), True, color)
            x = scale.x(tx)
            y = rect.y + (rect.h - txt.get_height()) // 2
            
            if is_active:
                # Stylized active tab indicator
                glow = pygame.Surface((scale.w(tab_spacing - 10), rect.h), pygame.SRCALPHA)
                glow.fill((*PRIMARY, 25))
                surface.blit(glow, (x - scale.w(15), rect.y))
                # Top/Bottom caps
                pygame.draw.line(surface, PRIMARY, (x - scale.w(15), rect.y), (x + scale.w(tab_spacing - 25), rect.y), 2)
                pygame.draw.line(surface, PRIMARY, (x - scale.w(15), rect.bottom-1), (x + scale.w(tab_spacing - 25), rect.bottom-1), 2)
                
            surface.blit(txt, (x, y))
            tx += tab_spacing

    def handle_event(self, event, scale: Scale):
        # F1-F8 to switch tabs
        if event.type == pygame.KEYDOWN:
            if pygame.K_F1 <= event.key <= pygame.K_F8:
                idx = event.key - pygame.K_F1
                if idx < len(self.TABS) and self.active != idx:
                    self.active = idx
                    self.on_switch(self.TABS[idx])
                return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            rect = scale.rect(0, TOPBAR_H, DESIGN_W, TAB_H)
            if rect.collidepoint(event.pos):
                # Each tab occupies a 240-design-unit-wide zone
                tab_spacing = 240
                for i, name in enumerate(self.TABS):
                    tx = 20 + i * tab_spacing
                    tab_rect = scale.rect(tx - 10, TOPBAR_H, tab_spacing, TAB_H)
                    if tab_rect.collidepoint(event.pos):
                        if self.active != i:
                            self.active = i
                            self.on_switch(name)
                        break



# BrowserView is now in ui/browser.py



class App:
    def __init__(self, host, port, no_music=False):
        pygame.init()
        pygame.display.set_caption("UPLINK")
        self.screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.scale = Scale(1280, 720)

        audio.init()
        if not no_music:
            audio.play_music()

        self.net = Network(host, port)
        self.scene = "login"  # "login" or "game"
        self.login = LoginScreen(self._on_join)
        self.topbar = TopBar(self.net)
        self.statusbar = StatusBar()

        self.browser = BrowserView(self.net, self.statusbar)
        self.sidebar = AppSidebar(self.net, self.statusbar)
        self.browser.sidebar = self.sidebar  # give browser access to sidebar
        self.sidebar.on_tool_run = self._on_tool_run
        self.tabs = TabBar(self._on_tab_switch)
        self.map_view = MapView(self.net)
        self.tab_views = {
            "Browser": self.browser,
            "Map": self.map_view,
            "Email": EmailView(self.net),
            "Gateway": GatewayView(self.net),
            "Missions": MissionsView(self.net),
            "BBS": BBSView(self.net, self.statusbar),
            "Software": SoftwareView(self.net, self.statusbar),
            "Hardware": HardwareView(self.net, self.statusbar),
        }
        self._prev_screen = ""
        self._connecting = False
        self._last_trace_poll = 0
        self._trace_warned = False

    def _on_join(self, handle, password):
        if not self.net.connected:
            self._connecting = True
            if not self.net.connect():
                self.login.set_error(f"Cannot connect to {self.net.host}:{self.net.port}")
                self._connecting = False
                return
        self.net.join(handle, password)

    def _on_tool_run(self, tool_name):
        """Called when a software tool is launched from the sidebar."""
        st = self.net.state.screen_type
        if tool_name in ("Password_Breaker", "Dictionary_Hacker"):
            # Auto-trigger password cracking if on a password screen
            if st in ("PasswordScreen", "UserIDScreen"):
                import time
                self.browser._cracking = True
                self.browser._crack_start = time.time()
                self.browser._crack_user = ""
                self.browser._crack_pass = ""
                self.net.crack_password()
                audio.play_sfx("short_whoosh6")
        elif tool_name == "Trace_Tracker":
            self.net.get_trace()

    def _on_tab_switch(self, tab_name):
        # Notify view
        view = self.tab_views.get(tab_name)
        if hasattr(view, "on_activate"):
            view.on_activate()

        # Request data for the new tab
        data_requests = {
            "Map": self.net.get_links,
            "Email": self.net.get_inbox,
            "Gateway": lambda: (self.net.get_gateway_info(), self.net.get_gateway_files()),
            "Missions": self.net.get_missions,
            "BBS": self.net.get_bbs,
            "Software": self.net.get_software_list,
            "Hardware": self.net.get_hardware_list,
        }
        req = data_requests.get(tab_name)
        if req:
            req()
        self.net.get_balance()

    def run(self):
        running = True
        while running:
            # Poll network
            if self.net.connected:
                responses = self.net.poll()
                for r in responses:
                    self._handle_response(r)

            # Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.scale = Scale(event.w, event.h)
                    invalidate_gradient()
                elif event.type == audio.MUSIC_END_EVENT:
                    audio.next_track()
                elif self.scene == "login":
                    self.login.handle_event(event, self.scale)
                elif self.scene == "game":
                    self.topbar.handle_event(event, self.scale, self.net.state)
                    # Sidebar gets first crack at events
                    if not self.sidebar.handle_event(event, self.scale, self.net.state):
                        self.tabs.handle_event(event, self.scale)
                        tab_name = TabBar.TABS[self.tabs.active]
                        view = self.tab_views.get(tab_name)
                        if view and hasattr(view, "handle_event"):
                            view.handle_event(event, self.scale, self.net.state)

            # Update browser (connecting animation, data requests, etc.)
            if self.scene == "game":
                self.browser.update(self.net.state)
                cur = self.net.state.screen_type + self.net.state.screen_data.get("maintitle", "")
                if cur != self._prev_screen:
                    self._prev_screen = cur
                    self.browser.on_screen_change()

                # Poll trace status every 2s when connected
                now = pygame.time.get_ticks()
                if now - self._last_trace_poll > 2000 and self.net.state.player.get("connected"):
                    self._last_trace_poll = now
                    self.net.get_trace()
                    # Alert on high trace progress
                    trace = self.net.state.trace
                    if trace.get("active"):
                        pct = trace.get("progress", 0) / max(trace.get("total", 1), 1)
                        if pct > 0.8 and not self._trace_warned:
                            self._trace_warned = True
                            audio.play_sfx("error")
                            self.statusbar.show("WARNING: Trace almost complete!")
                    else:
                        self._trace_warned = False

            # Draw
            draw_gradient(self.screen)
            if self.scene == "login":
                self.login.draw(self.screen, self.scale)
            elif self.scene == "game":
                # Show sidebar only when connected to a server (Browser tab)
                self.sidebar.visible = (
                    self.net.state.player.get("connected", False) and
                    TabBar.TABS[self.tabs.active] == "Browser"
                )
                if not self.sidebar.visible:
                    self.sidebar.clear_all()

                self.topbar.draw(self.screen, self.scale, self.net.state)
                self.tabs.draw(self.screen, self.scale)
                tab_name = TabBar.TABS[self.tabs.active]
                view = self.tab_views.get(tab_name)
                if view:
                    view.draw(self.screen, self.scale, self.net.state)
                self.sidebar.draw(self.screen, self.scale, self.net.state)
                self.statusbar.draw(self.screen, self.scale, self.net.state)

            pygame.display.flip()
            self.clock.tick(30)

        self.net.close()
        pygame.quit()

    def _handle_response(self, r):
        status = r.get("status", "")
        detail = r.get("detail", "")

        if status == "ok" and "session" in detail:
            # Join success
            self.scene = "game"
            self.net.joined = True
            self.net.request_state()
            self.net.get_links()
            self.net.get_balance()
            audio.play_sfx("login")
            self.statusbar.show(f"Welcome, Agent {self.net.state.player.get('handle', '')}")
        elif status == "error" and self.scene == "login":
            self.login.set_error(detail)
        elif status == "ok":
            # Don't show raw Eclipse button names in status bar
            if not any(x in detail for x in ["screen_", "button", "hd_", "ecl"]):
                self.statusbar.show(detail)
            if "authenticated" in detail:
                audio.play_sfx("login")
            elif "completed" in detail:
                audio.play_sfx("missionSuccess")
            elif "copied" in detail.lower() or "file" in detail.lower():
                audio.play_sfx("success")
            elif "$" in detail:
                audio.play_sfx("buy")
        elif status == "error":
            self.statusbar.show(f"Error: {detail}")
            audio.play_sfx("error")


def main():
    parser = argparse.ArgumentParser(description="Uplink Pygame Client")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9090)
    parser.add_argument("--no-music", action="store_true")
    parser.add_argument("--debug-log", default="", help="Write state JSON to this file each frame")
    parser.add_argument("--light-theme", action="store_true", help="White background for OCR testing")
    parser.add_argument("--auto-join", default="", help="Auto-join with this handle (skip login screen)")
    parser.add_argument("--auto-connect", default="", help="Auto-connect to this IP after joining")
    parser.add_argument("--auto-crack", action="store_true", help="Auto-crack password on connected server")
    args = parser.parse_args()

    if args.light_theme:
        import ui.theme as _t
        _t.BG_DARK = (245, 245, 247)
        _t.BG_LIGHT = (220, 225, 235)
        _t.PRIMARY = (0, 90, 190)
        _t.SECONDARY = (70, 80, 100)
        _t.SUCCESS = (0, 140, 70)
        _t.ALERT = (200, 20, 20)
        _t.TEXT_WHITE = (15, 15, 20)
        _t.TEXT_DIM = (80, 90, 110)
        _t.PANEL_BG = (235, 238, 245)
        _t.TOPBAR_BG = (215, 220, 230)
        _t.ROW_ALT = (210, 215, 225)
        _t.ROW_HOVER = (190, 200, 220)
        _t.ROW_SELECTED = (170, 185, 210)
        _t.invalidate_gradient()

    app = App(args.host, args.port, args.no_music)
    if args.debug_log:
        app.net.enable_debug_log(args.debug_log)

    # Auto-join: skip login screen, optionally connect to a server
    if args.auto_join:
        import time as _t
        if app.net.connect():
            app.net.join(args.auto_join, "auto")
            _t.sleep(2)
            app.net.poll()
            app.scene = "game"
            app.net.joined = True
            app.net.request_state()
            app.net.get_links()
            app.net.get_balance()

            if args.auto_connect:
                _t.sleep(0.5)
                app.net.poll()
                app.net.server_connect(args.auto_connect)
                _t.sleep(1)
                app.net.poll()
                app.browser._mode = "screen"

                if args.auto_crack:
                    # Crack password and auto-login as admin
                    app.net.send({"cmd": "crack_password"})
                    _t.sleep(1)
                    app.net.poll()
                    creds = app.net.state.credentials
                    admin = [c for c in creds if c.get("name") == "admin"]
                    if admin:
                        pw = admin[0]["password"]
                        print(f"Auto-crack: admin/{pw}")
                        app.net.submit_password(pw, "admin")
                        _t.sleep(1)
                        app.net.poll()

    app.run()


if __name__ == "__main__":
    main()
