"""Login screen: handle + password entry → join."""
import pygame
from ui.theme import PRIMARY, SECONDARY, TEXT_WHITE, TEXT_DIM, PANEL_BG, Scale, get_font, draw_gradient
from ui.widgets import TextInput, Button, Label


class LoginScreen:
    def __init__(self, on_join):
        self.on_join = on_join  # callback(handle, password)
        self.handle_input = TextInput(760, 460, 400, 40, placeholder="Agent handle", size=24)
        self.password_input = TextInput(760, 530, 400, 40, placeholder="Password", masked=True, size=24)
        self.handle_input.focused = True
        self.connect_btn = Button("CONNECT", 860, 600, 200, 44, callback=self._submit, color=PRIMARY, size=22)
        self.error_msg = ""
        self.title = Label("U P L I N K", size=72, color=PRIMARY)
        self.subtitle = Label("Agent Login System", size=28, color=SECONDARY, light=True)
        self.handle_label = Label("Handle", size=18, color=SECONDARY, light=True)
        self.password_label = Label("Password", size=18, color=SECONDARY, light=True)

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

        # Center panel
        pw, ph = 500, 340
        px, py = (1920 - pw) // 2, (1080 - ph) // 2 - 40
        panel = scale.rect(px, py, pw, ph)
        s = pygame.Surface((panel.w, panel.h), pygame.SRCALPHA)
        s.fill((*PANEL_BG, 200))
        surface.blit(s, panel.topleft)
        pygame.draw.rect(surface, SECONDARY, panel, 1, border_radius=4)

        # Title
        self.title.draw(surface, scale, 0, py - 100, align="center", max_w=1920)
        self.subtitle.draw(surface, scale, 0, py - 30, align="center", max_w=1920)

        # Labels
        self.handle_label.draw(surface, scale, 760, 438)
        self.password_label.draw(surface, scale, 760, 508)

        # Inputs
        self.handle_input.draw(surface, scale)
        self.password_input.draw(surface, scale)
        self.connect_btn.draw(surface, scale)

        # Error
        if self.error_msg:
            font = get_font(scale.fs(18))
            txt = font.render(self.error_msg, True, (211, 26, 26))
            cx = scale.x(960) - txt.get_width() // 2
            surface.blit(txt, (cx, scale.y(660)))

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
