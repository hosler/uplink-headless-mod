"""Login screen: handle + password entry → join."""
import pygame
import time
from ui.theme import PRIMARY, SECONDARY, TEXT_WHITE, TEXT_DIM, PANEL_BG, Scale, get_font, draw_gradient, BG_DARK
from ui.widgets import TextInput, Button, Label, HackerPanel


class LoginScreen:
    def __init__(self, on_join):
        self.on_join = on_join  # callback(handle, password)
        self.handle_input = TextInput(760, 460, 400, 40, placeholder="Agent handle", size=24)
        self.password_input = TextInput(760, 530, 400, 40, placeholder="Password", masked=True, size=24)
        self.handle_input.focused = True
        self.connect_btn = Button("CONNECT", 810, 600, 300, 54, callback=self._submit, color=PRIMARY, size=28)
        self.error_msg = ""
        self.title = Label("U P L I N K", size=84, color=PRIMARY)
        self.subtitle = Label("Neural Interface Access v4.2.0", size=24, color=SECONDARY, light=True)
        self.handle_label = Label("HANDLE", size=18, color=SECONDARY, light=False)
        self.password_label = Label("PASSWORD", size=18, color=SECONDARY, light=False)
        
        # Tech panel for login
        self.panel = HackerPanel(710, 410, 500, 310, title="Secure Login", color=SECONDARY)

    def _submit(self):
        handle = self.handle_input.text.strip()
        if not handle:
            self.error_msg = "Enter a handle"
            return
        self.on_join(handle, self.password_input.text)

    def set_error(self, msg):
        self.error_msg = msg

    def draw(self, surface, scale: Scale):
        draw_gradient(surface)
        
        # Decorative screen corners
        cw, ch = scale.w(60), scale.h(60)
        thick = 2
        # TL
        pygame.draw.line(surface, SECONDARY, (10, 10), (10 + cw, 10), thick)
        pygame.draw.line(surface, SECONDARY, (10, 10), (10, 10 + ch), thick)
        # BR
        pygame.draw.line(surface, SECONDARY, (scale.win_w - 10, scale.win_h - 10), (scale.win_w - 10 - cw, scale.win_h - 10), thick)
        pygame.draw.line(surface, SECONDARY, (scale.win_w - 10, scale.win_h - 10), (scale.win_w - 10, scale.win_h - 10 - ch), thick)

        # Techy background noise (lines)
        for i in range(10):
            y = scale.y(200 + i * 80)
            pygame.draw.line(surface, (15, 25, 35), (0, y), (scale.win_w, y), 1)

        # Panel
        self.panel.draw(surface, scale)

        # Title with pulse effect
        pulse = (time.time() * 2) % 1.0
        glow_alpha = int(40 + 20 * pulse)
        
        # Subtitle
        self.subtitle.draw(surface, scale, 0, 360, align="center", max_w=1920)
        # Main Title
        self.title.draw(surface, scale, 0, 260, align="center", max_w=1920)

        # Labels
        self.handle_label.draw(surface, scale, 760, 432)
        self.password_label.draw(surface, scale, 760, 502)

        # Inputs
        self.handle_input.draw(surface, scale)
        self.password_input.draw(surface, scale)
        self.connect_btn.draw(surface, scale)

        # Status text in corners
        font_tiny = get_font(scale.fs(14))
        status_txt = font_tiny.render("SYSTEM: READY | CONNECTION: ENCRYPTED", True, TEXT_DIM)
        surface.blit(status_txt, (20, scale.win_h - 30))
        
        ver_txt = font_tiny.render("UPLINK HEADLESS MOD v2.0", True, TEXT_DIM)
        surface.blit(ver_txt, (scale.win_w - ver_txt.get_width() - 20, scale.win_h - 30))

        # Error
        if self.error_msg:
            font = get_font(scale.fs(18))
            txt = font.render(self.error_msg.upper(), True, (211, 26, 26))
            cx = scale.x(960) - txt.get_width() // 2
            surface.blit(txt, (cx, scale.y(670)))

    def handle_event(self, event, scale: Scale):
        r = self.handle_input.handle_event(event, scale)
        if r == "submit":
            self.password_input.focused = True
            self.handle_input.focused = False
            return
        if r == "tab":
            self.handle_input.focused = False
            self.password_input.focused = True
            return

        r = self.password_input.handle_event(event, scale)
        if r == "submit":
            self._submit()
            return
        if r == "tab":
            self.password_input.focused = False
            self.handle_input.focused = True
            return

        self.connect_btn.handle_event(event, scale)
