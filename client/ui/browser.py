"""Browser tab: bookmarks, connecting animation, server screen rendering."""
import time
import math
import pygame
from ui.theme import (Scale, get_font, PRIMARY, SECONDARY, ALERT, SUCCESS,
                      TEXT_WHITE, TEXT_DIM, PANEL_BG, TOPBAR_H, TAB_H,
                      STATUSBAR_H, DESIGN_W, DESIGN_H)
from ui.widgets import TextInput, Label
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
        self._search_input = TextInput(SCR_X + 10, 920, 500, 36, placeholder="Search InterNIC...", size=18)
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
        # Active operation (file copy, log delete, etc.)
        self._operation = None      # {type, label, start, duration, on_complete}

        self._crack_user = ""
        self._crack_pass = ""
        self._crack_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"

    def connect_to(self, ip, name=""):
        self._mode = "connecting"
        self._connect_ip = ip
        self._connect_name = name
        self._connect_start = time.time()
        audio.play_sfx("bounce")
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
                self._scroll = 0
                # Clear stale data from previous screen
                state.remote_files = []
                state.remote_logs = []
                state.screen_links = []
                state.lan_data = {}
                self._lan_requested = False
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

        txt = f_title.render("G A T E W A Y", True, PRIMARY)
        surface.blit(txt, (scale.x(SCR_X + 10), scale.y(CONTENT_Y)))
        txt = f_sub.render("Your saved links", True, SECONDARY)
        surface.blit(txt, (scale.x(SCR_X + 10), scale.y(CONTENT_Y + 48)))

        # Separator
        sy = scale.y(CONTENT_Y + 85)
        pygame.draw.line(surface, SECONDARY, (scale.x(SCR_X), sy),
                         (scale.x(SCR_X + SCR_W), sy), max(1, scale.h(2)))

        # Link rows
        links = state.links
        mouse = pygame.mouse.get_pos()
        row_h = 60
        start_y = CONTENT_Y + 100

        for i, link in enumerate(links):
            y = start_y + i * row_h
            if y > 880:
                break
            rect = scale.rect(SCR_X, y, SCR_W, row_h - 4)
            hovered = rect.collidepoint(mouse)

            if hovered:
                glow = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                glow.fill((*PRIMARY, 25))
                surface.blit(glow, rect.topleft)
                pygame.draw.rect(surface, PRIMARY, rect, 1, border_radius=3)

            # Dot
            dot_x = scale.x(SCR_X + 20)
            dot_y = rect.y + rect.h // 2
            pygame.draw.circle(surface, PRIMARY if hovered else SECONDARY, (dot_x, dot_y), scale.w(5))

            # Name
            name = link.get("name", "Unknown")
            txt = f_name.render(name, True, TEXT_WHITE if hovered else PRIMARY)
            surface.blit(txt, (scale.x(SCR_X + 40), rect.y + scale.h(5)))

            # IP
            ip = link.get("ip", "")
            txt = f_ip.render(ip, True, TEXT_DIM)
            surface.blit(txt, (scale.x(SCR_X + 42), rect.y + scale.h(30)))

            # Arrow
            if hovered:
                txt = f_name.render(">", True, PRIMARY)
                surface.blit(txt, (scale.x(SCR_X + SCR_W - 40), rect.y + scale.h(8)))

        # Hint at bottom
        f_hint = get_font(scale.fs(14), light=True)
        txt = f_hint.render("Connect to InterNIC to search for more servers", True, TEXT_DIM)
        surface.blit(txt, (scale.x(SCR_X + 10), scale.y(940)))

    def _handle_bookmarks_event(self, event, scale, state):
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return

        links = state.links
        row_h = 60
        start_y = CONTENT_Y + 100

        for i, link in enumerate(links):
            y = start_y + i * row_h
            if y > 880:
                break
            rect = scale.rect(SCR_X, y, SCR_W, row_h - 4)
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
        f_ip = get_font(scale.fs(40))
        f_name = get_font(scale.fs(20), light=True)

        cx = DESIGN_W // 2
        cy = DESIGN_H // 2 - 60

        txt = f_label.render("Connecting to...", True, TEXT_DIM)
        surface.blit(txt, (scale.x(cx) - txt.get_width() // 2, scale.y(cy)))

        txt = f_ip.render(self._connect_ip, True, PRIMARY)
        surface.blit(txt, (scale.x(cx) - txt.get_width() // 2, scale.y(cy + 40)))

        # Progress bar
        bar_w = 400
        bar_h = 12
        bx = scale.x(cx - bar_w // 2)
        by = scale.y(cy + 100)
        bw = scale.w(bar_w)
        bh = scale.h(bar_h)
        pygame.draw.rect(surface, PANEL_BG, (bx, by, bw, bh))
        fill = int(bw * progress)
        if fill > 0:
            pygame.draw.rect(surface, PRIMARY, (bx, by, fill, bh))
        pygame.draw.rect(surface, SECONDARY, (bx, by, bw, bh), 1)

        # Percentage
        pct = f_label.render(f"{int(progress * 100)}%", True, TEXT_DIM)
        surface.blit(pct, (bx + bw + 10, by - 3))

        if self._connect_name:
            txt = f_name.render(self._connect_name, True, TEXT_DIM)
            surface.blit(txt, (scale.x(cx) - txt.get_width() // 2, scale.y(cy + 140)))

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
        f_arrow = get_font(scale.fs(28))
        txt = f_arrow.render("<", True, TEXT_WHITE if bh else SECONDARY)
        surface.blit(txt, (back_r.x + 8, back_r.y + 2))
        if bh:
            pygame.draw.circle(surface, (*PRIMARY, 30), back_r.center, scale.w(20))

        # Disconnect top-right
        disc_r = scale.rect(SCR_X + SCR_W - 120, CONTENT_Y, 120, 28)
        dh = disc_r.collidepoint(mouse)
        c = ALERT if dh else (80, 20, 20)
        pygame.draw.rect(surface, c, disc_r, 0 if dh else 1, border_radius=3)
        txt = f_small.render("Disconnect", True, (255, 255, 255) if dh else ALERT)
        surface.blit(txt, (disc_r.x + 12, disc_r.y + 5))

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
        if display_sub:
            txt = f_sub.render(display_sub, True, SECONDARY)
            surface.blit(txt, (scale.x(SCR_X + 10), scale.y(cy)))
            cy += 36
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
        options = state.screen_data.get("options", [])
        mouse = pygame.mouse.get_pos()
        for i, opt in enumerate(options):
            y = cy + i * 50
            rect = scale.rect(SCR_X + 10, y, SCR_W - 20, 44)
            hovered = rect.collidepoint(mouse)
            if hovered:
                glow = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                glow.fill((*PRIMARY, 40))
                surface.blit(glow, rect.topleft)
            pygame.draw.rect(surface, PRIMARY if hovered else SECONDARY, rect, 1, border_radius=3)
            # Arrow pointer on left (signature Uplink style)
            arr = f_btn.render(">", True, PRIMARY if hovered else SECONDARY)
            surface.blit(arr, (rect.x + 12, rect.y + (rect.h - arr.get_height()) // 2))
            txt = f_btn.render(opt["caption"], True, TEXT_WHITE if hovered else PRIMARY)
            surface.blit(txt, (rect.x + 36, rect.y + (rect.h - txt.get_height()) // 2))

    def _draw_highsecurity(self, surface, scale, state, cy):
        """Render HighSecurityScreen as security challenge panels."""
        f_title = get_font(scale.fs(20))
        f_label = get_font(scale.fs(16), light=True)
        f_btn = get_font(scale.fs(18))
        mouse = pygame.mouse.get_pos()
        options = state.screen_data.get("options", [])

        # Header
        txt = f_title.render("SECURITY AUTHENTICATION REQUIRED", True, ALERT)
        surface.blit(txt, (scale.x(SCR_X + 10), scale.y(cy)))
        cy += 30

        txt = f_label.render(f"{len(options)} verification steps remaining", True, TEXT_DIM)
        surface.blit(txt, (scale.x(SCR_X + 10), scale.y(cy)))
        cy += 30

        # Challenge icons
        CHALLENGE_ICONS = {
            "password": ("PASS", ALERT),
            "voice": ("VOICE", (43, 255, 209)),
            "cypher": ("CRYPT", (255, 200, 50)),
            "elliptic": ("CRYPT", (255, 200, 50)),
        }

        for i, opt in enumerate(options):
            caption = opt.get("caption", "")
            y = cy + i * 80

            # Panel
            panel_rect = scale.rect(SCR_X + 20, y, SCR_W - 40, 68)
            hovered = panel_rect.collidepoint(mouse)

            bg = pygame.Surface((panel_rect.w, panel_rect.h), pygame.SRCALPHA)
            bg.fill((*ALERT, 15) if hovered else (11, 21, 32, 200))
            surface.blit(bg, panel_rect.topleft)
            border_color = ALERT if hovered else (80, 30, 30)
            pygame.draw.rect(surface, border_color, panel_rect, 1, border_radius=3)

            # Icon
            icon_label = "AUTH"
            icon_color = ALERT
            for key, (lbl, col) in CHALLENGE_ICONS.items():
                if key in caption.lower():
                    icon_label = lbl
                    icon_color = col
                    break

            icon_rect = scale.rect(SCR_X + 30, y + 10, 60, 48)
            pygame.draw.rect(surface, icon_color, icon_rect, 1, border_radius=4)
            f_icon = get_font(scale.fs(14))
            txt = f_icon.render(icon_label, True, icon_color)
            surface.blit(txt, (icon_rect.centerx - txt.get_width() // 2,
                               icon_rect.centery - txt.get_height() // 2))

            # Challenge label
            txt = f_btn.render(caption, True, TEXT_WHITE if hovered else PRIMARY)
            surface.blit(txt, (scale.x(SCR_X + 110), scale.y(y + 12)))

            # Status text
            txt = f_label.render("Click to attempt bypass", True, icon_color if hovered else TEXT_DIM)
            surface.blit(txt, (scale.x(SCR_X + 110), scale.y(y + 38)))

            # Lock icon on right
            f_lock = get_font(scale.fs(24))
            txt = f_lock.render("LOCKED", True, ALERT if not hovered else TEXT_WHITE)
            surface.blit(txt, (scale.x(SCR_X + SCR_W - 130), scale.y(y + 18)))

    def _draw_dialog(self, surface, scale, state, cy):
        f_body = get_font(scale.fs(18), light=True)
        f_btn = get_font(scale.fs(18))
        f_label = get_font(scale.fs(14), light=True)
        mouse = pygame.mouse.get_pos()

        # Widget types: 1=BASIC, 2=CAPTION, 3=TEXTBOX, 4=PASSWORDBOX,
        # 5=NEXTPAGE, 6=IMAGE, 7=IMAGEBUTTON, 8=SCRIPTBUTTON, 9=FIELDVALUE
        CAPTION_TYPES = (1, 2, 9)
        INPUT_TYPES = (3, 4)
        BUTTON_TYPES = (5, 7, 8)

        for w in state.screen_data.get("widgets", []):
            cap = w.get("caption", "")
            wtype = w.get("type", 1)
            if not cap:
                continue

            if wtype in CAPTION_TYPES:
                # Plain text / label
                for line in self._word_wrap(cap, f_body, scale.w(SCR_W - 40)):
                    txt = f_body.render(line, True, TEXT_WHITE)
                    surface.blit(txt, (scale.x(SCR_X + 20), scale.y(cy)))
                    cy += 24
                cy += 4

            elif wtype in INPUT_TYPES:
                # Text input field
                Label(cap, 14, TEXT_DIM, True).draw(surface, scale, SCR_X + 20, cy)
                cy += 18
                rect = scale.rect(SCR_X + 20, cy, 400, 32)
                pygame.draw.rect(surface, PANEL_BG, rect)
                pygame.draw.rect(surface, SECONDARY, rect, 1)
                placeholder = "••••••" if wtype == 4 else cap
                txt = f_label.render(placeholder, True, TEXT_DIM)
                surface.blit(txt, (rect.x + 8, rect.y + 7))
                cy += 40

            elif wtype in BUTTON_TYPES:
                # Clickable button
                btn_w = max(160, f_btn.size(cap)[0] + 40)
                rect = scale.rect(SCR_X + 20, cy, btn_w, 34)
                hovered = rect.collidepoint(mouse)
                if hovered:
                    pygame.draw.rect(surface, PRIMARY, rect, 0, border_radius=3)
                    txt = f_btn.render(cap, True, (0, 0, 0))
                else:
                    pygame.draw.rect(surface, PRIMARY, rect, 1, border_radius=3)
                    txt = f_btn.render(cap, True, PRIMARY)
                surface.blit(txt, (rect.x + 20, rect.y + 6))
                cy += 42

            else:
                # Unknown widget type — render as text
                txt = f_body.render(cap, True, TEXT_DIM)
                surface.blit(txt, (scale.x(SCR_X + 20), scale.y(cy)))
                cy += 24

        # OK button at bottom — centered
        cy += 10
        btn_w = 200
        rect = scale.rect(SCR_X + (SCR_W - btn_w) // 2, cy, btn_w, 42)
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
        f_label = get_font(scale.fs(16), light=True)
        f_btn = get_font(scale.fs(20))
        f_crack = get_font(scale.fs(28))
        f_crack_label = get_font(scale.fs(14), light=True)
        mouse = pygame.mouse.get_pos()

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
                target = admin[0] if admin else creds[0]
                self._crack_user = target.get("name", "")
                self._crack_pass = target.get("password", "")

            # Cycling character animation
            anim_y = cy
            if st == "UserIDScreen" and self._crack_user:
                Label("Username", 14, SECONDARY, True).draw(surface, scale, form_x, anim_y - 10)
                anim_y += 10
                displayed = ""
                for j, ch in enumerate(self._crack_user):
                    char_progress = min(1.0, progress * len(self._crack_user) / max(j + 1, 1))
                    if char_progress >= 1.0:
                        displayed += ch
                    else:
                        displayed += random.choice(self._crack_chars)
                txt = f_crack.render(displayed, True, SUCCESS)
                surface.blit(txt, (scale.x(form_x), scale.y(anim_y)))
                anim_y += 40

            if self._crack_pass:
                Label("Password", 14, SECONDARY, True).draw(surface, scale, form_x, anim_y + 5)
                anim_y += 25
                displayed = ""
                pw_start = 0.3 if st == "UserIDScreen" else 0.0
                pw_progress = max(0, (progress - pw_start) / (1.0 - pw_start))
                for j, ch in enumerate(self._crack_pass):
                    char_progress = min(1.0, pw_progress * len(self._crack_pass) / max(j + 1, 1))
                    if char_progress >= 1.0:
                        displayed += ch
                    else:
                        displayed += random.choice(self._crack_chars)
                txt = f_crack.render(displayed, True, SUCCESS)
                surface.blit(txt, (scale.x(form_x), scale.y(anim_y)))
                anim_y += 50

            # Progress bar
            bar_y = anim_y + 20
            bar_rect = scale.rect(form_x, bar_y, form_w, 6)
            pygame.draw.rect(surface, (20, 35, 50), bar_rect)
            fill_rect = scale.rect(form_x, bar_y, int(form_w * progress), 6)
            pygame.draw.rect(surface, PRIMARY, fill_rect)

            txt = f_crack_label.render("Password Breaker running...", True, PRIMARY)
            surface.blit(txt, (scale.x(form_x), scale.y(bar_y + 12)))

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
            self._pw_input = TextInput(form_x, cy + 40, form_w, 40, placeholder="Password", masked=True, size=22)
            self._pw_input.focused = True
            self._user_input = TextInput(form_x, cy - 10, form_w, 40, placeholder="Username", size=22)
            if st == "UserIDScreen":
                self._user_input.text = "admin"
                self._user_input.cursor_pos = 5

        if st == "UserIDScreen":
            Label("Username", 16, SECONDARY, True).draw(surface, scale, form_x, cy - 28)
            self._user_input.draw(surface, scale)

        Label("Password", 16, SECONDARY, True).draw(surface, scale, form_x, cy + 22)
        self._pw_input.draw(surface, scale)

        # Submit button
        btn_w = 200
        btn_x = form_x + (form_w - btn_w) // 2
        rect = scale.rect(btn_x, cy + 95, btn_w, 38)
        hovered = rect.collidepoint(mouse)
        if hovered:
            pygame.draw.rect(surface, PRIMARY, rect, 0, border_radius=3)
            txt = f_btn.render("Submit", True, (0, 0, 0))
        else:
            pygame.draw.rect(surface, PRIMARY, rect, 1, border_radius=3)
            txt = f_btn.render("Submit", True, PRIMARY)
        surface.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))

        # "Run Password Breaker" button
        crack_y = cy + 160
        crack_w = 280
        crack_x = form_x + (form_w - crack_w) // 2
        crack_rect = scale.rect(crack_x, crack_y, crack_w, 34)
        crack_hovered = crack_rect.collidepoint(mouse)
        crack_color = ALERT if crack_hovered else (120, 30, 30)
        pygame.draw.rect(surface, crack_color, crack_rect, 0 if crack_hovered else 1, border_radius=3)
        f_crack_btn = get_font(scale.fs(16))
        txt = f_crack_btn.render("Run Password Breaker", True, TEXT_WHITE if crack_hovered else ALERT)
        surface.blit(txt, (crack_rect.centerx - txt.get_width() // 2, crack_rect.centery - txt.get_height() // 2))

    def _draw_links(self, surface, scale, state, cy):
        """Render LinksScreen — clickable server list with search filter."""
        f_name = get_font(scale.fs(20))
        f_ip = get_font(scale.fs(14), light=True)
        f_label = get_font(scale.fs(16), light=True)
        mouse = pygame.mouse.get_pos()

        # Search/filter box
        self._search_input.dy = cy - 5
        self._search_input.dx = SCR_X + 550
        self._search_input.dw = 350
        self._search_input.dh = 30
        self._search_input.placeholder = "Filter..."
        self._search_input.size = 16
        self._search_input.draw(surface, scale)
        cy += 35

        # Filter links
        links = state.screen_links
        query = self._search_input.text.strip().lower()
        if query:
            links = [l for l in links if query in l.get("name", "").lower() or query in l.get("ip", "").lower()]

        # Count display
        txt = f_label.render(f"{len(links)} servers", True, TEXT_DIM)
        surface.blit(txt, (scale.x(SCR_X + 10), scale.y(cy - 30)))

        for i, link in enumerate(links):
            y = cy + i * 32
            if y > 960:
                break
            rect = scale.rect(SCR_X + 10, y, SCR_W - 20, 28)
            hovered = rect.collidepoint(mouse)

            # Zebra stripe
            if i % 2 == 1:
                alt = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                alt.fill((180, 210, 255, 20))
                surface.blit(alt, rect.topleft)
            if hovered:
                glow = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                glow.fill((*PRIMARY, 15))
                surface.blit(glow, rect.topleft)

            name = link.get("name", "")
            ip = link.get("ip", "")
            # Server name on left, IP right-aligned on same line
            txt = f_name.render(name[:45], True, TEXT_WHITE if hovered else PRIMARY)
            surface.blit(txt, (rect.x + 10, rect.y + 3))
            txt = f_ip.render(ip, True, SECONDARY if hovered else TEXT_DIM)
            surface.blit(txt, (rect.right - txt.get_width() - 10, rect.y + 5))

    def _draw_message(self, surface, scale, state, cy):
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
            for line in self._word_wrap(msg_text, f_body, scale.w(SCR_W - 40)):
                txt = f_body.render(line, True, TEXT_WHITE)
                surface.blit(txt, (scale.x(SCR_X + 20), scale.y(cy)))
                cy += 22
            cy += 20

        # Only show Continue button if there's a messagescreen_click button
        has_next = any("messagescreen_click" in b.get("name", "") for b in state.buttons)
        if has_next:
            btn_w = 220
            rect = scale.rect(SCR_X + (SCR_W - btn_w) // 2, cy + 10, btn_w, 44)
            hovered = rect.collidepoint(mouse)
            if hovered:
                pygame.draw.rect(surface, PRIMARY, rect, 0, border_radius=4)
                txt = f_btn.render("Continue", True, (0, 0, 0))
            else:
                pygame.draw.rect(surface, PRIMARY, rect, 1, border_radius=4)
                txt = f_btn.render("Continue", True, PRIMARY)
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

        is_file_screen = "file" in subtitle or "server" in subtitle
        if files and is_file_screen:
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

    def _draw_records(self, surface, scale, state, cy):
        """Render Records screen from recordscreen_title/value buttons."""
        f_title = get_font(scale.fs(18))
        f_value = get_font(scale.fs(18), light=True)
        f_label = get_font(scale.fs(13), light=True)
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

        # Render as rows
        for idx in sorted(records.keys(), key=int):
            r = records[idx]
            title = r.get("title", "")
            value = r.get("value", "")

            row_rect = scale.rect(SCR_X + 10, cy, SCR_W - 20, 36)
            bg = pygame.Surface((row_rect.w, row_rect.h), pygame.SRCALPHA)
            bg.fill((255, 255, 255, 8) if int(idx) % 2 == 0 else (0, 0, 0, 0))
            surface.blit(bg, row_rect.topleft)

            txt = f_title.render(title, True, SECONDARY)
            surface.blit(txt, (scale.x(SCR_X + 20), scale.y(cy + 8)))
            txt = f_value.render(value, True, TEXT_WHITE)
            surface.blit(txt, (scale.x(SCR_X + 300), scale.y(cy + 8)))
            cy += 38

        # Prev/Next/Close buttons
        cy += 15
        for label, bname_prefix in [("< Prev", "recordscreen_scrollleft"),
                                     ("Next >", "recordscreen_scrollright"),
                                     ("Close", "recordscreen_click")]:
            btn = next((b for b in state.buttons if bname_prefix in b.get("name", "")), None)
            if btn:
                bw = 100
                rect = scale.rect(SCR_X + 20, cy, bw, 30)
                hovered = rect.collidepoint(mouse)
                color = PRIMARY if hovered else SECONDARY
                pygame.draw.rect(surface, color, rect, 0 if hovered else 1, border_radius=3)
                txt = f_btn.render(label, True, (0, 0, 0) if hovered else color)
                surface.blit(txt, (rect.x + 10, rect.y + 5))
                # Shift x for next button
                # Actually stack them horizontally
        # Redraw horizontally
        # (simplified: just show the record data for now)

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

            row_rect = scale.rect(SCR_X + 10, cy, SCR_W - 20, 36)
            bg = pygame.Surface((row_rect.w, row_rect.h), pygame.SRCALPHA)
            bg.fill((255, 255, 255, 8))
            surface.blit(bg, row_rect.topleft)

            txt = f_title.render(title, True, PRIMARY)
            surface.blit(txt, (scale.x(SCR_X + 20), scale.y(cy + 8)))
            txt = f_value.render(level, True, SUCCESS)
            surface.blit(txt, (scale.x(SCR_X + 400), scale.y(cy + 8)))
            cy += 40

    def _draw_console(self, surface, scale, state, cy):
        """Render Console screen with interactive command prompt."""
        f_prompt = get_font(scale.fs(16))
        f_output = get_font(scale.fs(14), light=True)

        # Console prompt prefix
        prompt_prefix = "/:>"
        for b in state.buttons:
            if b.get("name", "") == "console_typehere":
                cap = b.get("caption", "").strip()
                if cap:
                    prompt_prefix = cap

        # Render terminal-style background
        term_rect = scale.rect(SCR_X + 10, cy, SCR_W - 20, 420)
        pygame.draw.rect(surface, (5, 10, 15), term_rect, border_radius=4)
        pygame.draw.rect(surface, SECONDARY, term_rect, 1, border_radius=4)

        # Console output lines
        out_y = cy + 10
        for b in state.buttons:
            name = b.get("name", "")
            cap = b.get("caption", "").strip()
            if name.startswith("console_") and name not in ("console_typehere", "console_post", "console_title"):
                if cap:
                    txt = f_output.render(cap, True, SUCCESS)
                    surface.blit(txt, (scale.x(SCR_X + 20), scale.y(out_y)))
                    out_y += 18

        # Interactive prompt at bottom
        prompt_y = cy + 380
        if not self._console_input:
            self._console_input = TextInput(SCR_X + 20, prompt_y, SCR_W - 60, 30,
                                            placeholder="Type command...", size=16)
            self._console_input.focused = True

        # Draw prompt prefix
        txt = f_prompt.render(prompt_prefix, True, SUCCESS)
        prefix_w = txt.get_width() + 8
        surface.blit(txt, (scale.x(SCR_X + 20), scale.y(prompt_y + 5)))

        # Position input after prefix
        self._console_input.dx = SCR_X + 20 + int(prefix_w / scale.factor)
        self._console_input.dy = prompt_y
        self._console_input.dw = SCR_W - 60 - int(prefix_w / scale.factor)
        self._console_input.draw(surface, scale)

    def _draw_lan(self, surface, scale, state, cy):
        """Render LAN topology as a node graph."""
        lan = state.lan_data
        systems = lan.get("systems", [])
        links = lan.get("links", [])
        mouse = pygame.mouse.get_pos()

        if not systems:
            f = get_font(scale.fs(16), light=True)
            txt = f.render("No LAN systems detected.", True, TEXT_DIM)
            surface.blit(txt, (scale.x(SCR_X + 20), scale.y(cy)))
            return

        # LAN view area
        lan_x = SCR_X + 20
        lan_y = cy + 10
        lan_w = SCR_W - 40
        lan_h = 550

        # Background panel
        lan_rect = scale.rect(lan_x, lan_y, lan_w, lan_h)
        pygame.draw.rect(surface, (5, 10, 18), lan_rect, border_radius=4)
        pygame.draw.rect(surface, SECONDARY, lan_rect, 1, border_radius=4)

        # System type icons/colors
        TYPE_COLORS = {
            "Router": (43, 170, 255),        # cyan
            "Hub": (30, 98, 168),             # blue
            "Terminal": (140, 170, 200),      # light gray
            "MainServer": (255, 200, 50),     # gold
            "MailServer": (43, 255, 209),     # teal
            "FileServer": (43, 255, 209),     # teal
            "Authentication": (211, 26, 26),  # red
            "Lock": (211, 26, 26),            # red
            "IsolationBridge": (255, 100, 50),# orange
            "Modem": (100, 200, 100),         # green
            "LogServer": (180, 140, 255),     # purple
        }
        TYPE_SHAPES = {
            "Router": "diamond",
            "Hub": "circle",
            "Terminal": "rect",
            "MainServer": "hexagon",
            "MailServer": "circle",
            "FileServer": "circle",
            "Authentication": "triangle",
            "Lock": "triangle",
            "IsolationBridge": "diamond",
            "Modem": "rect",
            "LogServer": "circle",
        }

        # Scale system positions to fit in LAN area
        # Systems have x,y coords from the server
        min_x = min(s.get("x", 0) for s in systems)
        max_x = max(s.get("x", 1) for s in systems)
        min_y = min(s.get("y", 0) for s in systems)
        max_y = max(s.get("y", 1) for s in systems)
        range_x = max(max_x - min_x, 1)
        range_y = max(max_y - min_y, 1)

        def sys_pos(sys):
            nx = (sys.get("x", 0) - min_x) / range_x
            ny = (sys.get("y", 0) - min_y) / range_y
            # Pad to keep nodes away from edges
            nx = 0.08 + nx * 0.84
            ny = 0.08 + ny * 0.84
            sx = lan_rect.x + int(nx * lan_rect.w)
            sy = lan_rect.y + int(ny * lan_rect.h)
            return sx, sy

        # Draw links first (behind nodes)
        f_small = get_font(scale.fs(11), light=True)
        sys_by_idx = {s.get("index", i): s for i, s in enumerate(systems)}
        for link in links:
            from_sys = sys_by_idx.get(link.get("from"))
            to_sys = sys_by_idx.get(link.get("to"))
            if from_sys and to_sys:
                p1 = sys_pos(from_sys)
                p2 = sys_pos(to_sys)
                sec = link.get("security", 0)
                color = ALERT if sec > 0 else (30, 55, 80)
                width = 2 if sec > 0 else 1
                pygame.draw.line(surface, color, p1, p2, width)

        # Draw systems
        f_label = get_font(scale.fs(12))
        f_type = get_font(scale.fs(10), light=True)
        node_radius = scale.w(16)
        self._lan_selected = getattr(self, '_lan_selected', -1)

        for i, sys in enumerate(systems):
            if not sys.get("visible", 1):
                continue
            sx, sy = sys_pos(sys)
            type_name = sys.get("typeName", "unknown")
            color = TYPE_COLORS.get(type_name, SECONDARY)
            shape = TYPE_SHAPES.get(type_name, "circle")

            # Check hover
            dist = ((mouse[0] - sx) ** 2 + (mouse[1] - sy) ** 2) ** 0.5
            hovered = dist < node_radius + 5
            selected = sys.get("index", i) == self._lan_selected

            # Glow for hover/selected
            if hovered or selected:
                glow = pygame.Surface((node_radius * 4, node_radius * 4), pygame.SRCALPHA)
                glow_color = (*color, 50) if hovered else (*PRIMARY, 30)
                pygame.draw.circle(glow, glow_color, (node_radius * 2, node_radius * 2), node_radius * 2)
                surface.blit(glow, (sx - node_radius * 2, sy - node_radius * 2))

            # Draw shape
            r = node_radius
            if shape == "diamond":
                pts = [(sx, sy - r), (sx + r, sy), (sx, sy + r), (sx - r, sy)]
                pygame.draw.polygon(surface, color, pts)
                pygame.draw.polygon(surface, TEXT_WHITE if hovered else SECONDARY, pts, 1)
            elif shape == "hexagon":
                pts = []
                for a in range(6):
                    angle = math.radians(60 * a - 30)
                    pts.append((sx + int(r * math.cos(angle)), sy + int(r * math.sin(angle))))
                pygame.draw.polygon(surface, color, pts)
                pygame.draw.polygon(surface, TEXT_WHITE if hovered else SECONDARY, pts, 1)
            elif shape == "rect":
                rect = pygame.Rect(sx - r + 2, sy - r + 4, (r - 2) * 2, (r - 4) * 2)
                pygame.draw.rect(surface, color, rect)
                pygame.draw.rect(surface, TEXT_WHITE if hovered else SECONDARY, rect, 1)
            elif shape == "triangle":
                pts = [(sx, sy - r), (sx + r, sy + r), (sx - r, sy + r)]
                pygame.draw.polygon(surface, color, pts)
                pygame.draw.polygon(surface, TEXT_WHITE if hovered else SECONDARY, pts, 1)
            else:  # circle
                pygame.draw.circle(surface, color, (sx, sy), r)
                pygame.draw.circle(surface, TEXT_WHITE if hovered else SECONDARY, (sx, sy), r, 1)

            # Label
            label = type_name
            txt = f_label.render(label, True, TEXT_WHITE if hovered else TEXT_DIM)
            surface.blit(txt, (sx - txt.get_width() // 2, sy + r + 4))

            # Security indicator
            sec = sys.get("security", 0)
            if sec > 0:
                txt = f_type.render(f"Sec:{sec}", True, ALERT)
                surface.blit(txt, (sx - txt.get_width() // 2, sy + r + 16))

        # Info panel for selected system
        info_y = lan_y + lan_h + 15
        f_info = get_font(scale.fs(15))
        f_info_sm = get_font(scale.fs(13), light=True)

        if self._lan_selected >= 0:
            sel_sys = sys_by_idx.get(self._lan_selected)
            if sel_sys:
                type_name = sel_sys.get("typeName", "unknown")
                sec = sel_sys.get("security", 0)
                screen_idx = sel_sys.get("screenIndex", -1)
                color = TYPE_COLORS.get(type_name, SECONDARY)

                txt = f_info.render(f"{type_name}", True, color)
                surface.blit(txt, (scale.x(lan_x), scale.y(info_y)))
                txt = f_info_sm.render(f"Security: {sec}   Screen: {screen_idx}", True, TEXT_DIM)
                surface.blit(txt, (scale.x(lan_x + 200), scale.y(info_y + 2)))

                # Navigate button if system has a screen
                if screen_idx >= 0:
                    btn_rect = scale.rect(lan_x + lan_w - 160, info_y - 2, 140, 28)
                    btn_hover = btn_rect.collidepoint(mouse)
                    btn_color = PRIMARY if btn_hover else SECONDARY
                    pygame.draw.rect(surface, btn_color, btn_rect, 0 if btn_hover else 1, border_radius=3)
                    f_btn = get_font(scale.fs(14))
                    txt = f_btn.render("ACCESS", True, (0, 0, 0) if btn_hover else btn_color)
                    surface.blit(txt, (btn_rect.centerx - txt.get_width() // 2, btn_rect.centery - txt.get_height() // 2))

        # Legend
        legend_y = info_y + 30
        f_leg = get_font(scale.fs(12), light=True)
        lx = scale.x(lan_x)
        ly = scale.y(legend_y)
        for type_name, color in [("Router", (43, 170, 255)), ("MainServer", (255, 200, 50)),
                                  ("Authentication", (211, 26, 26)), ("Terminal", (140, 170, 200)),
                                  ("FileServer", (43, 255, 209))]:
            pygame.draw.circle(surface, color, (lx + 5, ly + 6), 4)
            txt = f_leg.render(f"  {type_name}", True, TEXT_DIM)
            surface.blit(txt, (lx + 12, ly))
            lx += txt.get_width() + 24

    def _draw_company_info(self, surface, scale, state, cy, buttons):
        """Render company information from companyscreen_ buttons."""
        f_title = get_font(scale.fs(20))
        f_body = get_font(scale.fs(16), light=True)
        f_label = get_font(scale.fs(13), light=True)

        # Parse company info from button names/captions
        # Pattern: companyscreen_mdtitle, companyscreen_md, companyscreen_mdemail, companyscreen_mdtel
        # Pattern: companyscreen_admintitle, companyscreen_admin, etc.
        roles = {}  # role -> {title, name, email, tel}
        for b in buttons:
            name = b.get("name", "")
            cap = b.get("caption", "").strip()
            if not cap:
                continue
            # Extract role and field
            prefix = "companyscreen_"
            if not name.startswith(prefix):
                continue
            field = name[len(prefix):]
            # Determine role (md, admin, etc.)
            role = ""
            for r in ("md", "admin", "ceo", "cto", "cfo"):
                if field.startswith(r):
                    role = r
                    field = field[len(r):]
                    break
            if not role:
                role = "other"
            if role not in roles:
                roles[role] = {}
            if field == "title" or field == "":
                if field == "":
                    roles[role]["name"] = cap
                else:
                    roles[role]["title"] = cap
            elif field == "email":
                roles[role]["email"] = cap
            elif field == "tel":
                roles[role]["tel"] = cap
            elif not field:
                roles[role]["name"] = cap

        # Render as info cards
        for role, info in roles.items():
            title = info.get("title", role.upper())
            name = info.get("name", "")
            email = info.get("email", "")
            tel = info.get("tel", "")

            # Card background
            card_h = 70
            card_rect = scale.rect(SCR_X + 10, cy, SCR_W - 20, card_h)
            bg = pygame.Surface((card_rect.w, card_rect.h), pygame.SRCALPHA)
            bg.fill((255, 255, 255, 8))
            surface.blit(bg, card_rect.topleft)

            # Title (role)
            txt = f_label.render(title, True, SECONDARY)
            surface.blit(txt, (scale.x(SCR_X + 20), scale.y(cy + 5)))

            # Name
            if name:
                txt = f_title.render(name, True, PRIMARY)
                surface.blit(txt, (scale.x(SCR_X + 20), scale.y(cy + 22)))

            # Email + Tel on right
            rx = SCR_X + 500
            if email:
                txt = f_body.render(email, True, TEXT_DIM)
                surface.blit(txt, (scale.x(rx), scale.y(cy + 10)))
            if tel:
                txt = f_body.render(tel, True, TEXT_DIM)
                surface.blit(txt, (scale.x(rx), scale.y(cy + 32)))

            cy += card_h + 8

    def _draw_file_server(self, surface, scale, state, cy, files, mouse):
        f_header = get_font(scale.fs(16))
        f_row = get_font(scale.fs(15), light=True)
        f_small = get_font(scale.fs(13), light=True)
        max_vis = 20
        row_h = 28

        # Column headers
        headers = [("Filename", 0), ("Size", 500), ("Encrypted", 600), ("Compressed", 730)]
        for h, hx in headers:
            txt = f_header.render(h, True, TEXT_WHITE)
            surface.blit(txt, (scale.x(SCR_X + hx), scale.y(cy)))
        cy += 24
        pygame.draw.line(surface, SECONDARY,
                         (scale.x(SCR_X), scale.y(cy)),
                         (scale.x(SCR_X + SCR_W), scale.y(cy)), max(1, scale.h(1)))
        cy += 6

        visible = files[self._scroll:self._scroll + max_vis]
        for i, f in enumerate(visible):
            y = cy + i * row_h
            row_rect = scale.rect(SCR_X, y, SCR_W, row_h - 2)
            hovered = row_rect.collidepoint(mouse)

            # Alternating rows
            if i % 2 == 1:
                alt = pygame.Surface((row_rect.w, row_rect.h), pygame.SRCALPHA)
                alt.fill((255, 255, 255, 8))
                surface.blit(alt, row_rect.topleft)
            if hovered:
                sel = pygame.Surface((row_rect.w, row_rect.h), pygame.SRCALPHA)
                sel.fill((*PRIMARY, 20))
                surface.blit(sel, row_rect.topleft)

            color = TEXT_WHITE if hovered else (140, 170, 200)
            txt = f_row.render(f["title"][:40], True, color)
            surface.blit(txt, (scale.x(SCR_X + 4), scale.y(y + 4)))
            txt = f_row.render(f"{f['size']} GQ", True, TEXT_DIM)
            surface.blit(txt, (scale.x(SCR_X + 500), scale.y(y + 4)))
            if f.get("encrypted"):
                txt = f_row.render("Level " + str(f["encrypted"]), True, ALERT)
                surface.blit(txt, (scale.x(SCR_X + 600), scale.y(y + 4)))
            if f.get("compressed"):
                txt = f_row.render("Level " + str(f["compressed"]), True, SECONDARY)
                surface.blit(txt, (scale.x(SCR_X + 730), scale.y(y + 4)))

            # Right-click hint
            if hovered:
                txt = f_small.render("Right-click for actions", True, TEXT_DIM)
                surface.blit(txt, (scale.x(SCR_X + SCR_W - 180), scale.y(y + 6)))

        # Scroll indicator
        bottom_y = cy + min(len(visible), max_vis) * row_h + 4
        if len(files) > max_vis:
            txt = f_small.render(f"{self._scroll + 1}-{min(self._scroll + max_vis, len(files))} of {len(files)} files", True, TEXT_DIM)
            surface.blit(txt, (scale.x(SCR_X), scale.y(bottom_y)))

        # Context menu
        self._draw_context_menu(surface, scale)

    def _draw_log_viewer(self, surface, scale, state, cy, logs, mouse):
        f_header = get_font(scale.fs(16))
        f_row = get_font(scale.fs(14), light=True)
        f_small = get_font(scale.fs(13), light=True)
        max_vis = 22
        row_h = 26

        # Column headers
        headers = [("Date", 0), ("From IP", 200), ("User", 400), ("Action", 560)]
        for h, hx in headers:
            txt = f_header.render(h, True, TEXT_WHITE)
            surface.blit(txt, (scale.x(SCR_X + hx), scale.y(cy)))
        cy += 22
        pygame.draw.line(surface, SECONDARY,
                         (scale.x(SCR_X), scale.y(cy)),
                         (scale.x(SCR_X + SCR_W), scale.y(cy)), max(1, scale.h(1)))
        cy += 4

        visible = logs[self._scroll:self._scroll + max_vis]
        for i, log in enumerate(visible):
            y = cy + i * row_h
            row_rect = scale.rect(SCR_X, y, SCR_W, row_h - 2)
            hovered = row_rect.collidepoint(mouse)

            if i % 2 == 1:
                alt = pygame.Surface((row_rect.w, row_rect.h), pygame.SRCALPHA)
                alt.fill((255, 255, 255, 8))
                surface.blit(alt, row_rect.topleft)
            if hovered:
                sel = pygame.Surface((row_rect.w, row_rect.h), pygame.SRCALPHA)
                sel.fill((*PRIMARY, 20))
                surface.blit(sel, row_rect.topleft)

            color = TEXT_WHITE if hovered else (140, 170, 200)
            # Suspicious logs in yellow/red
            sus = log.get("suspicious", 0)
            if sus > 0:
                color = ALERT if sus >= 2 else (255, 200, 50)

            txt = f_row.render(log.get("date", "")[:18], True, color)
            surface.blit(txt, (scale.x(SCR_X + 4), scale.y(y + 4)))
            txt = f_row.render(log.get("from_ip", "")[:18], True, color)
            surface.blit(txt, (scale.x(SCR_X + 200), scale.y(y + 4)))
            txt = f_row.render(log.get("from_name", "")[:14], True, color)
            surface.blit(txt, (scale.x(SCR_X + 400), scale.y(y + 4)))
            txt = f_row.render(log.get("data1", "")[:30], True, color)
            surface.blit(txt, (scale.x(SCR_X + 560), scale.y(y + 4)))

            if hovered:
                txt = f_small.render("Right-click", True, TEXT_DIM)
                surface.blit(txt, (scale.x(SCR_X + SCR_W - 100), scale.y(y + 6)))

        # Scroll indicator
        bottom_y = cy + min(len(visible), max_vis) * row_h + 4
        if len(logs) > max_vis:
            txt = f_small.render(f"{self._scroll + 1}-{min(self._scroll + max_vis, len(logs))} of {len(logs)} logs", True, TEXT_DIM)
            surface.blit(txt, (scale.x(SCR_X), scale.y(bottom_y)))

        # Context menu
        self._draw_context_menu(surface, scale)

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

        # Scroll wheel for file/log lists
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
            if sub_val: ctx_cy += 36
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

        # LinksScreen search input
        if st == "LinksScreen":
            self._search_input.handle_event(event, scale)

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

        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return

        # Back arrow
        back_r = scale.rect(BACK_X, CONTENT_Y + 5, 40, 40)
        if back_r.collidepoint(event.pos):
            self.net.back()
            audio.play_sfx("short_whoosh6")
            return

        # Disconnect button
        disc_r = scale.rect(SCR_X + SCR_W - 120, CONTENT_Y, 120, 28)
        if disc_r.collidepoint(event.pos):
            self.net.server_disconnect()
            self._mode = "bookmarks"
            self._operation = None
            self._cracking = False
            self.net.get_links()
            audio.play_sfx("short_whoosh6")
            return

        # Calculate content Y after title
        cy = CONTENT_Y
        mt = sd.get("maintitle", "")
        sub = sd.get("subtitle", "")
        if mt: cy += 46
        if sub: cy += 36
        cy += 24  # separator + padding

        if st == "MenuScreen" or st == "HighSecurityScreen":
            options = sd.get("options", [])
            for i, opt in enumerate(options):
                y = cy + i * 50
                rect = scale.rect(SCR_X + 10, y, SCR_W - 20, 44)
                if rect.collidepoint(event.pos):
                    self.net.menu_select(i)
                    audio.play_sfx("popup")
                    return

        elif st == "DialogScreen":
            # Find OK button position (after all text)
            f_body = get_font(scale.fs(18), light=True)
            ok_y = cy
            for w in sd.get("widgets", []):
                cap = w.get("caption", "")
                if cap:
                    lines = self._word_wrap(cap, f_body, scale.w(SCR_W - 40))
                    ok_y += len(lines) * 24 + 8
            rect = scale.rect(SCR_X + 300, ok_y + 10, 160, 40)
            if rect.collidepoint(event.pos):
                self.net.dialog_ok()
                audio.play_sfx("popup")
                return

        elif st in ("PasswordScreen", "UserIDScreen"):
            if self._cracking:
                return  # don't handle clicks during crack animation
            # Submit button
            form_x = SCR_X + (SCR_W - 400) // 2
            form_w = 400
            btn_w = 200
            btn_x = form_x + (form_w - btn_w) // 2
            rect = scale.rect(btn_x, cy + 95, btn_w, 38)
            if rect.collidepoint(event.pos):
                self._submit_password(st)
                return
            # "Run Password Breaker" button
            crack_w = 280
            crack_x = form_x + (form_w - crack_w) // 2
            crack_rect = scale.rect(crack_x, cy + 160, crack_w, 34)
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
            # Calculate Continue button position (same as draw)
            f_body = get_font(scale.fs(18), light=True)
            msg_cy = cy
            msg_text = ""
            for btn in state.buttons:
                cap = btn.get("caption", "").strip()
                if cap and cap not in ("OK", " ", "") and len(cap) > len(msg_text):
                    msg_text = cap
            if msg_text:
                lines = self._word_wrap(msg_text, f_body, scale.w(SCR_W - 40))
                msg_cy += len(lines) * 22 + 20

            # Only click if there's actually a messagescreen_click button
            btn_w = 220
            rect = scale.rect(SCR_X + (SCR_W - btn_w) // 2, msg_cy + 10, btn_w, 44)
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
            link_cy = cy + 35  # after search box
            for i, link in enumerate(links):
                y = link_cy + i * 32
                if y > 960:
                    break
                rect = scale.rect(SCR_X + 10, y, SCR_W - 20, 28)
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

        # Same layout constants as _draw_lan
        lan_x = SCR_X + 20
        lan_y = cy + 10
        lan_w = SCR_W - 40
        lan_h = 550
        lan_rect = scale.rect(lan_x, lan_y, lan_w, lan_h)
        node_radius = scale.w(16)

        min_x = min(s.get("x", 0) for s in systems)
        max_x = max(s.get("x", 1) for s in systems)
        min_y = min(s.get("y", 0) for s in systems)
        max_y = max(s.get("y", 1) for s in systems)
        range_x = max(max_x - min_x, 1)
        range_y = max(max_y - min_y, 1)

        # Check if clicked on ACCESS button
        if self._lan_selected >= 0:
            sys_by_idx = {s.get("index", i): s for i, s in enumerate(systems)}
            sel_sys = sys_by_idx.get(self._lan_selected)
            if sel_sys and sel_sys.get("screenIndex", -1) >= 0:
                info_y = lan_y + lan_h + 15
                btn_rect = scale.rect(lan_x + lan_w - 160, info_y - 2, 140, 28)
                if btn_rect.collidepoint(event.pos):
                    self.net.navigate(sel_sys["screenIndex"])
                    audio.play_sfx("popup")
                    return

        # Check if clicked on a system node
        for i, sys in enumerate(systems):
            if not sys.get("visible", 1):
                continue
            nx = (sys.get("x", 0) - min_x) / range_x
            ny = (sys.get("y", 0) - min_y) / range_y
            nx = 0.08 + nx * 0.84
            ny = 0.08 + ny * 0.84
            sx = lan_rect.x + int(nx * lan_rect.w)
            sy = lan_rect.y + int(ny * lan_rect.h)

            dist = ((event.pos[0] - sx) ** 2 + (event.pos[1] - sy) ** 2) ** 0.5
            if dist < node_radius + 5:
                self._lan_selected = sys.get("index", i)
                audio.play_sfx("popup")
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
