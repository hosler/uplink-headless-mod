"""Browser tab: bookmarks, connecting animation, server screen rendering."""
import time
import math
import pygame
from ui.theme import (Scale, get_font, PRIMARY, SECONDARY, ALERT, SUCCESS, WARNING,
                      TEXT_WHITE, TEXT_DIM, PANEL_BG, TOPBAR_H, TAB_H,
                      STATUSBAR_H, DESIGN_W, DESIGN_H, ROW_ALT, ROW_HOVER,
                      PANEL_BORDER)
from ui.widgets import TextInput, Label, HackerPanel
import audio

# Content area starts below topbar + tabbar
CONTENT_Y = TOPBAR_H + TAB_H + 10
# Screen content area — centered in the window
SCR_W = 900
SCR_X = (DESIGN_W - SCR_W) // 2  # centered
BACK_X = SCR_X - 60  # back arrow left of content


class BrowserView:
    def __init__(self, net, statusbar):
        self.net = net
        self.statusbar = statusbar
        self._mode = "bookmarks"  # "bookmarks" | "connecting" | "screen"
        self._connect_ip = ""
        self._connect_name = ""
        self._connect_start = 0.0
        self._prev_screen_key = ""
        self._files_requested = False
        self._links_requested = False
        self._pw_input = None
        self._user_input = None
        self._search_input = TextInput(SCR_X + 10, 920, 500, TAB_H, placeholder="Search InterNIC...", size=18)
        self._scroll = 0
        self._ctx_menu = None   # list of (label, callback) or None
        self._ctx_pos = (0, 0)
        self._ctx_target = None
        # Password cracking state
        self._cracking = False
        self._crack_start = 0.0
        self._crack_duration = 3.0  # seconds for animation
        self._crack_user = ""
        self._crack_pass = ""
        self._crack_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        # Console input
        self._console_input = None
        # LAN view
        self._lan_requested = False
        self._lan_selected = -1  # selected LAN system index
        # News view
        self._news_requested = False
        self._news_selected = -1
        # Active operation (file copy, log delete, etc.)
        self._operation = None      # {type, label, start, duration, on_complete}
        self._dialog_inputs = {}    # name -> TextInput

        self._crack_user = ""
        self._crack_pass = ""
        self._crack_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"

    def connect_to(self, ip, name=""):
        self._mode = "connecting"
        self._connect_ip = ip
        self._connect_name = name
        self._connect_start = time.time()
        audio.play_sfx("bounce")
        self.net.add_link(ip)  # Bookmark the server
        self.net.server_connect(ip)

    def update(self, state):
        connected = state.player.get("connected", False)
        # Auto-detect disconnect → switch to bookmarks
        if not connected and self._mode == "screen":
            self._mode = "bookmarks"
            self.net.get_links()
        # Connecting timeout
        if self._mode == "connecting":
            if time.time() - self._connect_start > 1.5:
                self._mode = "screen"
                audio.play_sfx("login")
        # Screen change → request supplementary data
        if self._mode == "screen":
            key = state.screen_type + state.screen_data.get("maintitle", "") + state.screen_data.get("subtitle", "")
            if key != self._prev_screen_key:
                self._prev_screen_key = key
                self._files_requested = False
                self._links_requested = False
                self._pw_input = None
                self._user_input = None
                self._console_input = None
                self._dialog_inputs = {}
                self._scroll = 0
                # Clear stale data from previous screen
                state.remote_files = []
                state.remote_logs = []
                state.screen_links = []
                state.lan_data = {}
                state.news = []
                self._lan_requested = False
                self._news_requested = False
                self._news_selected = -1
            if not self._files_requested:
                subtitle = state.screen_data.get("subtitle", "").lower()
                if state.screen_type in ("GenericScreen", "unknown") and ("file" in subtitle or "server" in subtitle):
                    self.net.get_files()
                    self._files_requested = True
                elif state.screen_type == "LogScreen":
                    self.net.get_logs()
                    self._files_requested = True
            if not self._links_requested and state.screen_type == "LinksScreen":
                self.net.get_screen_links()
                self._links_requested = True
            # Try LAN scan on unknown/LanScreen screens
            if not self._lan_requested and state.screen_type in ("LanScreen", "unknown", "none"):
                self.net.lan_scan()
                self._lan_requested = True
            # Request news data when on a news screen
            if not self._news_requested:
                subtitle = state.screen_data.get("subtitle", "").lower()
                if "news" in subtitle:
                    self.net.get_news()
                    self._news_requested = True

    def on_screen_change(self):
        self._pw_input = None
        self._user_input = None

    def draw(self, surface, scale: Scale, state):
        if self._mode == "connecting":
            self._draw_connecting(surface, scale)
        elif self._mode == "bookmarks" or not state.player.get("connected", False):
            self._draw_bookmarks(surface, scale, state)
        else:
            self._draw_screen(surface, scale, state)
        # Operation progress overlay
        self._draw_operation(surface, scale)

    def handle_event(self, event, scale: Scale, state):
        if self._mode == "connecting":
            return
        elif self._mode == "bookmarks" or not state.player.get("connected", False):
            self._handle_bookmarks_event(event, scale, state)
        else:
            self._handle_screen_event(event, scale, state)

    # ================================================================
    # BOOKMARKS VIEW (disconnected)
    # ================================================================

    def _draw_bookmarks(self, surface, scale, state):
        f_title = get_font(scale.fs(42))
        f_sub = get_font(scale.fs(24), light=True)
        f_name = get_font(scale.fs(22))
        f_ip = get_font(scale.fs(15), light=True)

        txt = f_title.render("B O O K M A R K S", True, PRIMARY)
        surface.blit(txt, (scale.x(SCR_X + 10), scale.y(CONTENT_Y)))
        txt = f_sub.render("Your saved links", True, SECONDARY)
        surface.blit(txt, (scale.x(SCR_X + 10), scale.y(CONTENT_Y + 48)))

        # Separator (decorative)
        sy = scale.y(CONTENT_Y + 85)
        sw = max(1, scale.h(1))
        sh = max(1, scale.h(4))
        pygame.draw.line(surface, (*SECONDARY, 150), (scale.x(SCR_X), sy),
                         (scale.x(SCR_X + SCR_W), sy), sw)
        pygame.draw.line(surface, SECONDARY, (scale.x(SCR_X), sy - sh), (scale.x(SCR_X), sy + sh), max(1, scale.w(2)))
        pygame.draw.line(surface, SECONDARY, (scale.x(SCR_X + SCR_W), sy - sh), (scale.x(SCR_X + SCR_W), sy + sh), max(1, scale.w(2)))

        # Link rows
        links = state.links
        mouse = pygame.mouse.get_pos()
        row_h = 42
        start_y = CONTENT_Y + 110

        for i, link in enumerate(links):
            y = start_y + i * (row_h + 8)
            if y > 920:
                break
            rect = scale.rect(SCR_X, y, SCR_W, row_h)
            hovered = rect.collidepoint(mouse)

            # Row background
            fill_alpha = 45 if hovered else 20
            fill = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            fill.fill((*PRIMARY, fill_alpha))
            surface.blit(fill, rect.topleft)
            
            # Row border
            pygame.draw.rect(surface, (*SECONDARY, 100), rect, 1)
            if hovered:
                pygame.draw.rect(surface, PRIMARY, rect, 1)

            # Diamond icon
            dot_x = scale.x(SCR_X + 24)
            dot_y = rect.y + rect.h // 2
            ds = scale.w(8)
            pts = [(dot_x, dot_y - ds // 2), (dot_x + ds // 2, dot_y),
                   (dot_x, dot_y + ds // 2), (dot_x - ds // 2, dot_y)]
            color = PRIMARY if hovered else SECONDARY
            
            if hovered:
                # Diamond glow
                glow = pygame.Surface((ds * 3, ds * 3), pygame.SRCALPHA)
                pygame.draw.polygon(glow, (*PRIMARY, 120), [(ds*1.5, ds*0.5), (ds*2.5, ds*1.5), (ds*1.5, ds*2.5), (ds*0.5, ds*1.5)])
                surface.blit(glow, (dot_x - ds * 1.5, dot_y - ds * 1.5))
                
            pygame.draw.polygon(surface, color, pts)

            # Name
            name = link.get("name", "Unknown")
            txt = f_name.render(name, True, TEXT_WHITE if hovered else PRIMARY)
            surface.blit(txt, (scale.x(SCR_X + 50), rect.y + scale.h(2)))

            # IP
            ip = link.get("ip", "")
            txt = f_ip.render(ip, True, TEXT_DIM)
            surface.blit(txt, (scale.x(SCR_X + 52), rect.y + scale.h(24)))

            # Arrow
            if hovered:
                txt = f_name.render(">", True, PRIMARY)
                surface.blit(txt, (scale.x(SCR_X + SCR_W - 40), rect.y + scale.h(8)))

        # Hint at bottom
        f_hint = get_font(scale.fs(14), light=True)
        txt = f_hint.render("Connect to InterNIC to search for more servers", True, SECONDARY)
        surface.blit(txt, (scale.x(SCR_X + 10), scale.y(960)))

    def _handle_bookmarks_event(self, event, scale, state):
        # Keyboard: 1-9 to connect to bookmark by index
        if event.type == pygame.KEYDOWN:
            links = state.links
            if pygame.K_1 <= event.key <= pygame.K_9:
                idx = event.key - pygame.K_1
                if idx < len(links):
                    self.connect_to(links[idx]["ip"], links[idx].get("name", ""))
                return

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return

        links = state.links
        row_h = 42
        start_y = CONTENT_Y + 110

        for i, link in enumerate(links):
            y = start_y + i * (row_h + 8)
            if y > 920:
                break
            rect = scale.rect(SCR_X, y, SCR_W, row_h)
            if rect.collidepoint(event.pos):
                self.connect_to(link["ip"], link.get("name", ""))
                return

    # ================================================================
    # CONNECTING ANIMATION
    # ================================================================

    def _draw_connecting(self, surface, scale):
        elapsed = time.time() - self._connect_start
        progress = min(1.0, elapsed / 1.5)

        f_label = get_font(scale.fs(22), light=True)
        f_ip = get_font(scale.fs(44))
        f_name = get_font(scale.fs(20), light=True)
        f_tech = get_font(scale.fs(12), light=True)

        cx = DESIGN_W // 2
        cy = DESIGN_H // 2 - 100
        
        # Center panel for connection
        pw, ph = 600, 320
        HackerPanel(cx - pw//2, cy - 10, pw, ph, title="Establishing Link").draw(surface, scale)

        # Pulse effect for "Connecting to..."
        pulse = (math.sin(time.time() * 6) + 1) / 2
        # Pulse between TEXT_DIM and PRIMARY
        r = int(TEXT_DIM[0] + (PRIMARY[0] - TEXT_DIM[0]) * pulse)
        g = int(TEXT_DIM[1] + (PRIMARY[1] - TEXT_DIM[1]) * pulse)
        b = int(TEXT_DIM[2] + (PRIMARY[2] - TEXT_DIM[2]) * pulse)
        txt = f_label.render("Connecting to...", True, (r, g, b))
        surface.blit(txt, (scale.x(cx) - txt.get_width() // 2, scale.y(cy + 40)))

        txt = f_ip.render(self._connect_ip, True, PRIMARY)
        surface.blit(txt, (scale.x(cx) - txt.get_width() // 2, scale.y(cy + 85)))

        if self._connect_name:
            txt = f_name.render(self._connect_name.upper(), True, TEXT_DIM)
            surface.blit(txt, (scale.x(cx) - txt.get_width() // 2, scale.y(cy + 130)))

        # Progress bar (segmented)
        bar_w = 420
        bar_h = 24
        bx = cx - bar_w // 2
        by = cy + 170
        from ui.widgets import ProgressBar
        pb = ProgressBar(bx, by, bar_w, bar_h, segments=True)
        pb.value = progress
        pb.draw(surface, scale)

        # Tech noise and deco lines
        noise_y = cy + 230
        import random
        for i in range(4):
            line = "".join(random.choices("0123456789ABCDEF", k=32))
            txt = f_tech.render(f"AUTH_STREAM_{i}: {line}", True, (35, 75, 110))
            surface.blit(txt, (scale.x(cx) - txt.get_width() // 2, scale.y(noise_y + i * 16)))
        
        # Subtle "LINKING..." text at bottom of panel
        if progress < 1.0:
            txt = f_tech.render("ESTABLISHING ENCRYPTED HANDSHAKE...", True, (50, 100, 150))
            surface.blit(txt, (scale.x(cx) - txt.get_width() // 2, scale.y(cy + ph - 30)))

    # ================================================================
    # SCREEN RENDERING (connected)
    # ================================================================

    def _draw_screen(self, surface, scale, state):
        st = state.screen_type
        sd = state.screen_data

        f_title = get_font(scale.fs(36))
        f_sub = get_font(scale.fs(22), light=True)
        f_small = get_font(scale.fs(15), light=True)

        # Back arrow on the left
        back_r = scale.rect(BACK_X, CONTENT_Y + 5, 40, 40)
        mouse = pygame.mouse.get_pos()
        bh = back_r.collidepoint(mouse)
        if bh:
            # Pulsing glow
            pulse = (math.sin(time.time() * 8) + 1) / 2
            glow_r = scale.w(20 + 4 * pulse)
            glow = pygame.Surface((glow_r*2, glow_r*2), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*PRIMARY, 40), (glow_r, glow_r), glow_r)
            surface.blit(glow, (back_r.centerx - glow_r, back_r.centery - glow_r))
            
        f_arrow = get_font(scale.fs(28))
        txt = f_arrow.render("<", True, TEXT_WHITE if bh else SECONDARY)
        surface.blit(txt, (back_r.x + 8, back_r.y + 2))
        pygame.draw.rect(surface, (*SECONDARY, 80), back_r, 1, border_radius=scale.w(20))

        # Disconnect top-right
        disc_r = scale.rect(SCR_X + SCR_W - 120, CONTENT_Y, 120, 32)
        dh = disc_r.collidepoint(mouse)
        c = ALERT if dh else (100, 30, 30)
        # Beveled disconnect button
        pygame.draw.rect(surface, (20, 10, 10), disc_r, border_radius=3)
        pygame.draw.rect(surface, c, disc_r, 1, border_radius=3)
        if dh:
            s = pygame.Surface((disc_r.w, disc_r.h), pygame.SRCALPHA)
            s.fill((*ALERT, 40))
            surface.blit(s, disc_r.topleft)

        txt = f_small.render("DISCONNECT", True, (255, 255, 255) if dh else ALERT)
        surface.blit(txt, (disc_r.centerx - txt.get_width() // 2, disc_r.centery - txt.get_height() // 2))

        # Title + Subtitle
        # When maintitle is generic ("Uplink"), promote subtitle to be the main title
        cy = CONTENT_Y
        mt = sd.get("maintitle", "")
        sub = sd.get("subtitle", "")

        # Try to find the actual server name from player's links
        remote_ip = state.player.get("remotehost", "")
        server_name = ""
        for lk in state.links:
            if lk.get("ip") == remote_ip:
                server_name = lk.get("name", "")
                break

        if mt and mt != "Uplink" and mt != "uplink":
            # Real title (e.g. "InterNIC", "Uplink Test Machine")
            display_title = mt
            display_sub = sub
        elif server_name:
            display_title = server_name
            display_sub = sub
        elif sub:
            display_title = sub
            display_sub = ""
        else:
            display_title = mt
            display_sub = ""

        if display_title:
            spaced = " ".join(display_title.upper())
            txt = f_title.render(spaced, True, PRIMARY)
            surface.blit(txt, (scale.x(SCR_X + 10), scale.y(cy)))
            cy += 46
        # Message/Dialog/Auth screens draw their own internal headers, so suppress redundant subtitle here
        if display_sub and st not in ("MessageScreen", "DialogScreen", "PasswordScreen", "UserIDScreen"):
            txt = f_sub.render(display_sub, True, SECONDARY)
            surface.blit(txt, (scale.x(SCR_X + 10), scale.y(cy)))
            cy += TAB_H
        cy += 14

        # Separator
        sy = scale.y(cy)
        pygame.draw.line(surface, SECONDARY, (scale.x(SCR_X), sy),
                         (scale.x(SCR_X + SCR_W), sy), max(1, scale.h(2)))
        cy += 10

        # Dispatch on screen type
        if st == "MenuScreen":
            self._draw_menu(surface, scale, state, cy)
        elif st == "DialogScreen":
            self._draw_dialog(surface, scale, state, cy)
        elif st in ("PasswordScreen", "UserIDScreen"):
            self._draw_password(surface, scale, state, st, cy)
        elif st == "LinksScreen":
            self._draw_links(surface, scale, state, cy)
        elif st == "MessageScreen":
            self._draw_message(surface, scale, state, cy)
        elif st == "LogScreen":
            self._draw_log_viewer(surface, scale, state, cy, state.remote_logs, pygame.mouse.get_pos())
        elif st in ("GenericScreen", "unknown"):
            self._draw_generic(surface, scale, state, cy)
        elif st == "HighSecurityScreen":
            self._draw_highsecurity(surface, scale, state, cy)
        elif st == "none":
            # Check if LAN data is available
            if state.lan_data.get("systems"):
                self._draw_lan(surface, scale, state, cy)
        elif st == "LanScreen":
            self._draw_lan(surface, scale, state, cy)
        else:
            # Unknown screen — might be LAN if lan_data populated
            if state.lan_data.get("systems"):
                self._draw_lan(surface, scale, state, cy)
            else:
                f = get_font(scale.fs(18), light=True)
                txt = f.render(f"Screen: {st}", True, TEXT_DIM)
                surface.blit(txt, (scale.x(SCR_X + 10), scale.y(cy)))

    def _draw_menu(self, surface, scale, state, cy):
        f_btn = get_font(scale.fs(22))
        sd = state.screen_data
        mt = sd.get("maintitle", "").lower()
        sub = sd.get("subtitle", "").lower()
        is_internic = "internic" in mt or "internic" in sub

        # If InterNIC, add search box before options
        if is_internic:
            f_lab = get_font(scale.fs(16), light=True)
            txt = f_lab.render("SEARCH FOR SYSTEMS:", True, SECONDARY)
            surface.blit(txt, (scale.x(SCR_X + 10), scale.y(cy + 6)))

            self._search_input.dx = SCR_X + 220
            self._search_input.dy = cy - 2
            self._search_input.dw = 400
            self._search_input.dh = TAB_H
            self._search_input.placeholder = "ENTER KEYWORDS..."
            self._search_input.draw(surface, scale)

            # Add "GO" button
            go_r = scale.rect(SCR_X + 630, cy - 2, 80, TAB_H)
            mouse = pygame.mouse.get_pos()
            gh = go_r.collidepoint(mouse)
            pygame.draw.rect(surface, PRIMARY if gh else SECONDARY, go_r, 1, border_radius=2)
            if gh:
                s = pygame.Surface((go_r.w, go_r.h), pygame.SRCALPHA)
                s.fill((*PRIMARY, 40))
                surface.blit(s, go_r.topleft)
            f_go = get_font(scale.fs(18))
            txt = f_go.render("GO", True, PRIMARY if gh else SECONDARY)
            surface.blit(txt, (go_r.centerx - txt.get_width() // 2, go_r.centery - txt.get_height() // 2))

            cy += 60

        options = state.screen_data.get("options", [])
        mouse = pygame.mouse.get_pos()
        for i, opt in enumerate(options):
            y = cy + i * 54
            rect = scale.rect(SCR_X + 10, y, SCR_W - 20, 48)
            hovered = rect.collidepoint(mouse)

            # Row background
            if hovered:
                bg_color = (*ROW_HOVER, 180)
                border_color = PRIMARY
            else:
                bg_color = (*ROW_ALT, 120) if i % 2 == 0 else (0, 0, 0, 0)
                border_color = SECONDARY

            if bg_color[3] > 0:
                fill = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                fill.fill(bg_color)
                surface.blit(fill, rect.topleft)

            pygame.draw.rect(surface, border_color, rect, 1, border_radius=2)

            # Uplink-style selection indicator (filled triangle/pointer)
            if hovered:
                pts = [
                    (rect.x + scale.w(10), rect.y + scale.h(14)),
                    (rect.x + scale.w(10), rect.y + rect.h - scale.h(14)),
                    (rect.x + scale.w(26), rect.y + rect.h // 2)
                ]
                pygame.draw.polygon(surface, PRIMARY, pts)
                # Outer glow for triangle (symmetric)
                for j in range(1, 4):
                    # Expand triangle points outward: top-left (p0), bottom-left (p1), tip (p2)
                    glow_pts = [
                        (pts[0][0] - j, pts[0][1] - j),
                        (pts[1][0] - j, pts[1][1] + j),
                        (pts[2][0] + j, pts[2][1])
                    ]
                    pygame.draw.polygon(surface, (*PRIMARY, 60 - j * 15), glow_pts, 1)
            else:
                # Thin pointer
                pts = [
                    (rect.x + scale.w(12), rect.y + scale.h(18)),
                    (rect.x + scale.w(12), rect.y + rect.h - scale.h(18)),
                    (rect.x + scale.w(20), rect.y + rect.h // 2)
                ]
                pygame.draw.polygon(surface, SECONDARY, pts)

            txt = f_btn.render(opt["caption"], True, TEXT_WHITE if hovered else PRIMARY)
            surface.blit(txt, (rect.x + scale.w(42), rect.y + (rect.h - txt.get_height()) // 2))

    def _draw_highsecurity(self, surface, scale, state, cy):
        f_title = get_font(scale.fs(22))
        f_label = get_font(scale.fs(16), light=True)
        f_btn = get_font(scale.fs(18))
        mouse = pygame.mouse.get_pos()
        options = state.screen_data.get("options", [])

        # Header
        txt = f_title.render("SECURITY AUTHENTICATION REQUIRED", True, ALERT)
        surface.blit(txt, (scale.x(SCR_X + 10), scale.y(cy)))
        cy += 35

        txt = f_label.render(f"{len(options)} verification steps remaining", True, TEXT_DIM)
        surface.blit(txt, (scale.x(SCR_X + 10), scale.y(cy)))
        cy += 30

        # Challenge icons
        CHALLENGE_ICONS = {
            "password": ("PASS", ALERT),
            "voice": ("VOICE", (43, 255, 209)),
            "cypher": ("CRYPT", WARNING),
            "elliptic": ("CRYPT", WARNING),
        }

        for i, opt in enumerate(options):
            caption = opt.get("caption", "")
            y = cy + i * 90

            # Use HackerPanel for each challenge
            panel_w = SCR_W - 40
            panel_h = 75
            hp = HackerPanel(SCR_X + 20, y, panel_w, panel_h, color=ALERT)
            hp.draw(surface, scale)
            
            panel_rect = scale.rect(SCR_X + 20, y, panel_w, panel_h)
            hovered = panel_rect.collidepoint(mouse)

            if hovered:
                bg = pygame.Surface((panel_rect.w, panel_rect.h), pygame.SRCALPHA)
                bg.fill((*ALERT, 30))
                surface.blit(bg, panel_rect.topleft)

            # Icon
            icon_label = "AUTH"
            icon_color = ALERT
            for key, (lbl, col) in CHALLENGE_ICONS.items():
                if key in caption.lower():
                    icon_label = lbl
                    icon_color = col
                    break

            icon_rect = scale.rect(SCR_X + 40, y + 12, 65, 50)
            pygame.draw.rect(surface, icon_color, icon_rect, 1, border_radius=4)
            if hovered:
                glow = pygame.Surface((icon_rect.w + 4, icon_rect.h + 4), pygame.SRCALPHA)
                pygame.draw.rect(glow, (*icon_color, 40), (0, 0, icon_rect.w+4, icon_rect.h+4), 2, border_radius=4)
                surface.blit(glow, (icon_rect.x - 2, icon_rect.y - 2))

            f_icon = get_font(scale.fs(15))
            txt = f_icon.render(icon_label, True, icon_color)
            surface.blit(txt, (icon_rect.centerx - txt.get_width() // 2,
                               icon_rect.centery - txt.get_height() // 2))

            # Challenge label
            txt = f_btn.render(caption.upper(), True, TEXT_WHITE if hovered else PRIMARY)
            surface.blit(txt, (scale.x(SCR_X + 125), scale.y(y + 18)))

            # Status text
            status_txt = "Click to attempt bypass" if hovered else "SYSTEM LOCKED"
            status_col = icon_color if hovered else TEXT_DIM
            txt = f_label.render(status_txt, True, status_col)
            surface.blit(txt, (scale.x(SCR_X + 125), scale.y(y + 44)))

            # Lock icon on right
            f_lock = get_font(scale.fs(22))
            lock_label = "READY" if hovered else "LOCKED"
            txt = f_lock.render(lock_label, True, ALERT if not hovered else SUCCESS)
            surface.blit(txt, (scale.x(SCR_X + SCR_W - 140), scale.y(y + 25)))

    def _draw_dialog(self, surface, scale, state, cy):
        f_body = get_font(scale.fs(16), light=True)
        f_btn = get_font(scale.fs(18))
        f_label = get_font(scale.fs(14), light=True)
        mouse = pygame.mouse.get_pos()

        # Widget types: 1=BASIC, 2=CAPTION, 3=TEXTBOX, 4=PASSWORDBOX,
        # 5=NEXTPAGE, 6=IMAGE, 7=IMAGEBUTTON, 8=SCRIPTBUTTON, 9=FIELDVALUE
        CAPTION_TYPES = (1, 2, 9)
        INPUT_TYPES = (3, 4)
        BUTTON_TYPES = (5, 7, 8)

        # First pass: collect inputs and buttons
        widgets = state.screen_data.get("widgets", [])
        
        # Determine if this looks like a bank form
        is_bank = any("bank" in w.get("caption", "").lower() for w in widgets) or "bank" in state.screen_data.get("subtitle", "").lower()
        
        # Use a centered form container
        form_w = 500
        form_x = SCR_X + (SCR_W - form_w) // 2
        
        # Draw decorative form background
        bg_h = 450 # estimate
        bg_color = (20, 30, 45, 180) if is_bank else (15, 25, 40, 150)
        border_color = PRIMARY if is_bank else SECONDARY
        
        pygame.draw.rect(surface, bg_color, scale.rect(form_x - 20, cy, form_w + 40, bg_h), border_radius=4)
        pygame.draw.rect(surface, border_color, scale.rect(form_x - 20, cy, form_w + 40, bg_h), 1, border_radius=4)
        
        if is_bank:
            # Add a "Bank Secure" header strip
            strip_r = scale.rect(form_x - 20, cy, form_w + 40, 32)
            pygame.draw.rect(surface, (10, 40, 80), strip_r, border_top_left_radius=4, border_top_right_radius=4)
            pygame.draw.rect(surface, PRIMARY, strip_r, 1, border_top_left_radius=4, border_top_right_radius=4)
            
            # Padlock icon (scaled and refined)
            lx, ly = strip_r.x + scale.w(15), strip_r.centery
            pw, ph = scale.w(12), scale.h(10)
            pygame.draw.rect(surface, PRIMARY, (lx, ly - scale.h(2), pw, ph), border_radius=1)
            # Shackle: centered above body
            shackle_rect = pygame.Rect(lx + scale.w(2), ly - scale.h(8), scale.w(8), scale.h(12))
            pygame.draw.arc(surface, PRIMARY, shackle_rect, 0, 3.14, max(1, scale.w(2)))
            
            f_sec = get_font(scale.fs(12), light=True)
            txt = f_sec.render("SECURE BANKING INTERFACE - ENCRYPTION: [RSA 4096-BIT / ACTIVE]", True, PRIMARY)
            surface.blit(txt, (lx + scale.w(25), strip_r.centery - txt.get_height() // 2))
            cy += 42
        else:
            cy += 20
        for w in widgets:
            cap = w.get("caption", "")
            wname = w.get("name", "")
            wtype = w.get("type", 1)
            if not cap and wtype not in INPUT_TYPES: continue

            if wtype in CAPTION_TYPES:
                col = PRIMARY if is_bank and "account" in cap.lower() else TEXT_WHITE
                for line in self._word_wrap(cap, f_body, scale.w(form_w)):
                    txt = f_body.render(line, True, col)
                    surface.blit(txt, (scale.x(form_x), scale.y(cy)))
                    cy += 22
                cy += 8

            elif wtype in INPUT_TYPES:
                # Text input field
                txt = f_label.render(cap.upper() if cap else "FIELD", True, SECONDARY)
                surface.blit(txt, (scale.x(form_x), scale.y(cy)))
                cy += 20
                
                # Manage TextInput widget
                if wname not in self._dialog_inputs:
                    self._dialog_inputs[wname] = TextInput(form_x, cy, form_w, TAB_H, placeholder=cap, masked=(wtype==4), size=18)
                    # If it's the first input, focus it
                    if len(self._dialog_inputs) == 1:
                        self._dialog_inputs[wname].focused = True
                
                inp = self._dialog_inputs[wname]
                inp.dx, inp.dy, inp.dw = form_x, cy, form_w
                inp.draw(surface, scale)
                cy += 48

            elif wtype in BUTTON_TYPES:
                # Form button (Submit, Cancel, etc.)
                btn_w = 220
                rect = scale.rect(form_x + (form_w - btn_w) // 2, cy, btn_w, 40)
                hovered = rect.collidepoint(mouse)
                
                col = SUCCESS if any(k in cap.lower() for k in ("create", "ok", "next", "submit")) else PRIMARY
                
                if hovered:
                    pygame.draw.rect(surface, col, rect, 0, border_radius=4)
                    txt = f_btn.render(cap.upper(), True, (0, 0, 0))
                else:
                    pygame.draw.rect(surface, col, rect, 1, border_radius=4)
                    txt = f_btn.render(cap.upper(), True, col)
                
                surface.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))
                cy += 50

        # Optional OK button if no other buttons found
        if not any(w.get("type") in BUTTON_TYPES for w in widgets):
            btn_w = 160
            rect = scale.rect(form_x + (form_w - btn_w) // 2, cy + 10, btn_w, 40)
            hovered = rect.collidepoint(mouse)
            if hovered:
                pygame.draw.rect(surface, PRIMARY, rect, 0, border_radius=4)
                txt = f_btn.render("OK", True, (0, 0, 0))
            else:
                pygame.draw.rect(surface, PRIMARY, rect, 1, border_radius=4)
                txt = f_btn.render("OK", True, PRIMARY)
            surface.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))

    def _draw_password(self, surface, scale, state, st, cy):
        import random, time
        f_subtitle = get_font(scale.fs(22))
        f_label = get_font(scale.fs(16), light=True)
        f_btn = get_font(scale.fs(20))
        f_crack = get_font(scale.fs(32))
        f_crack_label = get_font(scale.fs(14), light=True)
        f_error = get_font(scale.fs(18))
        mouse = pygame.mouse.get_pos()

        # Detect error message (e.g. "Invalid User ID")
        error_msg = ""
        for b in state.buttons:
            cap = b.get("caption", "").upper()
            if any(k in cap for k in ("INVALID", "DENIED", "INCORRECT", "FAILED")):
                error_msg = cap
                break

        # Centered sub-heading for the form
        cy += 20
        txt = f_subtitle.render("AUTHENTICATION REQUIRED", True, ALERT)
        surface.blit(txt, (scale.x(SCR_X + (SCR_W - txt.get_width() / scale.factor) // 2), scale.y(cy)))
        cy += 50
        
        if error_msg:
            txt = f_error.render(error_msg, True, ALERT)
            surface.blit(txt, (scale.x(SCR_X + (SCR_W - txt.get_width() / scale.factor) // 2), scale.y(cy)))
            cy += 40
        else:
            cy += 10

        # Center the form in the content area
        form_x = SCR_X + (SCR_W - 400) // 2
        form_w = 400

        # Check if cracking animation is running
        if self._cracking:
            elapsed = time.time() - self._crack_start
            progress = min(1.0, elapsed / self._crack_duration)

            # Find credentials from server response
            creds = state.credentials
            if creds and not self._crack_pass:
                # Pick admin or first available
                admin = [c for c in creds if c.get("name") == "admin"]
                target = admin[0] if admin else (creds[0] if creds else {})
                self._crack_user = target.get("name", "")
                self._crack_pass = target.get("password", "")

            # Decorative panel for cracking
            HackerPanel(form_x - 20, cy - 10, form_w + 40, 220, title="Decryption", color=SUCCESS).draw(surface, scale)

            # Cycling character animation
            anim_y = cy + 20
            if st == "UserIDScreen" and self._crack_user:
                Label("Target User", 14, SUCCESS, True).draw(surface, scale, form_x, anim_y - 10)
                anim_y += 10
                displayed = ""
                for j, ch in enumerate(self._crack_user):
                    # Improved progress logic: characters finish sequentially
                    char_progress = min(1.0, max(0.0, progress * (len(self._crack_user) + 2) - j))
                    if char_progress >= 1.0:
                        displayed += ch
                    else:
                        displayed += random.choice(self._crack_chars)
                txt = f_crack.render(displayed, True, SUCCESS)
                surface.blit(txt, (scale.x(form_x), scale.y(anim_y)))
                anim_y += 45

            if self._crack_pass:
                Label("Access Code", 14, SUCCESS, True).draw(surface, scale, form_x, anim_y + 5)
                anim_y += 25
                displayed = ""
                pw_start = 0.3 if st == "UserIDScreen" else 0.0
                pw_progress = max(0, (progress - pw_start) / (1.0 - pw_start))
                for j, ch in enumerate(self._crack_pass):
                    char_progress = min(1.0, max(0.0, pw_progress * (len(self._crack_pass) + 2) - j))
                    if char_progress >= 1.0:
                        displayed += ch
                    else:
                        displayed += random.choice(self._crack_chars)
                txt = f_crack.render(displayed, True, SUCCESS)
                surface.blit(txt, (scale.x(form_x), scale.y(anim_y)))
                anim_y += 55

            # Progress bar
            bar_y = anim_y + 15
            bar_rect = scale.rect(form_x, bar_y, form_w, 8)
            pygame.draw.rect(surface, (20, 35, 50), bar_rect)
            fill_rect = scale.rect(form_x, bar_y, int(form_w * progress), 8)
            pygame.draw.rect(surface, SUCCESS, fill_rect)

            txt = f_crack_label.render("DECRYPTING...", True, SUCCESS)
            surface.blit(txt, (scale.x(form_x), scale.y(bar_y + 14)))

            # Auto-submit when done
            if progress >= 1.0 and self._crack_pass:
                self._cracking = False
                if st == "UserIDScreen":
                    self.net.submit_password(self._crack_pass, self._crack_user)
                else:
                    self.net.submit_password(self._crack_pass)
                audio.play_sfx("login")
                self.statusbar.show(f"Cracked: {self._crack_user}/{self._crack_pass}")
                self._crack_user = ""
                self._crack_pass = ""
            return

        # Normal password form
        if not self._pw_input:
            self._pw_input = TextInput(form_x, cy + 45, form_w, 40, placeholder="Access Code", masked=True, size=22)
            self._pw_input.focused = True
            self._user_input = TextInput(form_x, cy - 5, form_w, 40, placeholder="Username", size=22)
            if st == "UserIDScreen":
                self._user_input.text = "admin"
                self._user_input.cursor_pos = 5

        if st == "UserIDScreen":
            Label("USER ID:", 15, SECONDARY, True).draw(surface, scale, form_x, cy - 26)
            self._user_input.draw(surface, scale)

        Label("ACCESS CODE:", 15, SECONDARY, True).draw(surface, scale, form_x, cy + 26)
        self._pw_input.draw(surface, scale)

        # Submit button
        btn_w = 220
        btn_x = form_x + (form_w - btn_w) // 2
        rect = scale.rect(btn_x, cy + 105, btn_w, 44)
        hovered = rect.collidepoint(mouse)
        if hovered:
            pygame.draw.rect(surface, PRIMARY, rect, 0, border_radius=3)
            txt = f_btn.render("SUBMIT", True, (0, 0, 0))
        else:
            pygame.draw.rect(surface, PRIMARY, rect, 1, border_radius=3)
            txt = f_btn.render("SUBMIT", True, PRIMARY)
        surface.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))

        # "Run Password Breaker" button
        crack_y = cy + 185
        crack_w = 340
        crack_x = form_x + (form_w - crack_w) // 2
        crack_rect = scale.rect(crack_x, crack_y, crack_w, 42)
        crack_hovered = crack_rect.collidepoint(mouse)
        
        # Stylized hacking tool button
        bg = pygame.Surface((crack_rect.w, crack_rect.h), pygame.SRCALPHA)
        bg.fill((*ALERT, 60 if crack_hovered else 30))
        surface.blit(bg, crack_rect.topleft)
        pygame.draw.rect(surface, ALERT if crack_hovered else (150, 40, 40), crack_rect, 1, border_radius=2)
        
        if crack_hovered:
            # Subtle glow
            glow = pygame.Surface((crack_rect.w + 10, crack_rect.h + 10), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*ALERT, 40), (0, 0, crack_rect.w+10, crack_rect.h+10), 2, border_radius=4)
            surface.blit(glow, (crack_rect.x - 5, crack_rect.y - 5))

        f_crack_btn = get_font(scale.fs(18))
        # Add a small icon prefix
        txt = f_crack_btn.render("[!] RUN PASSWORD BREAKER", True, TEXT_WHITE if crack_hovered else ALERT)
        surface.blit(txt, (crack_rect.centerx - txt.get_width() // 2, crack_rect.centery - txt.get_height() // 2))

    def _draw_links(self, surface, scale, state, cy):
        """Render LinksScreen — clickable server list with search filter."""
        f_name = get_font(scale.fs(20))
        f_ip = get_font(scale.fs(15), light=True)
        f_label = get_font(scale.fs(16), light=True)
        f_header = get_font(scale.fs(14))
        mouse = pygame.mouse.get_pos()
        row_h = 42

        # Search/filter box
        self._search_input.dy = cy - 8
        self._search_input.dx = SCR_X + 540
        self._search_input.dw = 350
        self._search_input.dh = TAB_H
        self._search_input.placeholder = "SEARCH SYSTEMS..."
        self._search_input.size = 16
        self._search_input.draw(surface, scale)

        # Filter links
        links = state.screen_links
        query = self._search_input.text.strip().lower()
        if query:
            links = [l for l in links if query in l.get("name", "").lower() or query in l.get("ip", "").lower()]

        # Header for the list
        txt = f_header.render(f"SHOWING {len(links)} KNOWN SYSTEMS", True, SECONDARY)
        surface.blit(txt, (scale.x(SCR_X + 15), scale.y(cy - 2)))
        cy += 45

        # Column headers
        pygame.draw.rect(surface, (20, 35, 50), scale.rect(SCR_X + 10, cy, SCR_W - 20, 30), border_radius=2)
        txt = f_header.render("SYSTEM NAME", True, PRIMARY)
        surface.blit(txt, (scale.x(SCR_X + 30), scale.y(cy + 6)))
        txt = f_header.render("NETWORK ADDRESS", True, PRIMARY)
        surface.blit(txt, (scale.x(SCR_X + SCR_W - 200), scale.y(cy + 6)))
        cy += 38

        for i, link in enumerate(links):
            y = cy + i * row_h
            if y > 980:
                break
            rect = scale.rect(SCR_X + 10, y, SCR_W - 20, row_h - 4)
            hovered = rect.collidepoint(mouse)

            # Row background
            if hovered:
                bg = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                bg.fill((*ROW_HOVER, 200))
                surface.blit(bg, rect.topleft)
                pygame.draw.rect(surface, PRIMARY, rect, 1, border_radius=2)
            elif i % 2 == 1:
                bg = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                bg.fill((*ROW_ALT, 120))
                surface.blit(bg, rect.topleft)

            name = link.get("name", "").upper()
            ip = link.get("ip", "")
            
            # Diamond icon
            dot_x = rect.x + scale.w(12)
            dot_y = rect.centery
            ds = scale.w(6)
            pts = [(dot_x, dot_y - ds // 2), (dot_x + ds // 2, dot_y),
                   (dot_x, dot_y + ds // 2), (dot_x - ds // 2, dot_y)]
            pygame.draw.polygon(surface, PRIMARY if hovered else SECONDARY, pts)

            # Server name
            txt = f_name.render(name[:50], True, TEXT_WHITE if hovered else PRIMARY)
            surface.blit(txt, (rect.x + scale.w(30), rect.y + (rect.h - txt.get_height()) // 2))
            
            # IP right-aligned
            txt = f_ip.render(ip, True, TEXT_WHITE if hovered else TEXT_DIM)
            surface.blit(txt, (rect.right - txt.get_width() - 20, rect.y + (rect.h - txt.get_height()) // 2))

    def _draw_message(self, surface, scale, state, cy):
        f_title = get_font(scale.fs(22))
        f_body = get_font(scale.fs(18), light=True)
        f_btn = get_font(scale.fs(20))
        mouse = pygame.mouse.get_pos()

        # Find the actual message text (longest caption that isn't a button label)
        msg_text = ""
        for btn in state.buttons:
            cap = btn.get("caption", "").strip()
            if cap and cap not in ("OK", " ", "") and len(cap) > len(msg_text):
                msg_text = cap

        if msg_text:
            # Detect if this is a warning/error message
            is_warning = any(k in msg_text.upper() for k in ("UNAUTHORISED", "CRIMINAL", "WARNING", "DENIED", "ALERT", "ILLEGAL"))
            theme_color = ALERT if is_warning else PRIMARY
            subtitle = state.screen_data.get("subtitle", "MESSAGE").upper()
            
            # Deduplicate: if subtitle is almost same as first few words of message, or message is subtitle
            clean_msg = msg_text.strip().upper()
            if subtitle in clean_msg and len(clean_msg) < len(subtitle) + 10:
                # Same message, hide the body to avoid double-rendering identical text
                lines = []
                panel_h = 100 # Minimum height for header-only panel
            else:
                lines = self._word_wrap(msg_text, f_body, scale.w(SCR_W - 80))
                panel_h = max(120, len(lines) * 24 + 100)
            
            panel_rect = scale.rect(SCR_X + 20, cy, SCR_W - 40, panel_h)
            
            # Background with subtle gradient/glow
            bg = pygame.Surface((panel_rect.w, panel_rect.h), pygame.SRCALPHA)
            bg.fill((*PANEL_BG, 230))
            # Subtle top-to-bottom gradient
            for i in range(panel_rect.h):
                alpha = int(230 + 15 * math.sin(i / panel_rect.h * 3.14))
                pygame.draw.line(bg, (*PANEL_BG, min(255, alpha)), (0, i), (panel_rect.w, i))
            surface.blit(bg, panel_rect.topleft)
            
            # Decorative corner accents (tech look)
            aw, ah = scale.w(20), scale.h(3)
            for pos in [panel_rect.topleft, (panel_rect.right - aw, panel_rect.top),
                        (panel_rect.left, panel_rect.bottom - ah), (panel_rect.right - aw, panel_rect.bottom - ah)]:
                pygame.draw.rect(surface, theme_color, (pos[0], pos[1], aw, ah))
            for pos in [panel_rect.topleft, (panel_rect.left, panel_rect.bottom - aw),
                        (panel_rect.right - ah, panel_rect.top), (panel_rect.right - ah, panel_rect.bottom - aw)]:
                pygame.draw.rect(surface, theme_color, (pos[0], pos[1], ah, aw))

            pygame.draw.rect(surface, (*theme_color, 120), panel_rect, 1)
            
            # Subtitle/Header
            txt = f_title.render(subtitle, True, theme_color)
            surface.blit(txt, (panel_rect.x + 25, panel_rect.y + 20))
            pygame.draw.line(surface, (*theme_color, 180), (panel_rect.x + 20, panel_rect.y + 55),
                             (panel_rect.x + panel_rect.w - 20, panel_rect.y + 55), 1)

            # Body text
            ty = panel_rect.y + 75
            for line in lines:
                txt = f_body.render(line, True, TEXT_WHITE)
                surface.blit(txt, (panel_rect.x + 30, ty))
                ty += 24
            
            cy += panel_h + 30

        # Only show Continue button if there's a messagescreen_click button
        has_next = any("messagescreen_click" in b.get("name", "") for b in state.buttons)
        if has_next:
            btn_w = 260
            rect = scale.rect(SCR_X + (SCR_W - btn_w) // 2, cy, btn_w, 48)
            hovered = rect.collidepoint(mouse)
            
            c = ALERT if (msg_text and any(k in msg_text.upper() for k in ("UNAUTHORISED", "CRIMINAL"))) else PRIMARY
            
            # Subtle fill
            fill = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            fill.fill((*c, 60 if hovered else 25))
            surface.blit(fill, rect.topleft)
            
            # Border + corner accents
            pygame.draw.rect(surface, (*c, 140), rect, 1, border_radius=4)
            # Corner accents (tech look)
            cw, ch = scale.w(12), scale.h(12)
            pygame.draw.line(surface, c, rect.topleft, (rect.x + cw, rect.y), 2)
            pygame.draw.line(surface, c, rect.topleft, (rect.x, rect.y + ch), 2)
            pygame.draw.line(surface, c, (rect.right-1, rect.bottom-1), (rect.right - cw, rect.bottom-1), 2)
            pygame.draw.line(surface, c, (rect.right-1, rect.bottom-1), (rect.right-1, rect.bottom - ch), 2)
            
            txt_color = (0, 0, 0) if (hovered and not is_warning) else (TEXT_WHITE if hovered else c)
            if is_warning and hovered:
                txt_color = (255, 255, 255)
            
            txt = f_btn.render("CONTINUE", True, txt_color)
            surface.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))

    def _draw_generic(self, surface, scale, state, cy):
        """Render GenericScreen — file server, company info, console, records, etc."""
        files = state.remote_files
        mouse = pygame.mouse.get_pos()
        subtitle = state.screen_data.get("subtitle", "").lower()

        # Detect screen subtype by button prefixes
        btn_names = [b.get("name", "") for b in state.buttons]
        has_company = any(n.startswith("companyscreen_") for n in btn_names)
        has_records = any(n.startswith("recordscreen_title") for n in btn_names)
        has_security = any(n.startswith("securityscreen_system") for n in btn_names)
        has_console = any(n == "console_typehere" for n in btn_names)

        is_news = "news" in subtitle
        is_file_screen = ("file" in subtitle or "server" in subtitle) and not is_news
        if is_news and state.news:
            self._draw_news(surface, scale, state, cy, mouse)
        elif files and is_file_screen:
            self._draw_file_server(surface, scale, state, cy, files, mouse)
        elif has_records:
            self._draw_records(surface, scale, state, cy)
        elif has_security:
            self._draw_security(surface, scale, state, cy)
        elif has_console:
            self._draw_console(surface, scale, state, cy)
        elif has_company:
            company_buttons = [b for b in state.buttons if b.get("name", "").startswith("companyscreen_")]
            self._draw_company_info(surface, scale, state, cy, company_buttons)
        else:
            # News, Rankings, Software sales, or other
            f_info = get_font(scale.fs(18), light=True)
            sub = state.screen_data.get("subtitle", "Unknown")
            txt = f_info.render(sub, True, TEXT_DIM)
            surface.blit(txt, (scale.x(SCR_X + 10), scale.y(cy)))

    def _draw_news(self, surface, scale, state, cy, mouse):
        """Render News screen — two-panel layout: story list + detail."""
        stories = state.news
        if not stories:
            f = get_font(scale.fs(18), light=True)
            txt = f.render("No news stories available.", True, TEXT_DIM)
            surface.blit(txt, (scale.x(SCR_X + 10), scale.y(cy)))
            return

        f_head = get_font(scale.fs(16))
        f_date = get_font(scale.fs(13), light=True)
        f_preview = get_font(scale.fs(13), light=True)
        f_body = get_font(scale.fs(15), light=True)
        f_header = get_font(scale.fs(14))

        list_w = 550
        detail_x = SCR_X + list_w + 30
        detail_w = SCR_W - list_w - 30

        # Header
        txt = f_header.render("N E W S   F E E D", True, PRIMARY)
        surface.blit(txt, (scale.x(SCR_X + 10), scale.y(cy)))
        cy += 28

        # Story list (left panel)
        row_h = 48
        max_vis = min(14, len(stories))
        visible = stories[self._scroll:self._scroll + max_vis]
        for i, story in enumerate(visible):
            idx = self._scroll + i
            y = cy + i * row_h
            rect = scale.rect(SCR_X, y, list_w, row_h - 2)
            hovered = rect.collidepoint(mouse)
            selected = idx == self._news_selected

            # Row background
            if selected:
                s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                s.fill((*PRIMARY, 35))
                surface.blit(s, rect.topleft)
            elif hovered:
                s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                s.fill((*PRIMARY, 15))
                surface.blit(s, rect.topleft)
            elif i % 2 == 1:
                s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                s.fill((180, 210, 255, 15))
                surface.blit(s, rect.topleft)

            pygame.draw.rect(surface, (*SECONDARY, 60), rect, 1)

            # Date
            date = story.get("date", "")
            txt = f_date.render(date, True, TEXT_DIM)
            surface.blit(txt, (rect.x + scale.w(8), rect.y + scale.h(4)))

            # Headline
            headline = story.get("headline", "")[:60]
            color = TEXT_WHITE if (selected or hovered) else PRIMARY
            txt = f_head.render(headline, True, color)
            surface.blit(txt, (rect.x + scale.w(8), rect.y + scale.h(20)))

        # Detail panel (right side)
        panel_rect = scale.rect(detail_x, cy, detail_w, max_vis * row_h)
        bg = pygame.Surface((panel_rect.w, panel_rect.h), pygame.SRCALPHA)
        bg.fill((*PANEL_BG, 160))
        surface.blit(bg, panel_rect.topleft)
        pygame.draw.rect(surface, SECONDARY, panel_rect, 1)

        if self._news_selected >= 0 and self._news_selected < len(stories):
            story = stories[self._news_selected]
            # Headline
            txt = f_head.render(story.get("headline", ""), True, PRIMARY)
            surface.blit(txt, (panel_rect.x + scale.w(12), panel_rect.y + scale.h(10)))
            # Date
            txt = f_date.render(story.get("date", ""), True, SECONDARY)
            surface.blit(txt, (panel_rect.x + scale.w(12), panel_rect.y + scale.h(30)))
            # Separator
            sep_y = panel_rect.y + scale.h(48)
            pygame.draw.line(surface, SECONDARY, (panel_rect.x + 10, sep_y),
                             (panel_rect.x + panel_rect.w - 10, sep_y), 1)
            # Body text with word wrap
            details = story.get("details", "")
            if details:
                lines = []
                for para in details.split("\n"):
                    if not para.strip():
                        lines.append("")
                        continue
                    words = para.split()
                    line = ""
                    for w in words:
                        test = f"{line} {w}".strip()
                        if f_body.size(test)[0] > panel_rect.w - scale.w(24):
                            lines.append(line)
                            line = w
                        else:
                            line = test
                    if line:
                        lines.append(line)
                ty = sep_y + scale.h(10)
                for line in lines:
                    if ty > panel_rect.y + panel_rect.h - scale.h(20):
                        break
                    if line == "":
                        ty += scale.h(8)
                        continue
                    txt = f_body.render(line, True, TEXT_WHITE)
                    surface.blit(txt, (panel_rect.x + scale.w(12), ty))
                    ty += scale.h(20)
        else:
            f = get_font(scale.fs(16), light=True)
            txt = f.render("Select a story to read", True, TEXT_DIM)
            cx = panel_rect.centerx - txt.get_width() // 2
            cy_mid = panel_rect.centery - txt.get_height() // 2
            surface.blit(txt, (cx, cy_mid))

    def _draw_records(self, surface, scale, state, cy):
        """Render Records screen from recordscreen_title/value buttons."""
        f_title = get_font(scale.fs(18))
        f_value = get_font(scale.fs(18), light=True)
        f_header = get_font(scale.fs(15))
        f_btn = get_font(scale.fs(16))
        mouse = pygame.mouse.get_pos()

        # Parse title/value pairs
        records = {}
        for b in state.buttons:
            name = b.get("name", "")
            cap = b.get("caption", "").strip()
            if name.startswith("recordscreen_title "):
                idx = name.split()[-1]
                records.setdefault(idx, {})["title"] = cap
            elif name.startswith("recordscreen_value "):
                idx = name.split()[-1]
                records.setdefault(idx, {})["value"] = cap

        # Header
        txt = f_header.render("DATABASE RECORD VIEW", True, PRIMARY)
        surface.blit(txt, (scale.x(SCR_X + 20), scale.y(cy - 4)))
        cy += 28
        pygame.draw.line(surface, (*SECONDARY, 150), (scale.x(SCR_X + 15), scale.y(cy)),
                         (scale.x(SCR_X + SCR_W - 15), scale.y(cy)), 1)
        cy += 15

        # Render as rows
        sorted_indices = sorted(records.keys(), key=int)
        for i, idx in enumerate(sorted_indices):
            r = records[idx]
            title = r.get("title", "").upper()
            value = r.get("value", "")

            row_rect = scale.rect(SCR_X + 15, cy, SCR_W - 30, 42)
            hovered = row_rect.collidepoint(mouse)

            # Row background
            fill_alpha = 180 if hovered else (100 if i % 2 == 0 else 40)
            fill_col = ROW_HOVER if hovered else ROW_ALT
            bg = pygame.Surface((row_rect.w, row_rect.h), pygame.SRCALPHA)
            bg.fill((*fill_col, fill_alpha))
            surface.blit(bg, row_rect.topleft)
            
            if hovered:
                pygame.draw.rect(surface, PRIMARY, row_rect, 1, border_radius=2)
            else:
                pygame.draw.rect(surface, (*SECONDARY, 60), row_rect, 1, border_radius=2)

            # Title on left
            txt = f_title.render(title, True, TEXT_WHITE if hovered else SECONDARY)
            surface.blit(txt, (row_rect.x + 20, row_rect.y + (row_rect.h - txt.get_height()) // 2))
            
            # Value right-ish
            txt = f_value.render(value, True, TEXT_WHITE if hovered else PRIMARY)
            surface.blit(txt, (scale.x(SCR_X + 340), row_rect.y + (row_rect.h - txt.get_height()) // 2))
            cy += 48

        # Prev/Next/Close buttons in a horizontal row
        cy += 25
        # Center the button group
        total_bw = 3 * 160 - 20
        bx = SCR_X + (SCR_W - total_bw) // 2
        
        for label, bname_prefix in [("< PREV", "recordscreen_scrollleft"),
                                     ("NEXT >", "recordscreen_scrollright"),
                                     ("CLOSE", "recordscreen_click")]:
            btn = next((b for b in state.buttons if bname_prefix in b.get("name", "")), None)
            if btn:
                bw = 140
                rect = scale.rect(bx, cy, bw, 38)
                hovered = rect.collidepoint(mouse)
                
                # Stylized button
                if hovered:
                    pygame.draw.rect(surface, PRIMARY, rect, 0, border_radius=4)
                    txt = f_btn.render(label, True, (0, 0, 0))
                else:
                    pygame.draw.rect(surface, SECONDARY, rect, 1, border_radius=4)
                    txt = f_btn.render(label, True, PRIMARY)
                
                surface.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))
                bx += 160
            else:
                # Still advance bx to maintain centering if some buttons are missing
                bx += 160

    def _draw_security(self, surface, scale, state, cy):
        """Render Security status screen."""
        f_title = get_font(scale.fs(18))
        f_value = get_font(scale.fs(16), light=True)

        # Parse security systems
        systems = {}
        for b in state.buttons:
            name = b.get("name", "")
            cap = b.get("caption", "").strip()
            if name.startswith("securityscreen_systemtitle "):
                idx = name.split()[-1]
                systems.setdefault(idx, {})["title"] = cap
            elif name.startswith("securityscreen_systemlevel "):
                idx = name.split()[-1]
                systems.setdefault(idx, {})["level"] = cap

        if not systems:
            txt = f_value.render("No security systems installed", True, TEXT_DIM)
            surface.blit(txt, (scale.x(SCR_X + 20), scale.y(cy)))
            return

        for idx in sorted(systems.keys(), key=int):
            sys_info = systems[idx]
            title = sys_info.get("title", "Unknown")
            level = sys_info.get("level", "?")

            row_rect = scale.rect(SCR_X + 10, cy, SCR_W - 20, TAB_H)
            bg = pygame.Surface((row_rect.w, row_rect.h), pygame.SRCALPHA)
            bg.fill((255, 255, 255, 8))
            surface.blit(bg, row_rect.topleft)

            txt = f_title.render(title, True, PRIMARY)
            surface.blit(txt, (scale.x(SCR_X + 20), scale.y(cy + 8)))
            txt = f_value.render(level, True, SUCCESS)
            surface.blit(txt, (scale.x(SCR_X + 400), scale.y(cy + 8)))
            cy += TAB_H + 4

    def _draw_console(self, surface, scale, state, cy):
        """Render Console screen with interactive command prompt."""
        f_header = get_font(scale.fs(14))
        f_prompt = get_font(scale.fs(16))
        f_output = get_font(scale.fs(15), light=True)

        # Console prompt prefix
        prompt_prefix = "root@uplink:/# "
        for b in state.buttons:
            if b.get("name", "") == "console_typehere":
                cap = b.get("caption", "").strip()
                if cap and cap.endswith(">"):
                    prompt_prefix = "REMOTE_ACCESS@SYSTEM:~# "

        # Terminal header bar
        header_rect = scale.rect(SCR_X + 10, cy - 2, SCR_W - 20, 24)
        pygame.draw.rect(surface, (15, 25, 35), header_rect, border_top_left_radius=4, border_top_right_radius=4)
        pygame.draw.rect(surface, (*SECONDARY, 150), header_rect, 1, border_top_left_radius=4, border_top_right_radius=4)
        
        txt = f_header.render("REMOTE TERMINAL SESSION [CONNECTED]", True, PRIMARY)
        surface.blit(txt, (header_rect.x + 10, header_rect.y + 4))
        
        # Small decorative dots/buttons in corner (like window controls)
        for i, col in enumerate([ALERT, WARNING, SUCCESS]):
            pygame.draw.circle(surface, col, (header_rect.right - 15 - i * 14, header_rect.centery), 3)

        cy += 22

        # Render terminal-style background with scanlines
        term_h = 520
        term_rect = scale.rect(SCR_X + 10, cy, SCR_W - 20, term_h)
        pygame.draw.rect(surface, (2, 8, 12), term_rect, border_bottom_left_radius=4, border_bottom_right_radius=4)
        pygame.draw.rect(surface, (*SECONDARY, 100), term_rect, 1, border_bottom_left_radius=4, border_bottom_right_radius=4)
        
        # Subtle terminal glow
        glow = pygame.Surface((term_rect.w, term_rect.h), pygame.SRCALPHA)
        for i in range(12):
            alpha = int(12 * (1 - i/12))
            pygame.draw.rect(glow, (*SUCCESS, alpha), (i, i, term_rect.w - 2*i, term_rect.h - 2*i), 1, border_radius=4)
        surface.blit(glow, term_rect.topleft)

        # Console output lines
        out_y = cy + 20
        # Only show last ~24 lines to fit in the terminal
        outputs = [b for b in state.buttons if b.get("name", "").startswith("console_") 
                   and b.get("name", "") not in ("console_typehere", "console_post", "console_title")]
        outputs = outputs[-24:]

        for b in outputs:
            cap = b.get("caption", "").strip()
            if cap:
                # Highlight different types of output
                is_cmd = any(cap.startswith(p) for p in (">", "/", "./"))
                is_error = any(k in cap.upper() for k in ("ERROR", "DENIED", "FAILED", "INVALID"))
                col = ALERT if is_error else (TEXT_WHITE if is_cmd else SUCCESS)
                
                txt = f_output.render(cap.upper(), True, col)
                surface.blit(txt, (scale.x(SCR_X + 30), scale.y(out_y)))
                out_y += 20

        # Interactive prompt at bottom
        prompt_y = cy + term_h - 45
        if not self._console_input:
            self._console_input = TextInput(SCR_X + 30, prompt_y, SCR_W - 70, STATUSBAR_H,
                                            placeholder="ENTER COMMAND...", size=16)
            self._console_input.focused = True

        # Draw prompt prefix
        txt = f_prompt.render(prompt_prefix, True, SUCCESS)
        prefix_w = txt.get_width() + 10
        surface.blit(txt, (scale.x(SCR_X + 30), scale.y(prompt_y + 6)))

        # Position input after prefix
        self._console_input.dx = SCR_X + 30 + int(prefix_w / scale.factor)
        self._console_input.dy = prompt_y
        self._console_input.dw = SCR_W - 80 - int(prefix_w / scale.factor)
        
        # Override text input rendering for console style (no box, just text + cursor)
        old_draw = self._console_input.draw
        def console_input_draw(surface, scale):
            rect = self._console_input.get_rect(scale)
            font = get_font(scale.fs(self._console_input.size))
            if self._console_input.text:
                txt = font.render(self._console_input.text.upper(), True, TEXT_WHITE)
            else:
                txt = font.render(self._console_input.placeholder, True, (60, 140, 120))
            surface.blit(txt, (rect.x, rect.y + (rect.h - txt.get_height()) // 2))
            
            # Custom terminal cursor (block)
            if self._console_input.focused and (time.time() * 2) % 2 < 1:
                cx = rect.x + font.size(self._console_input.text[:self._console_input.cursor_pos].upper())[0]
                pygame.draw.rect(surface, SUCCESS, (cx, rect.y + 6, scale.w(10), rect.h - 12))

        self._console_input.draw = console_input_draw
        self._console_input.draw(surface, scale)
        self._console_input.draw = old_draw  # Restore to avoid side effects


    def _draw_lan(self, surface, scale, state, cy):
        """Render LAN topology as a node graph with Wireless LAN Receiver welcome."""
        lan = state.lan_data
        systems = lan.get("systems", [])
        links = lan.get("links", [])
        mouse = pygame.mouse.get_pos()
        f_title = get_font(scale.fs(22))
        f_info = get_font(scale.fs(15))
        f_info_sm = get_font(scale.fs(13), light=True)

        if not systems:
            # Wireless LAN Receiver Scanning Screen
            HackerPanel(SCR_X + 20, cy, SCR_W - 40, 400, title="Wireless LAN Receiver", color=PRIMARY).draw(surface, scale)
            txt = f_title.render("SCANNING FOR SIGNALS...", True, PRIMARY)
            surface.blit(txt, (scale.x(SCR_X + SCR_W // 2) - txt.get_width() // 2, scale.y(cy + 150)))
            # Animated pulse
            pulse = (math.sin(time.time() * 5) + 1) / 2
            pygame.draw.circle(surface, (*PRIMARY, int(100 * (1-pulse))), (scale.x(SCR_X + SCR_W // 2), scale.y(cy + 170)), scale.w(50 + 100 * pulse), 2)
            return

        # LAN view area
        lan_x = SCR_X + 20
        lan_y = cy + 40
        lan_w = SCR_W - 40
        lan_h = 520

        # Header for LAN
        txt = f_title.render("WIRELESS LAN RECEIVER", True, PRIMARY)
        surface.blit(txt, (scale.x(lan_x), scale.y(cy)))
        
        # Signal Strength Meter
        sig_x = lan_x + lan_w - 220
        Label("SIGNAL:", 14, SECONDARY, True).draw(surface, scale, sig_x, cy + 6)
        for i in range(5):
            h = 6 + i * 4
            col = SUCCESS if i < 4 else (30, 60, 40)
            pygame.draw.rect(surface, col, scale.rect(sig_x + 65 + i * 10, cy + 22 - h, 6, h))

        # Background panel
        lan_rect = scale.rect(lan_x, lan_y, lan_w, lan_h)
        pygame.draw.rect(surface, (2, 5, 10), lan_rect, border_radius=4)
        pygame.draw.rect(surface, (*SECONDARY, 100), lan_rect, 1, border_radius=4)
        
        # Decorative grid
        for gx in range(0, lan_w, 50):
            pygame.draw.line(surface, (10, 20, 30), (scale.x(lan_x + gx), scale.y(lan_y)), (scale.x(lan_x + gx), scale.y(lan_y + lan_h)))
        for gy in range(0, lan_h, 50):
            pygame.draw.line(surface, (10, 20, 30), (scale.x(lan_x), scale.y(lan_y + gy)), (scale.x(lan_x + lan_w), scale.y(lan_y + gy)))

        # System type icons/colors
        TYPE_COLORS = {
            "Router": (43, 170, 255),        # cyan
            "Hub": (30, 98, 168),             # blue
            "Terminal": (140, 170, 200),      # light gray
            "MainServer": WARNING,     # gold
            "MailServer": (43, 255, 209),     # teal
            "FileServer": (43, 255, 209),     # teal
            "Authentication": (211, 26, 26),  # red
            "Lock": (211, 26, 26),            # red
            "IsolationBridge": (255, 100, 50),# orange
            "Modem": (100, 200, 100),         # green
            "LogServer": (180, 140, 255),     # purple
        }
        
        # Scale system positions
        min_x = min(s.get("x", 0) for s in systems)
        max_x = max(s.get("x", 1) for s in systems)
        min_y = min(s.get("y", 0) for s in systems)
        max_y = max(s.get("y", 1) for s in systems)
        range_x = max(max_x - min_x, 1)
        range_y = max(max_y - min_y, 1)

        def sys_pos(sys):
            nx = (sys.get("x", 0) - min_x) / range_x
            ny = (sys.get("y", 0) - min_y) / range_y
            nx = 0.1 + nx * 0.8
            ny = 0.1 + ny * 0.8
            return lan_rect.x + int(nx * lan_rect.w), lan_rect.y + int(ny * lan_rect.h)

        # Draw links
        sys_by_idx = {s.get("index", i): s for i, s in enumerate(systems)}
        for link in links:
            from_sys = sys_by_idx.get(link.get("from"))
            to_sys = sys_by_idx.get(link.get("to"))
            if from_sys and to_sys:
                p1 = sys_pos(from_sys)
                p2 = sys_pos(to_sys)
                sec = link.get("security", 0)
                color = ALERT if sec > 1 else (SECONDARY if sec == 1 else (30, 55, 80))
                pygame.draw.line(surface, color, p1, p2, 2 if sec > 0 else 1)

        # Draw systems
        f_label = get_font(scale.fs(11))
        node_radius = scale.w(14)
        for i, sys in enumerate(systems):
            if not sys.get("visible", 1): continue
            sx, sy = sys_pos(sys)
            type_name = sys.get("typeName", "unknown")
            color = TYPE_COLORS.get(type_name, SECONDARY)
            
            dist = ((mouse[0] - sx)**2 + (mouse[1] - sy)**2)**0.5
            hovered = dist < node_radius + 5
            selected = sys.get("index", i) == getattr(self, '_lan_selected', -1)

            if hovered or selected:
                glow_r = node_radius * (1.5 if hovered else 1.3)
                s = pygame.Surface((glow_r*2, glow_r*2), pygame.SRCALPHA)
                pygame.draw.circle(s, (*color, 60 if hovered else 30), (glow_r, glow_r), glow_r)
                surface.blit(s, (sx - glow_r, sy - glow_r))

            # Draw stylized node
            pygame.draw.circle(surface, (10, 15, 25), (sx, sy), node_radius)
            pygame.draw.circle(surface, color, (sx, sy), node_radius, 2)
            pygame.draw.circle(surface, color, (sx, sy), scale.w(4))
            
            # Type Label
            txt = f_label.render(type_name.upper(), True, TEXT_WHITE if hovered else TEXT_DIM)
            surface.blit(txt, (sx - txt.get_width() // 2, sy + node_radius + 4))

        # Selected system info panel
        if getattr(self, '_lan_selected', -1) >= 0:
            sel_sys = sys_by_idx.get(self._lan_selected)
            if sel_sys:
                info_y = lan_y + lan_h + 15
                type_name = sel_sys.get("typeName", "unknown")
                sec = sel_sys.get("security", 0)
                screen_idx = sel_sys.get("screenIndex", -1)
                color = TYPE_COLORS.get(type_name, SECONDARY)

                # Info card
                rect = scale.rect(lan_x, info_y, 400, 60)
                pygame.draw.rect(surface, (15, 25, 40, 180), rect, border_radius=4)
                pygame.draw.rect(surface, color, rect, 1, border_radius=4)
                
                txt = f_info.render(type_name.upper(), True, color)
                surface.blit(txt, (rect.x + 15, rect.y + 10))
                txt = f_info_sm.render(f"SECURITY LEVEL: {sec}   NODE INDEX: {sel_sys.get('index')}", True, TEXT_DIM)
                surface.blit(txt, (rect.x + 15, rect.y + 35))

                if screen_idx >= 0:
                    btn_rect = scale.rect(lan_x + lan_w - 180, info_y + 10, 160, 40)
                    btn_hover = btn_rect.collidepoint(mouse)
                    pygame.draw.rect(surface, PRIMARY if btn_hover else SECONDARY, btn_rect, 0 if btn_hover else 1, border_radius=4)
                    f_btn = get_font(scale.fs(16))
                    txt = f_btn.render("CONNECT TO NODE", True, (0, 0, 0) if btn_hover else PRIMARY)
                    surface.blit(txt, (btn_rect.centerx - txt.get_width() // 2, btn_rect.centery - txt.get_height() // 2))

    def _draw_company_info(self, surface, scale, state, cy, buttons):
        """Render company information from companyscreen_ buttons."""
        f_title = get_font(scale.fs(18))
        f_body = get_font(scale.fs(15), light=True)
        f_label = get_font(scale.fs(12), light=True)
        f_header = get_font(scale.fs(14))

        # Parse company info from button names/captions
        roles = {}  # role -> {title, name, email, tel}
        for b in buttons:
            name = b.get("name", "")
            cap = b.get("caption", "").strip()
            if not cap: continue
            
            prefix = "companyscreen_"
            if not name.startswith(prefix): continue
            field = name[len(prefix):]
            
            # Determine role (md, admin, ceo, etc.)
            role = "other"
            for r in ("md", "admin", "ceo", "cto", "cfo", "publicity"):
                if field.startswith(r):
                    role = r
                    field = field[len(r):]
                    break
            
            roles.setdefault(role, {})
            if field == "title": roles[role]["title"] = cap
            elif field == "email": roles[role]["email"] = cap
            elif field == "tel": roles[role]["tel"] = cap
            elif field == "" or field == "name": roles[role]["name"] = cap

        # Draw cards in 2 columns if there's enough space
        card_w = (SCR_W - 40) // 2
        card_h = 95
        gutter = 20
        
        # Sort roles: CEO/MD first
        role_order = ["ceo", "md", "cto", "cfo", "admin", "publicity", "other"]
        sorted_roles = sorted(roles.keys(), key=lambda r: role_order.index(r) if r in role_order else 99)

        # Header
        txt = f_header.render("CORPORATE DIRECTORY", True, SECONDARY)
        surface.blit(txt, (scale.x(SCR_X + 20), scale.y(cy - 4)))
        cy += 24
        pygame.draw.line(surface, (*SECONDARY, 150), (scale.x(SCR_X + 15), scale.y(cy)), 
                         (scale.x(SCR_X + SCR_W - 15), scale.y(cy)), 1)
        cy += 15

        for i, role in enumerate(sorted_roles):
            info = roles[role]
            col = i % 2
            row = i // 2
            rx = SCR_X + 15 + col * (card_w + gutter)
            ry = cy + row * (card_h + gutter)
            
            rect = scale.rect(rx, ry, card_w, card_h)
            mouse = pygame.mouse.get_pos()
            hovered = rect.collidepoint(mouse)
            
            # Card background with gradient-like fill
            bg = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            bg.fill((15, 25, 40, 210 if hovered else 160))
            surface.blit(bg, rect.topleft)
            pygame.draw.rect(surface, PRIMARY if hovered else (*SECONDARY, 80), rect, 1, border_radius=2)
            
            # Left accent bar
            accent_col = PRIMARY if role in ("ceo", "md") else SECONDARY
            pygame.draw.rect(surface, accent_col, (rect.x, rect.y, scale.w(4), rect.h))
            
            # Avatar placeholder - more refined person icon
            avatar_r = scale.rect(rx + 15, ry + 15, 52, 52)
            pygame.draw.rect(surface, (25, 35, 50), avatar_r, border_radius=4)
            pygame.draw.rect(surface, (*SECONDARY, 40), avatar_r, 1, border_radius=4)
            
            # Person silhouette
            head_r = scale.w(7)
            pygame.draw.circle(surface, (accent_col if hovered else SECONDARY), (avatar_r.centerx, avatar_r.y + scale.h(18)), head_r)
            # Body curve
            body_pts = [(avatar_r.x + scale.w(12), avatar_r.bottom - scale.h(10)),
                        (avatar_r.x + scale.w(12), avatar_r.bottom - scale.h(18)),
                        (avatar_r.centerx, avatar_r.bottom - scale.h(22)),
                        (avatar_r.right - scale.w(12), avatar_r.bottom - scale.h(18)),
                        (avatar_r.right - scale.w(12), avatar_r.bottom - scale.h(10))]
            pygame.draw.lines(surface, (accent_col if hovered else SECONDARY), False, body_pts, 2)

            # Info text
            tx = rx + 82
            title = info.get("title", role.upper()).upper()
            txt = f_label.render(title, True, accent_col)
            surface.blit(txt, (scale.x(tx), scale.y(ry + 15)))
            
            name = info.get("name", "REDACTED")
            txt = f_title.render(name, True, TEXT_WHITE)
            surface.blit(txt, (scale.x(tx), scale.y(ry + 34)))
            
            email = info.get("email", "")
            if email:
                txt = f_body.render(email, True, (160, 190, 220))
                surface.blit(txt, (scale.x(tx), scale.y(ry + 60)))
            
            tel = info.get("tel", "")
            if tel:
                # Phone icon or just label
                txt = f_body.render(f"TEL: {tel}", True, TEXT_DIM)
                surface.blit(txt, (scale.x(rx + card_w - txt.get_width() / scale.factor - 15), scale.y(ry + 15)))

    def _draw_file_server(self, surface, scale, state, cy, files, mouse):
        f_header = get_font(scale.fs(16))
        f_row = get_font(scale.fs(15), light=True)
        f_small = get_font(scale.fs(13), light=True)
        max_vis = 16
        row_h = 40

        # Column header background
        head_rect = scale.rect(SCR_X + 10, cy - 4, SCR_W - 20, TAB_H)
        bg = pygame.Surface((head_rect.w, head_rect.h), pygame.SRCALPHA)
        bg.fill((*PANEL_BG, 120))
        surface.blit(bg, head_rect.topleft)
        pygame.draw.rect(surface, SECONDARY, head_rect, 1, border_radius=2)

        # Column headers
        headers = [("FILENAME", 25), ("SIZE", 420), ("ENCRYPTION", 560), ("COMPRESSION", 720)]
        for h, hx in headers:
            txt = f_header.render(h, True, PRIMARY)
            surface.blit(txt, (scale.x(SCR_X + hx), head_rect.y + (head_rect.h - txt.get_height()) // 2))
        
        cy += 42

        visible = files[self._scroll:self._scroll + max_vis]
        for i, f in enumerate(visible):
            y = cy + i * row_h
            if y > 940:
                break
            row_rect = scale.rect(SCR_X + 10, y, SCR_W - 20, row_h - 4)
            hovered = row_rect.collidepoint(mouse)

            # Row background
            if hovered:
                sel = pygame.Surface((row_rect.w, row_rect.h), pygame.SRCALPHA)
                sel.fill((*ROW_HOVER, 200))
                surface.blit(sel, row_rect.topleft)
                pygame.draw.rect(surface, PRIMARY, row_rect, 1, border_radius=2)
            elif i % 2 == 1:
                alt = pygame.Surface((row_rect.w, row_rect.h), pygame.SRCALPHA)
                alt.fill((*ROW_ALT, 100))
                surface.blit(alt, row_rect.topleft)

            color = TEXT_WHITE if hovered else TEXT_DIM
            
            # Filename
            txt = f_row.render(f["title"][:40].upper(), True, color)
            surface.blit(txt, (scale.x(SCR_X + 25), row_rect.y + (row_rect.h - txt.get_height()) // 2))
            
            # Size
            txt = f_row.render(f"{f['size']} GQ", True, TEXT_WHITE if hovered else TEXT_DIM)
            surface.blit(txt, (scale.x(SCR_X + 420), row_rect.y + (row_rect.h - txt.get_height()) // 2))
            
            # Encrypted
            if f.get("encrypted"):
                txt = f_row.render("LEVEL " + str(f["encrypted"]), True, ALERT)
                surface.blit(txt, (scale.x(SCR_X + 560), row_rect.y + (row_rect.h - txt.get_height()) // 2))
            else:
                txt = f_row.render("NONE", True, (60, 80, 100))
                surface.blit(txt, (scale.x(SCR_X + 560), row_rect.y + (row_rect.h - txt.get_height()) // 2))
                
            # Compressed
            if f.get("compressed"):
                txt = f_row.render("LEVEL " + str(f["compressed"]), True, SUCCESS)
                surface.blit(txt, (scale.x(SCR_X + 720), row_rect.y + (row_rect.h - txt.get_height()) // 2))
            else:
                txt = f_row.render("NONE", True, (60, 80, 100))
                surface.blit(txt, (scale.x(SCR_X + 720), row_rect.y + (row_rect.h - txt.get_height()) // 2))

        # Scroll indicator
        if len(files) > max_vis:
            bottom_y = cy + max_vis * row_h + 10
            txt = f_small.render(f"FILES {self._scroll + 1}-{min(self._scroll + max_vis, len(files))} OF {len(files)}", True, TEXT_DIM)
            surface.blit(txt, (scale.x(SCR_X + 20), scale.y(bottom_y)))

    def _draw_log_viewer(self, surface, scale, state, cy, logs, mouse):
        f_header = get_font(scale.fs(16))
        f_row = get_font(scale.fs(14), light=True)
        f_small = get_font(scale.fs(13), light=True)
        max_vis = 18
        row_h = TAB_H

        # Column header background
        head_rect = scale.rect(SCR_X + 10, cy - 4, SCR_W - 20, TAB_H)
        bg = pygame.Surface((head_rect.w, head_rect.h), pygame.SRCALPHA)
        bg.fill((*PANEL_BG, 120))
        surface.blit(bg, head_rect.topleft)
        pygame.draw.rect(surface, SECONDARY, head_rect, 1, border_radius=2)

        # Column headers
        headers = [("DATE/TIME", 25), ("SOURCE IP", 200), ("USER ID", 380), ("ACTION/EVENT", 540)]
        for h, hx in headers:
            txt = f_header.render(h, True, PRIMARY)
            surface.blit(txt, (scale.x(SCR_X + hx), head_rect.y + (head_rect.h - txt.get_height()) // 2))
        
        cy += 42

        visible = logs[self._scroll:self._scroll + max_vis]
        for i, log in enumerate(visible):
            y = cy + i * row_h
            if y > 940:
                break
            row_rect = scale.rect(SCR_X + 10, y, SCR_W - 20, row_h - 4)
            hovered = row_rect.collidepoint(mouse)

            # Row background
            if hovered:
                sel = pygame.Surface((row_rect.w, row_rect.h), pygame.SRCALPHA)
                sel.fill((*ROW_HOVER, 200))
                surface.blit(sel, row_rect.topleft)
                pygame.draw.rect(surface, PRIMARY, row_rect, 1, border_radius=2)
            elif i % 2 == 1:
                alt = pygame.Surface((row_rect.w, row_rect.h), pygame.SRCALPHA)
                alt.fill((*ROW_ALT, 100))
                surface.blit(alt, row_rect.topleft)

            # Default color
            color = TEXT_WHITE if hovered else TEXT_DIM
            
            # Suspicious logs in yellow/red
            sus = log.get("suspicious", 0)
            if sus > 0:
                color = ALERT if sus >= 2 else WARNING

            # Date
            txt = f_row.render(log.get("date", "")[:18], True, color)
            surface.blit(txt, (scale.x(SCR_X + 25), row_rect.y + (row_rect.h - txt.get_height()) // 2))
            
            # From IP
            txt = f_row.render(log.get("from_ip", "")[:18], True, color)
            surface.blit(txt, (scale.x(SCR_X + 200), row_rect.y + (row_rect.h - txt.get_height()) // 2))
            
            # User
            txt = f_row.render(log.get("from_name", "")[:14].upper(), True, color)
            surface.blit(txt, (scale.x(SCR_X + 380), row_rect.y + (row_rect.h - txt.get_height()) // 2))
            
            # Action
            txt = f_row.render(log.get("data1", "")[:35].upper(), True, color)
            surface.blit(txt, (scale.x(SCR_X + 540), row_rect.y + (row_rect.h - txt.get_height()) // 2))

        # Scroll indicator
        if len(logs) > max_vis:
            bottom_y = cy + max_vis * row_h + 10
            txt = f_small.render(f"LOGS {self._scroll + 1}-{min(self._scroll + max_vis, len(logs))} OF {len(logs)}", True, TEXT_DIM)
            surface.blit(txt, (scale.x(SCR_X + 20), scale.y(bottom_y)))


    # ================================================================
    # CONTEXT MENU (right-click)
    # ================================================================

    def _draw_context_menu(self, surface, scale):
        if not self._ctx_menu:
            return
        x, y = self._ctx_pos
        f = get_font(scale.fs(15))
        mouse = pygame.mouse.get_pos()
        menu_w = scale.w(180)
        item_h = scale.h(28)
        menu_h = len(self._ctx_menu) * item_h + 4

        # Background
        bg = pygame.Surface((menu_w, menu_h), pygame.SRCALPHA)
        bg.fill((15, 25, 40, 240))
        surface.blit(bg, (x, y))
        pygame.draw.rect(surface, PRIMARY, (x, y, menu_w, menu_h), 1)

        for i, (label, action) in enumerate(self._ctx_menu):
            iy = y + 2 + i * item_h
            item_rect = pygame.Rect(x + 1, iy, menu_w - 2, item_h)
            hovered = item_rect.collidepoint(mouse)
            if hovered:
                pygame.draw.rect(surface, (*PRIMARY, 60), item_rect)
            txt = f.render(label, True, TEXT_WHITE if hovered else PRIMARY)
            surface.blit(txt, (x + 10, iy + 4))

    def _start_operation(self, op_type, label, duration, on_complete):
        """Start a timed operation (file copy, log delete, etc.)."""
        import time
        self._operation = {
            "type": op_type,
            "label": label,
            "start": time.time(),
            "duration": duration,
            "on_complete": on_complete,
            "done": False,
        }

    def _draw_operation(self, surface, scale):
        """Draw active operation progress bar. Returns True if operation is active."""
        if not self._operation:
            return False
        import time
        op = self._operation
        elapsed = time.time() - op["start"]
        progress = min(1.0, elapsed / op["duration"])

        # Progress bar at bottom of content area
        bar_y = 900
        bar_x = SCR_X + 100
        bar_w = SCR_W - 200
        bar_h = 20

        # Background panel
        panel_rect = scale.rect(bar_x - 10, bar_y - 30, bar_w + 20, 70)
        bg = pygame.Surface((panel_rect.w, panel_rect.h), pygame.SRCALPHA)
        bg.fill((11, 21, 32, 230))
        surface.blit(bg, panel_rect.topleft)
        pygame.draw.rect(surface, SECONDARY, panel_rect, 1)

        # Label
        f = get_font(scale.fs(14), light=True)
        pct_text = f"{int(progress * 100)}%"
        txt = f.render(f"{op['label']}  {pct_text}", True, PRIMARY)
        surface.blit(txt, (scale.x(bar_x), scale.y(bar_y - 22)))

        # Bar
        bg_rect = scale.rect(bar_x, bar_y, bar_w, bar_h)
        pygame.draw.rect(surface, (20, 35, 50), bg_rect)
        fill_rect = scale.rect(bar_x, bar_y, int(bar_w * progress), bar_h)
        pygame.draw.rect(surface, PRIMARY, fill_rect)
        pygame.draw.rect(surface, SECONDARY, bg_rect, 1)

        # Complete
        if progress >= 1.0 and not op["done"]:
            op["done"] = True
            op["on_complete"]()
            audio.play_sfx("success")
            self._operation = None

        return True

    # ================================================================
    # EVENT HANDLING (connected)
    # ================================================================

    def _handle_screen_event(self, event, scale, state):
        st = state.screen_type
        sd = state.screen_data

        # Context menu click
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self._ctx_menu:
            mx, my = event.pos
            f = get_font(scale.fs(15))
            menu_w = scale.w(180)
            item_h = scale.h(28)
            cx, cy_m = self._ctx_pos
            for i, (label, action) in enumerate(self._ctx_menu):
                iy = cy_m + 2 + i * item_h
                item_rect = pygame.Rect(cx + 1, iy, menu_w - 2, item_h)
                if item_rect.collidepoint(event.pos):
                    action()
                    self._ctx_menu = None
                    return
            # Click outside menu — close it
            self._ctx_menu = None
            return

        # Console input
        if self._console_input and st in ("GenericScreen", "unknown"):
            has_console = any(b.get("name", "") == "console_typehere" for b in state.buttons)
            if has_console:
                r = self._console_input.handle_event(event, scale)
                if r == "submit":
                    cmd_text = self._console_input.text.strip()
                    if cmd_text:
                        self.net.set_field("console_typehere", cmd_text)
                        self.net.send_key(13)  # Enter
                        self._console_input.text = ""
                        self._console_input.cursor_pos = 0
                        self.net.request_state()
                        audio.play_sfx("popup")
                    return

        # News story click
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and state.news:
            subtitle_lower = sd.get("subtitle", "").lower()
            if "news" in subtitle_lower:
                # Compute cy to match _draw_screen → _draw_generic → _draw_news
                # Title is always shown for News Server, subtitle suppressed for GenericScreen
                news_cy = CONTENT_Y + 46 + 24 + 28  # title + separator + "NEWS FEED" header
                row_h = 48
                max_vis = min(14, len(state.news))
                for i in range(max_vis):
                    idx = self._scroll + i
                    y = news_cy + i * row_h
                    rect = scale.rect(SCR_X, y, 550, row_h - 2)
                    if rect.collidepoint(event.pos):
                        self._news_selected = idx
                        return

        # Scroll wheel for file/log/news lists
        if event.type == pygame.MOUSEBUTTONDOWN and st in ("GenericScreen", "unknown", "LogScreen"):
            if st == "LogScreen":
                items = state.remote_logs
                max_items = 22
            else:
                items = state.remote_files
                max_items = 20
            if event.button == 4:  # scroll up
                self._scroll = max(0, self._scroll - 1)
                return
            elif event.button == 5:  # scroll down
                self._scroll = min(max(0, len(items) - max_items), self._scroll + 1)
                return

        # Right-click context menu on files/logs
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3 and st in ("GenericScreen", "unknown", "LogScreen"):
            files = state.remote_files if st != "LogScreen" else []
            logs = state.remote_logs if st == "LogScreen" else []
            # Compute content_y
            ctx_cy = CONTENT_Y
            mt_val = sd.get("maintitle", "")
            sub_val = sd.get("subtitle", "")
            if mt_val: ctx_cy += 46
            if sub_val: ctx_cy += TAB_H
            ctx_cy += 24 + 26 + 6  # separator + headers

            if files:
                visible = files[self._scroll:self._scroll + 20]
                for i, f in enumerate(visible):
                    y = ctx_cy + i * 28
                    row_rect = scale.rect(SCR_X, y, SCR_W, 26)
                    if row_rect.collidepoint(event.pos):
                        title = f["title"]
                        size = f.get("size", 1)
                        encrypted = f.get("encrypted", 0)
                        sb = getattr(self, 'sidebar', None)
                        has_copier = sb and sb.is_running("File_Copier")
                        has_decrypter = sb and sb.is_running("Decrypter")
                        # Copy time: ~1s per GQ, min 0.5s
                        copy_dur = max(0.5, size * 1.0)
                        del_dur = max(0.3, size * 0.2)
                        decrypt_dur = max(1.0, encrypted * 2.0)
                        self._ctx_pos = event.pos
                        self._ctx_menu = []
                        if has_copier:
                            self._ctx_menu.append(
                                ("Copy to Gateway", lambda t=title, d=copy_dur: self._start_operation(
                                    "copy", f"Copying {t}...", d,
                                    lambda: (self.net.copy_file(t), self.net.get_files()))))
                        else:
                            self._ctx_menu.append(
                                ("Copy (need File_Copier)", lambda: (
                                    self.statusbar.show("Run File_Copier first"), audio.play_sfx("error"))))
                        if encrypted and has_decrypter:
                            self._ctx_menu.append(
                                ("Decrypt File", lambda t=title, d=decrypt_dur: self._start_operation(
                                    "decrypt", f"Decrypting {t}...", d,
                                    lambda: (self.statusbar.show(f"Decrypted: {t}"), self.net.get_files()))))
                        elif encrypted:
                            self._ctx_menu.append(
                                ("Decrypt (need Decrypter)", lambda: (
                                    self.statusbar.show("Run Decrypter first"), audio.play_sfx("error"))))
                        self._ctx_menu.append(
                            ("Delete File", lambda t=title, d=del_dur: self._start_operation(
                                "delete", f"Deleting {t}...", d,
                                lambda: (self.net.delete_file(t), self.net.get_files()))))
                        return
            elif logs:
                n_logs = len(logs)
                # Delete all logs: ~0.3s per log, min 1s
                del_all_dur = max(1.0, n_logs * 0.3)
                visible = logs[self._scroll:self._scroll + 22]
                for i, log in enumerate(visible):
                    y = ctx_cy + i * 26
                    row_rect = scale.rect(SCR_X, y, SCR_W, 24)
                    if row_rect.collidepoint(event.pos):
                        self._ctx_pos = event.pos
                        has_log_deleter = hasattr(self, 'sidebar') and self.sidebar and self.sidebar.is_running("Log_Deleter")
                        log_idx = self._scroll + i
                        if has_log_deleter:
                            self._ctx_menu = [
                                ("Delete This Log", lambda idx=log_idx: self._start_operation(
                                    "delete_log", f"Deleting log entry...", 1.5,
                                    lambda: (self.net.delete_logs(), self.net.get_logs()))),
                                ("Delete All Logs", lambda d=del_all_dur: self._start_operation(
                                    "delete_logs", f"Deleting {n_logs} logs...", d,
                                    lambda: (self.net.delete_logs(), self.net.get_logs()))),
                            ]
                        else:
                            self._ctx_menu = [
                                ("Delete This Log", lambda: (self.statusbar.show("Run Log_Deleter first"), audio.play_sfx("error"))),
                                ("Delete All Logs", lambda d=del_all_dur: self._start_operation(
                                    "delete_logs", f"Deleting {n_logs} logs...", d,
                                    lambda: (self.net.delete_logs(), self.net.get_logs()))),
                                ("Modify Log", lambda: (self.statusbar.show("Requires Log_Modifier software"), audio.play_sfx("error"))),
                            ]
                        return

        # LinksScreen or InterNIC menu search input
        if st == "LinksScreen":
            self._search_input.handle_event(event, scale)
        elif st == "MenuScreen":
            sd = state.screen_data
            mt = sd.get("maintitle", "").lower()
            sub = sd.get("subtitle", "").lower()
            if "internic" in mt or "internic" in sub:
                r = self._search_input.handle_event(event, scale)
                # Check for "GO" button click or Enter key
                if r == "submit" or (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
                    # For mouse click, we need to check the rect. 
                    # Instead of re-calculating cy, we check if r == "submit" (Enter) 
                    # OR if we clicked in the general area where GO button is.
                    # This is safe because we only do this if it's the InterNIC screen.
                    should_submit = (r == "submit")
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        # Estimate GO button area: SCR_X+630, cy-2. 
                        # SCR_X is ~510. SCR_X+630 is ~1140.
                        mx, my = event.pos
                        if scale.x(SCR_X + 630) <= mx <= scale.x(SCR_X + 710) and scale.y(150) <= my <= scale.y(250):
                            should_submit = True
                    
                    if should_submit:
                        q = self._search_input.text.strip()
                        if q:
                            self.net.set_field("internic_search_input", q)
                            self.net.send_key(13)
                            self.net.request_state()
                            audio.play_sfx("popup")
                        return

        # Password input
        if st in ("PasswordScreen", "UserIDScreen") and self._pw_input:
            if self._user_input:
                r = self._user_input.handle_event(event, scale)
                if r == "tab":
                    self._user_input.focused = False
                    self._pw_input.focused = True
                    return
            r = self._pw_input.handle_event(event, scale)
            if r == "submit":
                self._submit_password(st)
                return
            elif r == "tab" and self._user_input:
                self._pw_input.focused = False
                self._user_input.focused = True
                return

        # Keyboard shortcuts for server screens
        if event.type == pygame.KEYDOWN:
            # Escape: disconnect
            if event.key == pygame.K_ESCAPE:
                self.net.server_disconnect()
                self._mode = "bookmarks"
                self._operation = None
                self._cracking = False
                self.net.get_links()
                audio.play_sfx("short_whoosh6")
                return
            # Backspace: back
            if event.key == pygame.K_BACKSPACE and st not in ("PasswordScreen", "UserIDScreen"):
                self.net.back()
                audio.play_sfx("short_whoosh6")
                return
            # Enter/Return: Continue (MessageScreen) or OK (DialogScreen)
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                if st == "MessageScreen":
                    for btn in state.buttons:
                        if "messagescreen_click" in btn.get("name", ""):
                            self.net.send({"cmd": "click", "button": btn["name"]}, refresh_state=True)
                            audio.play_sfx("popup")
                            return
                elif st == "DialogScreen":
                    self.net.dialog_ok()
                    audio.play_sfx("popup")
                    return
            # 1-9: select menu option
            if st in ("MenuScreen", "HighSecurityScreen"):
                if pygame.K_1 <= event.key <= pygame.K_9:
                    idx = event.key - pygame.K_1
                    options = sd.get("options", [])
                    if idx < len(options):
                        self.net.menu_select(idx)
                        audio.play_sfx("popup")
                    return
            # P: Run Password Breaker
            if event.key == pygame.K_p and st in ("PasswordScreen", "UserIDScreen"):
                if not self._cracking:
                    import time as _t
                    self._cracking = True
                    self._crack_start = _t.time()
                    self._crack_user = ""
                    self._crack_pass = ""
                    self.net.crack_password()
                return

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return

        # Back arrow
        back_r = scale.rect(BACK_X, CONTENT_Y + 5, 40, 40)
        if back_r.collidepoint(event.pos):
            self.net.back()
            audio.play_sfx("short_whoosh6")
            return

        # Disconnect button
        disc_r = scale.rect(SCR_X + SCR_W - 120, CONTENT_Y, 120, 32)
        if disc_r.collidepoint(event.pos):
            self.net.server_disconnect()
            self._mode = "bookmarks"
            self._operation = None
            self._cracking = False
            self.net.get_links()
            audio.play_sfx("short_whoosh6")
            return

        # Calculate content Y after title (must match _draw_screen logic)
        cy = CONTENT_Y
        mt = sd.get("maintitle", "")
        sub = sd.get("subtitle", "")
        remote_ip = state.player.get("remotehost", "")
        server_name = ""
        for lk in state.links:
            if lk.get("ip") == remote_ip:
                server_name = lk.get("name", "")
                break
        # Match _draw_screen title logic
        if (mt and mt not in ("Uplink", "uplink")) or server_name or sub:
            cy += 46  # display_title always shown
        display_sub = sub if (mt and mt not in ("Uplink", "uplink")) or server_name else ""
        if display_sub:
            cy += TAB_H
        cy += 24  # separator (14) + post-separator (10)

        if st == "MenuScreen" or st == "HighSecurityScreen":
            options = sd.get("options", [])
            for i, opt in enumerate(options):
                y = cy + i * 54
                rect = scale.rect(SCR_X + 10, y, SCR_W - 20, 48)
                if rect.collidepoint(event.pos):
                    self.net.menu_select(i)
                    audio.play_sfx("popup")
                    return

        elif st == "DialogScreen":
            # Handle TextInput events
            for name, inp in self._dialog_inputs.items():
                r = inp.handle_event(event, scale)
                if r == "submit":
                    self.net.set_field(name, inp.text)
                    self.net.dialog_ok()
                    return
                elif r == "tab":
                    inp.focused = False
                    # Focus next input
                    names = list(self._dialog_inputs.keys())
                    idx = (names.index(name) + 1) % len(names)
                    self._dialog_inputs[names[idx]].focused = True
                    return
                elif r: # text changed
                    self.net.set_field(name, inp.text)

            if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
                return

            # Match drawing logic for button positions
            form_w = 500
            form_x = SCR_X + (SCR_W - form_w) // 2
            f_body = get_font(scale.fs(16), light=True)
            
            # Use same bank-detection logic as _draw_dialog
            widgets = sd.get("widgets", [])
            is_bank = any("bank" in w.get("caption", "").lower() for w in widgets) or "bank" in sd.get("subtitle", "").lower()
            
            btn_cy = cy + (42 if is_bank else 20)
            for w in widgets:
                cap = w.get("caption", "")
                wname = w.get("name", "")
                wtype = w.get("type", 1)
                if not cap and wtype not in (3, 4): continue

                if wtype in (1, 2, 9):
                    lines = self._word_wrap(cap, f_body, scale.w(form_w))
                    btn_cy += len(lines) * 22 + 8
                elif wtype in (3, 4):
                    btn_cy += 68
                elif wtype in (5, 7, 8):
                    btn_w = 220
                    rect = scale.rect(form_x + (form_w - btn_w) // 2, btn_cy, btn_w, 40)
                    if rect.collidepoint(event.pos):
                        for iname, inp in self._dialog_inputs.items():
                            self.net.set_field(iname, inp.text)
                        self.net.send({"cmd": "click", "button": wname}, refresh_state=True)
                        audio.play_sfx("popup")
                        return
                    btn_cy += 50

            # Optional OK button
            if not any(w.get("type") in (5, 7, 8) for w in widgets):
                btn_w = 160
                rect = scale.rect(form_x + (form_w - btn_w) // 2, btn_cy + 10, btn_w, 40)
                if rect.collidepoint(event.pos):
                    for iname, inp in self._dialog_inputs.items():
                        self.net.set_field(iname, inp.text)
                    self.net.dialog_ok()
                    audio.play_sfx("popup")
                    return

        elif st in ("PasswordScreen", "UserIDScreen"):
            if self._cracking:
                return  # don't handle clicks during crack animation
            # Submit button
            form_x = SCR_X + (SCR_W - 400) // 2
            form_w = 400
            btn_w = 220
            btn_x = form_x + (form_w - btn_w) // 2
            rect = scale.rect(btn_x, cy + 105, btn_w, 44)
            if rect.collidepoint(event.pos):
                self._submit_password(st)
                return
            # "Run Password Breaker" button
            crack_w = 340
            crack_x = form_x + (form_w - crack_w) // 2
            crack_rect = scale.rect(crack_x, cy + 185, crack_w, 42)
            if crack_rect.collidepoint(event.pos):
                import time
                self._cracking = True
                self._crack_start = time.time()
                self._crack_user = ""
                self._crack_pass = ""
                self.net.crack_password()
                audio.play_sfx("short_whoosh6")
                self.statusbar.show("Running Password Breaker...")
                return

        elif st == "MessageScreen":
            # Calculate Continue button position (must match draw code)
            f_body = get_font(scale.fs(18), light=True)
            msg_cy = cy
            msg_text = ""
            for btn in state.buttons:
                cap = btn.get("caption", "").strip()
                if cap and cap not in ("OK", " ", "") and len(cap) > len(msg_text):
                    msg_text = cap
            if msg_text:
                # Same subtitle-deduplication logic as _draw_message
                subtitle = sd.get("subtitle", "MESSAGE").upper()
                clean_msg = msg_text.strip().upper()
                if subtitle in clean_msg and len(clean_msg) < len(subtitle) + 10:
                    lines = []
                else:
                    lines = self._word_wrap(msg_text, f_body, scale.w(SCR_W - 80))
                
                panel_h = max(60, len(lines) * 24 + 100)
                msg_cy += panel_h + 30

            # Only click if there's actually a messagescreen_click button
            btn_w = 260
            rect = scale.rect(SCR_X + (SCR_W - btn_w) // 2, msg_cy, btn_w, 48)
            if rect.collidepoint(event.pos):
                for btn in state.buttons:
                    name = btn.get("name", "")
                    if "messagescreen_click" in name:
                        self.net.send({"cmd": "click", "button": name}, refresh_state=True)
                        audio.play_sfx("popup")
                        return
                # No messagescreen_click button — this is a dead-end message
                # (like ARC Access Terminal). Do nothing.

        elif st == "LinksScreen":
            # Filter same as draw
            links = state.screen_links
            query = self._search_input.text.strip().lower()
            if query:
                links = [l for l in links if query in l.get("name", "").lower() or query in l.get("ip", "").lower()]
            link_cy = cy + 45 + 38
            row_h = 42
            for i, link in enumerate(links):
                y = link_cy + i * row_h
                if y > 980:
                    break
                rect = scale.rect(SCR_X + 10, y, SCR_W - 20, row_h - 4)
                if rect.collidepoint(event.pos):
                    ip = link.get("ip", "")
                    if ip:
                        self.connect_to(ip, link.get("name", ""))
                    return

        elif st in ("GenericScreen", "unknown"):
            # Check if this is a LAN view
            if state.lan_data.get("systems"):
                self._handle_lan_click(event, scale, state, cy)
                return
            # File actions handled by right-click context menu

        elif st == "LanScreen":
            self._handle_lan_click(event, scale, state, cy)
            return

        elif st == "LogScreen":
            pass  # Log actions handled by right-click context menu

    def _handle_lan_click(self, event, scale, state, cy):
        """Handle clicks on the LAN topology view."""
        lan = state.lan_data
        systems = lan.get("systems", [])
        if not systems:
            return

        # Match layout from _draw_lan
        lan_x = SCR_X + 20
        lan_y = cy + 40
        lan_w = SCR_W - 40
        lan_h = 520
        lan_rect = scale.rect(lan_x, lan_y, lan_w, lan_h)
        node_radius = scale.w(14)

        min_x = min(s.get("x", 0) for s in systems)
        max_x = max(s.get("x", 1) for s in systems)
        min_y = min(s.get("y", 0) for s in systems)
        max_y = max(s.get("y", 1) for s in systems)
        range_x = max(max_x - min_x, 1)
        range_y = max(max_y - min_y, 1)

        sys_by_idx = {s.get("index", i): s for i, s in enumerate(systems)}

        # Check for system node selection
        for i, sys in enumerate(systems):
            if not sys.get("visible", 1):
                continue
            nx = (sys.get("x", 0) - min_x) / range_x
            ny = (sys.get("y", 0) - min_y) / range_y
            nx = 0.1 + nx * 0.8
            ny = 0.1 + ny * 0.8
            sx = lan_rect.x + int(nx * lan_rect.w)
            sy = lan_rect.y + int(ny * lan_rect.h)

            dist = ((event.pos[0] - sx) ** 2 + (event.pos[1] - sy) ** 2) ** 0.5
            if dist < node_radius + 5:
                self._lan_selected = sys.get("index", i)
                audio.play_sfx("popup")
                return

        # Check if clicked on CONNECT TO NODE button
        if getattr(self, '_lan_selected', -1) >= 0:
            sel_sys = sys_by_idx.get(self._lan_selected)
            if sel_sys and sel_sys.get("screenIndex", -1) >= 0:
                info_y = lan_y + lan_h + 15
                btn_rect = scale.rect(lan_x + lan_w - 180, info_y + 10, 160, 40)
                if btn_rect.collidepoint(event.pos):
                    self.net.navigate(sel_sys["screenIndex"])
                    audio.play_sfx("login")
                    return

        # Clicked empty space — deselect
        if lan_rect.collidepoint(event.pos):
            self._lan_selected = -1

    def _submit_password(self, st):
        pw = self._pw_input.text if self._pw_input else ""
        user = self._user_input.text if self._user_input and st == "UserIDScreen" else None
        self.net.submit_password(pw, user)
        self._pw_input = None
        self._user_input = None
        audio.play_sfx("login")

    @staticmethod
    def _word_wrap(text, font, max_width):
        words = text.split()
        lines = []
        line = ""
        for word in words:
            test = line + " " + word if line else word
            if font.size(test)[0] > max_width:
                if line:
                    lines.append(line)
                line = word
            else:
                line = test
        if line:
            lines.append(line)
        return lines
