"""Content tab views: Email, Gateway, Missions, BBS, Software, Hardware."""
import pygame
from ui.theme import (Scale, get_font, PRIMARY, SECONDARY, ALERT, SUCCESS,
                      TEXT_WHITE, TEXT_DIM, PANEL_BG, PANEL_BORDER, ROW_ALT,
                      ROW_HOVER, ROW_SELECTED, TOPBAR_H, TAB_H, STATUSBAR_H,
                      DESIGN_W, DESIGN_H)
import audio

# Layout constants — match browser.py centered layout
CONTENT_Y = TOPBAR_H + TAB_H + 10
SCR_W = 1400
SCR_X = (DESIGN_W - SCR_W) // 2
ROW_H = 32


def _draw_panel(surface, scale, x, y, w, h, title=None):
    """Draw a dark panel with hacker corner accents and optional title."""
    rect = scale.rect(x, y, w, h)
    # Translucent background
    bg = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    bg.fill((*PANEL_BG, 200))
    surface.blit(bg, rect.topleft)
    
    pygame.draw.rect(surface, (*SECONDARY, 80), rect, 1)
    
    # Corner accents
    cl = scale.w(12)
    cw = scale.w(2)
    # TL
    pygame.draw.line(surface, SECONDARY, (rect.x, rect.y), (rect.x + cl, rect.y), cw)
    pygame.draw.line(surface, SECONDARY, (rect.x, rect.y), (rect.x, rect.y + cl), cw)
    # BR
    pygame.draw.line(surface, SECONDARY, (rect.right, rect.bottom), (rect.right - cl, rect.bottom), cw)
    pygame.draw.line(surface, SECONDARY, (rect.right, rect.bottom), (rect.right, rect.bottom - cl), cw)

    if title:
        f = get_font(scale.fs(14))
        txt = f.render(title.upper(), True, PRIMARY)
        # Title tab
        tw = txt.get_width() + 16
        th = scale.h(20)
        tr = pygame.Rect(rect.x, rect.y - th, tw, th)
        points = [(tr.x, tr.bottom), (tr.x, tr.y), (tr.right - 8, tr.y), (tr.right, tr.bottom)]
        pygame.draw.polygon(surface, PANEL_BG, points)
        pygame.draw.lines(surface, SECONDARY, False, points, 1)
        surface.blit(txt, (rect.x + scale.w(8), rect.y - th + scale.h(2)))
    return rect


def _draw_header_row(surface, scale, cy, columns):
    """Draw column headers and separator line. Returns y after header."""
    f = get_font(scale.fs(16))
    for label, col_x in columns:
        txt = f.render(label.upper(), True, PRIMARY)
        surface.blit(txt, (scale.x(col_x + 10), scale.y(cy)))
    cy += 30 # Increased padding
    # Decorative separator
    line_x = scale.x(SCR_X)
    line_w = scale.w(SCR_W)
    line_y = scale.y(cy)
    
    # Glow effect for separator
    glow = pygame.Surface((line_w, 4), pygame.SRCALPHA)
    pygame.draw.line(glow, (*SECONDARY, 40), (0, 2), (line_w, 2), 4)
    surface.blit(glow, (line_x, line_y - 2))
    
    pygame.draw.line(surface, (*SECONDARY, 150), (line_x, line_y), (line_x + line_w, line_y), 1)
    # Ends
    pygame.draw.line(surface, SECONDARY, (line_x, line_y - 4), (line_x, line_y + 4), 2)
    pygame.draw.line(surface, SECONDARY, (line_x + line_w, line_y - 4), (line_x + line_w, line_y + 4), 2)
    return cy + 14 # Extra space below line


def _draw_data_row(surface, scale, y, hovered, selected=False, alt=False):
    """Draw row with hacker style: borders, diamond icons, interaction states."""
    row_rect = scale.rect(SCR_X + 2, y + 2, SCR_W - 4, ROW_H - 4)
    
    # Base background
    if selected:
        s = pygame.Surface((row_rect.w, row_rect.h), pygame.SRCALPHA)
        s.fill((*ROW_SELECTED, 180))
        surface.blit(s, row_rect.topleft)
    elif hovered:
        s = pygame.Surface((row_rect.w, row_rect.h), pygame.SRCALPHA)
        s.fill((*ROW_HOVER, 140))
        surface.blit(s, row_rect.topleft)
    elif alt:
        s = pygame.Surface((row_rect.w, row_rect.h), pygame.SRCALPHA)
        s.fill((*ROW_ALT, 100))
        surface.blit(s, row_rect.topleft)
    
    # Row border
    pygame.draw.rect(surface, (*SECONDARY, 60), row_rect, 1)
    
    # Diamond icon
    icon_size = scale.w(8)
    ix = row_rect.x + scale.w(12)
    iy_center = row_rect.y + row_rect.h // 2
    points = [(ix, iy_center - icon_size // 2), (ix + icon_size // 2, iy_center),
              (ix, iy_center + icon_size // 2), (ix - icon_size // 2, iy_center)]
    icon_color = PRIMARY if selected else (SECONDARY if hovered else TEXT_DIM)
    pygame.draw.polygon(surface, icon_color, points)
    
    return row_rect


def _draw_button(surface, scale, x, y, w, h, label, mouse, enabled=True):
    """Draw a high-fidelity tech button."""
    btn_rect = scale.rect(x, y, w, h)
    btn_hovered = btn_rect.collidepoint(mouse) and enabled
    f_btn = get_font(scale.fs(13))
    
    color = PRIMARY if enabled else TEXT_DIM
    
    if enabled:
        # Resting state: subtle fill
        rest_fill = pygame.Surface((btn_rect.w, btn_rect.h), pygame.SRCALPHA)
        rest_fill.fill((*color, 20))
        surface.blit(rest_fill, btn_rect.topleft)
        
        # Border with corner tabs
        pygame.draw.rect(surface, (*SECONDARY, 120), btn_rect, 1)
        cw, ch = scale.w(6), scale.h(6)
        pygame.draw.line(surface, color, (btn_rect.x, btn_rect.y), (btn_rect.x + cw, btn_rect.y), 2)
        pygame.draw.line(surface, color, (btn_rect.x, btn_rect.y), (btn_rect.x, btn_rect.y + ch), 2)
        pygame.draw.line(surface, color, (btn_rect.right-1, btn_rect.bottom-1), (btn_rect.right - cw, btn_rect.bottom-1), 2)
        pygame.draw.line(surface, color, (btn_rect.right-1, btn_rect.bottom-1), (btn_rect.right-1, btn_rect.bottom - ch), 2)
        
        if btn_hovered:
            fill = pygame.Surface((btn_rect.w, btn_rect.h), pygame.SRCALPHA)
            fill.fill((*color, 60))
            surface.blit(fill, btn_rect.topleft)
            pygame.draw.rect(surface, color, btn_rect, 1)
            
        txt_color = color if btn_hovered else TEXT_WHITE
        txt = f_btn.render(label, True, txt_color)
    else:
        pygame.draw.rect(surface, TEXT_DIM, btn_rect, 1)
        txt = f_btn.render(label, True, TEXT_DIM)
        
    tx = btn_rect.x + (btn_rect.w - txt.get_width()) // 2
    ty = btn_rect.y + (btn_rect.h - txt.get_height()) // 2
    surface.blit(txt, (tx, ty))
    return btn_rect


def _draw_scrollbar(surface, scale, x, y, h, scroll, total, visible):
    """Draw a thin vertical scrollbar. x/y/h in design coords."""
    if total <= visible:
        return
    bar_rect = scale.rect(x, y, 4, h)
    # Track
    track = pygame.Surface((bar_rect.w, bar_rect.h), pygame.SRCALPHA)
    track.fill((*SECONDARY, 30))
    surface.blit(track, bar_rect.topleft)
    # Thumb
    thumb_h = max(scale.h(20), int(bar_rect.h * visible / total))
    thumb_y = bar_rect.y + int((bar_rect.h - thumb_h) * scroll / max(total - visible, 1))
    thumb_rect = pygame.Rect(bar_rect.x, thumb_y, bar_rect.w, thumb_h)
    pygame.draw.rect(surface, PRIMARY, thumb_rect, border_radius=2)


def _draw_empty_state(surface, scale, cy, message, submessage=None):
    """Draw a centered empty-state message with dimmed hint."""
    f = get_font(scale.fs(18), light=True)
    txt = f.render(message, True, TEXT_DIM)
    surface.blit(txt, (scale.x(SCR_X + 20), scale.y(cy)))
    if submessage:
        f_sm = get_font(scale.fs(14), light=True)
        txt = f_sm.render(submessage, True, TEXT_DIM)
        surface.blit(txt, (scale.x(SCR_X + 20), scale.y(cy + 28)))


def _draw_tab_title(surface, scale, cy, title, balance=None):
    """Draw a tab title in large caps with optional balance display. Returns y after title."""
    f_title = get_font(scale.fs(28))
    txt = f_title.render(title, True, PRIMARY)
    surface.blit(txt, (scale.x(SCR_X), scale.y(cy)))
    if balance is not None:
        f_bal = get_font(scale.fs(16))
        txt = f_bal.render(f"Balance: {balance:,}c", True, SUCCESS)
        surface.blit(txt, (scale.x(SCR_X + SCR_W - 200), scale.y(cy + 8)))
    return cy + 42


# ============================================================================
# Email View — two-panel: message list + body reader
# ============================================================================

class EmailView:
    def __init__(self, net):
        self.net = net
        self.selected = -1
        self.scroll = 0
        self._data_requested = False
        self.composing = False
        self._compose_to = ""
        self._compose_subject = ""
        self._compose_body = ""
        self._compose_attach = ""
        self._compose_inputs = None  # lazy-initialized TextInputs

    def on_activate(self):
        self._data_requested = False
        self.net.get_inbox()

    def draw(self, surface, scale, state):
        if not self._data_requested:
            self._data_requested = True
            self.net.get_inbox()

        mouse = pygame.mouse.get_pos()
        cy = CONTENT_Y

        cy = _draw_tab_title(surface, scale, cy, "E M A I L")

        msgs = state.inbox
        if not msgs:
            _draw_empty_state(surface, scale, cy,
                              "No messages.",
                              "Messages from employers and contacts will appear here.")
            return

        # Left panel: message list
        list_w = 560
        f_row = get_font(scale.fs(14), light=True)
        f_from = get_font(scale.fs(14))
        f_subj = get_font(scale.fs(13), light=True)

        # Column headers for list
        columns = [("From", SCR_X + 10), ("Subject", SCR_X + 180)]
        cy = _draw_header_row(surface, scale, cy, columns)

        max_vis = 20
        visible = msgs[self.scroll:self.scroll + max_vis]
        for i, msg in enumerate(visible):
            idx = self.scroll + i
            y = cy + i * ROW_H
            row_rect = scale.rect(SCR_X, y, list_w, ROW_H - 2)
            hovered = row_rect.collidepoint(mouse)
            selected = idx == self.selected
            _draw_data_row(surface, scale, y, hovered, selected, i % 2 == 1)

            color = TEXT_WHITE if (hovered or selected) else TEXT_DIM
            sender = msg.get("from", "")[:20]
            subject = msg.get("subject", "")[:40]

            txt = f_from.render(sender, True, color)
            surface.blit(txt, (scale.x(SCR_X + 10), scale.y(y + 7)))
            txt = f_subj.render(subject, True, color)
            surface.blit(txt, (scale.x(SCR_X + 180), scale.y(y + 7)))

        # Scroll indicator + scrollbar
        if len(msgs) > max_vis:
            f_sm = get_font(scale.fs(13), light=True)
            txt = f_sm.render(f"{self.scroll + 1}-{min(self.scroll + max_vis, len(msgs))} of {len(msgs)}", True, TEXT_DIM)
            surface.blit(txt, (scale.x(SCR_X), scale.y(cy + max_vis * ROW_H + 4)))
            _draw_scrollbar(surface, scale, SCR_X + list_w - 8, cy, max_vis * ROW_H, self.scroll, len(msgs), max_vis)

        # Right panel: message body
        body_x = SCR_X + list_w + 30
        body_w = SCR_W - list_w - 30
        body_y = CONTENT_Y + 42

        _draw_panel(surface, scale, body_x, body_y, body_w, 620, "Message")

        if 0 <= self.selected < len(msgs):
            msg = msgs[self.selected]
            f_head = get_font(scale.fs(16))
            f_body = get_font(scale.fs(14), light=True)

            by = body_y + 26
            # From
            txt = f_head.render(f"From: {msg.get('from', '')}", True, TEXT_WHITE)
            surface.blit(txt, (scale.x(body_x + 12), scale.y(by)))
            by += 24
            # Subject
            txt = f_head.render(f"Subject: {msg.get('subject', '')}", True, PRIMARY)
            surface.blit(txt, (scale.x(body_x + 12), scale.y(by)))
            by += 30

            # Separator
            pygame.draw.line(surface, SECONDARY,
                             (scale.x(body_x + 10), scale.y(by)),
                             (scale.x(body_x + body_w - 10), scale.y(by)),
                             max(1, scale.h(1)))
            by += 10

            # Body text — word wrap
            body = msg.get("body", "")
            lines = body.replace("\\n", "\n").split("\n")
            for line in lines:
                # Simple word wrap at ~70 chars
                while len(line) > 70:
                    txt = f_body.render(line[:70], True, TEXT_WHITE)
                    surface.blit(txt, (scale.x(body_x + 12), scale.y(by)))
                    by += 20
                    line = line[70:]
                txt = f_body.render(line, True, TEXT_WHITE)
                surface.blit(txt, (scale.x(body_x + 12), scale.y(by)))
                by += 20
                if by > body_y + 600:
                    break
            # Attachment indicator
            if msg.get("hasdata"):
                by += 10
                txt = f_body.render("[Attachment included]", True, SUCCESS)
                surface.blit(txt, (scale.x(body_x + 12), scale.y(by)))
        elif self.composing:
            # Compose mode
            f_head = get_font(scale.fs(16))
            f_lbl = get_font(scale.fs(13), light=True)
            by = body_y + 26
            txt = f_head.render("Compose Email", True, PRIMARY)
            surface.blit(txt, (scale.x(body_x + 12), scale.y(by)))
            by += 28

            if not self._compose_inputs:
                from ui.widgets import TextInput
                inp_x = body_x + 12
                inp_w = body_w - 24
                self._compose_inputs = {
                    "to": TextInput(inp_x, by + 16, inp_w, 28, placeholder="recipient@company.net", size=14),
                    "subject": TextInput(inp_x, by + 64, inp_w, 28, placeholder="Subject", size=14),
                    "body": TextInput(inp_x, by + 112, inp_w, 28, placeholder="Message body", size=14),
                    "attach": TextInput(inp_x, by + 160, inp_w, 28, placeholder="Attachment filename (optional)", size=14),
                }
                self._compose_inputs["to"].text = self._compose_to
                self._compose_inputs["to"].cursor_pos = len(self._compose_to)
                self._compose_inputs["subject"].text = self._compose_subject
                self._compose_inputs["body"].text = self._compose_body
                self._compose_inputs["attach"].text = self._compose_attach
                self._compose_inputs["to"].focused = True

            for label, key in [("To:", "to"), ("Subject:", "subject"), ("Body:", "body"), ("Attach:", "attach")]:
                txt = f_lbl.render(label, True, SECONDARY)
                surface.blit(txt, (scale.x(body_x + 12), scale.y(by)))
                by += 16
                self._compose_inputs[key].dy = by
                self._compose_inputs[key].draw(surface, scale)
                by += 34

            # Send button
            by += 10
            self._send_btn_rect = scale.rect(body_x + 12, by, 140, 28)
            _draw_button(surface, scale, body_x + 12, by, 140, 28, "SEND", mouse)
            # Cancel button
            self._cancel_btn_rect = scale.rect(body_x + 170, by, 140, 28)
            _draw_button(surface, scale, body_x + 170, by, 140, 28, "CANCEL", mouse)
        else:
            f = get_font(scale.fs(14), light=True)
            txt = f.render("Select a message to read", True, TEXT_DIM)
            surface.blit(txt, (scale.x(body_x + 12), scale.y(body_y + 40)))

            # Compose button
            compose_y = body_y + 80
            self._compose_btn_rect = scale.rect(body_x + 12, compose_y, 180, 28)
            _draw_button(surface, scale, body_x + 12, compose_y, 180, 28, "COMPOSE EMAIL", mouse)

    def handle_event(self, event, scale, state):
        # Compose mode input handling
        if self.composing and self._compose_inputs:
            for key, inp in self._compose_inputs.items():
                r = inp.handle_event(event, scale)
                if r == "tab":
                    # Cycle focus
                    keys = list(self._compose_inputs.keys())
                    idx = keys.index(key)
                    for inp2 in self._compose_inputs.values():
                        inp2.focused = False
                    self._compose_inputs[keys[(idx + 1) % len(keys)]].focused = True
                    return
                if r == "submit":
                    # Send on Enter from any field
                    self._do_send_email()
                    return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Compose mode buttons
            if self.composing:
                if hasattr(self, '_send_btn_rect') and self._send_btn_rect.collidepoint(event.pos):
                    self._do_send_email()
                    return
                if hasattr(self, '_cancel_btn_rect') and self._cancel_btn_rect.collidepoint(event.pos):
                    self.composing = False
                    self._compose_inputs = None
                    return
            # Compose button (when no message selected and not composing)
            elif not self.composing and self.selected < 0:
                if hasattr(self, '_compose_btn_rect') and self._compose_btn_rect.collidepoint(event.pos):
                    self.composing = True
                    self._compose_inputs = None
                    audio.play_sfx("popup")
                    return

            # Message list clicks
            cy = CONTENT_Y + 42 + 28
            list_w = 560
            msgs = state.inbox
            max_vis = 20
            for i in range(min(max_vis, len(msgs) - self.scroll)):
                idx = self.scroll + i
                y = cy + i * ROW_H
                row_rect = scale.rect(SCR_X, y, list_w, ROW_H - 2)
                if row_rect.collidepoint(event.pos):
                    self.selected = idx
                    self.composing = False
                    self._compose_inputs = None
                    audio.play_sfx("popup")
                    return

        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(self.scroll - event.y, max(0, len(state.inbox) - 20)))

    def _do_send_email(self):
        if not self._compose_inputs:
            return
        to = self._compose_inputs["to"].text.strip()
        subject = self._compose_inputs["subject"].text.strip()
        body = self._compose_inputs["body"].text.strip()
        attach = self._compose_inputs["attach"].text.strip()
        if not to:
            return
        self.net.send_mail(to, subject or "No subject", body or " ", attach or None)
        self.net.get_inbox()
        audio.play_sfx("success")
        self.composing = False
        self._compose_inputs = None
        self._compose_to = ""
        self._compose_subject = ""
        self._compose_body = ""
        self._compose_attach = ""


# ============================================================================
# Gateway View — model info, hardware, files, memory bar
# ============================================================================

class GatewayView:
    def __init__(self, net):
        self.net = net
        self.scroll = 0
        self._data_requested = False
        self._ctx_menu = None   # [(label, callback)]
        self._ctx_pos = (0, 0)
        self._file_rows_y = 0   # y start of file list, set during draw

    def on_activate(self):
        self._data_requested = False
        self.net.get_gateway_info()
        self.net.get_gateway_files()

    def draw(self, surface, scale, state):
        if not self._data_requested:
            self._data_requested = True
            self.net.get_gateway_info()
            self.net.get_gateway_files()

        mouse = pygame.mouse.get_pos()
        cy = CONTENT_Y

        cy = _draw_tab_title(surface, scale, cy, "G A T E W A Y")

        gi = state.gateway_info
        if not gi:
            _draw_empty_state(surface, scale, cy,
                              "Loading gateway info...",
                              "Connecting to your gateway system.")
            return

        f_label = get_font(scale.fs(15))
        f_val = get_font(scale.fs(15), light=True)
        f_small = get_font(scale.fs(13), light=True)

        # Model name
        f_model = get_font(scale.fs(22))
        model = gi.get("model", "Unknown Gateway")
        txt = f_model.render(model, True, TEXT_WHITE)
        surface.blit(txt, (scale.x(SCR_X + 10), scale.y(cy)))
        cy += 36

        # Stats row
        stats = [
            ("Modem", f"{gi.get('modemspeed', 0)} GHz"),
            ("Memory", f"{gi.get('memorysize', 0)} GQ"),
            ("Bandwidth", f"{gi.get('bandwidth', 0)} GQs"),
            ("Max CPUs", str(gi.get("maxcpus", "?"))),
            ("Max Memory", f"{gi.get('maxmemory', 0)} GQ"),
        ]
        sx = SCR_X + 10
        for label, val in stats:
            txt = f_label.render(label, True, SECONDARY)
            surface.blit(txt, (scale.x(sx), scale.y(cy)))
            txt = f_val.render(val, True, TEXT_WHITE)
            surface.blit(txt, (scale.x(sx), scale.y(cy + 20)))
            sx += 200

        cy += 52

        # Nuked warning
        if gi.get("nuked"):
            txt = f_label.render("!! GATEWAY NUKED !!", True, ALERT)
            surface.blit(txt, (scale.x(SCR_X + 10), scale.y(cy)))
            cy += 28

        # Memory bar
        mem_total = gi.get("memorysize", 1)
        mem_used = sum(f.get("size", 0) for f in state.gateway_files) if state.gateway_files else 0
        cy += 6
        txt = f_label.render("Memory Usage", True, SECONDARY)
        surface.blit(txt, (scale.x(SCR_X + 10), scale.y(cy)))
        cy += 20
        bar_w = 600
        bar_h = 18
        bar_rect = scale.rect(SCR_X + 10, cy, bar_w, bar_h)
        
        # Background track
        pygame.draw.rect(surface, PANEL_BG, bar_rect)
        track_fill = pygame.Surface((bar_rect.w, bar_rect.h), pygame.SRCALPHA)
        track_fill.fill((*SECONDARY, 20))
        surface.blit(track_fill, bar_rect.topleft)
        
        if mem_total > 0:
            fill_pct = min(1.0, mem_used / mem_total)
            fill_color = ALERT if fill_pct > 0.9 else (SUCCESS if fill_pct < 0.7 else (255, 200, 50))
            fill_w = int(bar_rect.w * fill_pct)
            if fill_w > 0:
                # Main fill
                fill_surf = pygame.Surface((fill_w, bar_rect.h), pygame.SRCALPHA)
                fill_surf.fill((*fill_color, 160))
                surface.blit(fill_surf, bar_rect.topleft)
                # Segments
                seg_w = scale.w(12)
                gap = scale.w(2)
                for sx in range(seg_w, fill_w, seg_w + gap):
                    pygame.draw.line(surface, PANEL_BG, (bar_rect.x + sx, bar_rect.y),
                                     (bar_rect.x + sx, bar_rect.y + bar_rect.h), max(1, gap))

        pygame.draw.rect(surface, SECONDARY, bar_rect, 1, border_radius=1)
        txt = f_small.render(f"{mem_used} / {mem_total} GQ", True, TEXT_WHITE)
        surface.blit(txt, (scale.x(SCR_X + bar_w + 20), scale.y(cy)))
        cy += 30

        # Separator between memory bar and hardware
        pygame.draw.line(surface, SECONDARY,
                         (scale.x(SCR_X + 10), scale.y(cy)),
                         (scale.x(SCR_X + SCR_W - 10), scale.y(cy)),
                         max(1, scale.h(1)))
        cy += 10

        # Installed hardware
        hw_list = gi.get("hardware", [])
        if hw_list:
            txt = f_label.render("Installed Hardware", True, SECONDARY)
            surface.blit(txt, (scale.x(SCR_X + 10), scale.y(cy)))
            cy += 22
            for hw in hw_list:
                txt = f_val.render(f"  {hw}", True, TEXT_WHITE)
                surface.blit(txt, (scale.x(SCR_X + 10), scale.y(cy)))
                cy += 22
            cy += 10

        # Gateway files
        files = state.gateway_files
        if files:
            columns = [("Filename", SCR_X + 10), ("Size", SCR_X + 500)]
            cy = _draw_header_row(surface, scale, cy, columns)
            self._file_rows_y = cy

            f_row = get_font(scale.fs(14), light=True)
            max_vis = 15
            visible = files[self.scroll:self.scroll + max_vis]
            for i, f in enumerate(visible):
                y = cy + i * ROW_H
                row_rect = scale.rect(SCR_X, y, SCR_W, ROW_H - 2)
                hovered = row_rect.collidepoint(mouse)
                _draw_data_row(surface, scale, y, hovered, alt=i % 2 == 1)

                color = TEXT_WHITE if hovered else (140, 170, 200)
                txt = f_row.render(f.get("title", "")[:50], True, color)
                surface.blit(txt, (scale.x(SCR_X + 10), scale.y(y + 7)))
                txt = f_row.render(f"{f.get('size', 0)} GQ", True, TEXT_DIM)
                surface.blit(txt, (scale.x(SCR_X + 500), scale.y(y + 7)))

            if len(files) > max_vis:
                txt = f_small.render(f"{self.scroll + 1}-{min(self.scroll + max_vis, len(files))} of {len(files)}", True, TEXT_DIM)
                surface.blit(txt, (scale.x(SCR_X), scale.y(cy + max_vis * ROW_H + 4)))
                _draw_scrollbar(surface, scale, SCR_X + SCR_W - 8, cy, max_vis * ROW_H, self.scroll, len(files), max_vis)

        # Context menu
        if self._ctx_menu:
            x, y = self._ctx_pos
            f_menu = get_font(scale.fs(15))
            menu_w = scale.w(180)
            item_h = scale.h(28)
            menu_h = len(self._ctx_menu) * item_h + 4
            bg = pygame.Surface((menu_w, menu_h), pygame.SRCALPHA)
            bg.fill((15, 25, 40, 240))
            surface.blit(bg, (x, y))
            pygame.draw.rect(surface, PRIMARY, (x, y, menu_w, menu_h), 1)
            for i, (label, _) in enumerate(self._ctx_menu):
                iy = y + 2 + i * item_h
                item_rect = pygame.Rect(x + 1, iy, menu_w - 2, item_h)
                hovered = item_rect.collidepoint(mouse)
                if hovered:
                    pygame.draw.rect(surface, (*PRIMARY, 60), item_rect)
                txt = f_menu.render(label, True, TEXT_WHITE if hovered else PRIMARY)
                surface.blit(txt, (x + 10, iy + 4))

    def handle_event(self, event, scale, state):
        if event.type == pygame.MOUSEWHEEL:
            max_files = len(state.gateway_files)
            self.scroll = max(0, min(self.scroll - event.y, max(0, max_files - 15)))

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self._ctx_menu:
            # Context menu click
            x, y = self._ctx_pos
            menu_w = scale.w(180)
            item_h = scale.h(28)
            for i, (label, action) in enumerate(self._ctx_menu):
                iy = y + 2 + i * item_h
                item_rect = pygame.Rect(x + 1, iy, menu_w - 2, item_h)
                if item_rect.collidepoint(event.pos):
                    action()
                    self._ctx_menu = None
                    return
            self._ctx_menu = None
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            # Right-click on gateway file
            files = state.gateway_files
            max_vis = 15
            visible = files[self.scroll:self.scroll + max_vis]
            for i, f in enumerate(visible):
                y = self._file_rows_y + i * ROW_H
                row_rect = scale.rect(SCR_X, y, SCR_W, ROW_H - 2)
                if row_rect.collidepoint(event.pos):
                    title = f.get("title", "")
                    self._ctx_pos = event.pos
                    self._ctx_menu = [
                        ("Delete File", lambda t=title: (
                            self.net.delete_gateway_file(t),
                            self.net.get_gateway_files(),
                            audio.play_sfx("popup"))),
                    ]
                    return


# ============================================================================
# Missions View — two-panel: mission list + details
# ============================================================================

class MissionsView:
    def __init__(self, net):
        self.net = net
        self.selected = -1
        self._data_requested = False
        self._complete_btn_rect = None  # set during draw
        self._link_rects = []  # [(rect, ip)] set during draw

    def on_activate(self):
        self._data_requested = False
        self.net.get_missions()

    def draw(self, surface, scale, state):
        if not self._data_requested:
            self._data_requested = True
            self.net.get_missions()

        mouse = pygame.mouse.get_pos()
        cy = CONTENT_Y

        cy = _draw_tab_title(surface, scale, cy, "M I S S I O N S")

        missions = state.missions
        if not missions:
            _draw_empty_state(surface, scale, cy,
                              "No active missions.",
                              "Check the BBS tab to accept available work.")
            return

        # Left panel: mission list
        list_w = 560
        f_row = get_font(scale.fs(14), light=True)
        f_pay = get_font(scale.fs(14))

        columns = [("Payment", SCR_X + 10), ("Difficulty", SCR_X + 120), ("Description", SCR_X + 210)]
        cy = _draw_header_row(surface, scale, cy, columns)

        for i, m in enumerate(missions):
            y = cy + i * ROW_H
            row_rect = scale.rect(SCR_X, y, list_w, ROW_H - 2)
            hovered = row_rect.collidepoint(mouse)
            selected = i == self.selected
            _draw_data_row(surface, scale, y, hovered, selected, i % 2 == 1)

            color = TEXT_WHITE if (hovered or selected) else TEXT_DIM
            txt = f_pay.render(f"${m.get('payment', 0):,}", True, SUCCESS)
            surface.blit(txt, (scale.x(SCR_X + 10), scale.y(y + 7)))

            diff = m.get("difficulty", 0)
            diff_color = SUCCESS if diff <= 3 else ((255, 200, 50) if diff <= 6 else ALERT)
            txt = f_row.render(f"{'*' * diff}", True, diff_color)
            surface.blit(txt, (scale.x(SCR_X + 120), scale.y(y + 7)))

            desc = m.get("description", "")[:35]
            txt = f_row.render(desc, True, color)
            surface.blit(txt, (scale.x(SCR_X + 210), scale.y(y + 7)))

        # Right panel: mission details
        detail_x = SCR_X + list_w + 30
        detail_w = SCR_W - list_w - 30
        detail_y = CONTENT_Y + 42

        _draw_panel(surface, scale, detail_x, detail_y, detail_w, 620, "Mission Details")

        if 0 <= self.selected < len(missions):
            m = missions[self.selected]
            f_head = get_font(scale.fs(16))
            f_body = get_font(scale.fs(14), light=True)
            f_sm = get_font(scale.fs(13), light=True)

            dy = detail_y + 26

            # Employer
            txt = f_head.render(f"Employer: {m.get('employer', 'Unknown')}", True, TEXT_WHITE)
            surface.blit(txt, (scale.x(detail_x + 12), scale.y(dy)))
            dy += 24

            # Contact
            txt = f_body.render(f"Contact: {m.get('contact', '')}", True, TEXT_DIM)
            surface.blit(txt, (scale.x(detail_x + 12), scale.y(dy)))
            dy += 24

            # Payment + Difficulty
            txt = f_head.render(f"Payment: ${m.get('payment', 0):,}", True, SUCCESS)
            surface.blit(txt, (scale.x(detail_x + 12), scale.y(dy)))
            diff = m.get("difficulty", 0)
            txt = f_body.render(f"Difficulty: {diff}", True, TEXT_WHITE)
            surface.blit(txt, (scale.x(detail_x + 250), scale.y(dy)))
            dy += 30

            # Separator
            pygame.draw.line(surface, SECONDARY,
                             (scale.x(detail_x + 10), scale.y(dy)),
                             (scale.x(detail_x + detail_w - 10), scale.y(dy)),
                             max(1, scale.h(1)))
            dy += 12

            # Description
            desc = m.get("description", "")
            lines = desc.replace("\\n", "\n").split("\n")
            for line in lines:
                while len(line) > 60:
                    txt = f_body.render(line[:60], True, TEXT_WHITE)
                    surface.blit(txt, (scale.x(detail_x + 12), scale.y(dy)))
                    dy += 20
                    line = line[60:]
                txt = f_body.render(line, True, TEXT_WHITE)
                surface.blit(txt, (scale.x(detail_x + 12), scale.y(dy)))
                dy += 20
            dy += 10

            # Completion targets
            compA = m.get("completionA", "")
            compB = m.get("completionB", "")
            if compA:
                txt = f_sm.render(f"Target A: {compA}", True, SECONDARY)
                surface.blit(txt, (scale.x(detail_x + 12), scale.y(dy)))
                dy += 20
            if compB:
                txt = f_sm.render(f"Target B: {compB}", True, SECONDARY)
                surface.blit(txt, (scale.x(detail_x + 12), scale.y(dy)))
                dy += 20
            dy += 10

            # Links (clickable)
            links = m.get("links", [])
            self._link_rects = []
            if links:
                txt = f_head.render("Links:", True, SECONDARY)
                surface.blit(txt, (scale.x(detail_x + 12), scale.y(dy)))
                dy += 22
                for lk in links:
                    lk_rect = scale.rect(detail_x + 12, dy, detail_w - 24, 20)
                    lk_hover = lk_rect.collidepoint(mouse)
                    txt = f_body.render(f"  > {lk}", True, TEXT_WHITE if lk_hover else PRIMARY)
                    surface.blit(txt, (scale.x(detail_x + 12), scale.y(dy)))
                    self._link_rects.append((lk_rect, lk))
                    dy += 20

            # Codes
            codes = m.get("codes", {})
            if codes:
                dy += 6
                txt = f_head.render("Access Codes:", True, SECONDARY)
                surface.blit(txt, (scale.x(detail_x + 12), scale.y(dy)))
                dy += 22
                for ip, code in codes.items():
                    txt = f_body.render(f"  {ip}: {code}", True, SUCCESS)
                    surface.blit(txt, (scale.x(detail_x + 12), scale.y(dy)))
                    dy += 20

            # "Send Completion" button
            dy += 16
            self._complete_btn_rect = scale.rect(detail_x + 12, dy, 220, 28)
            _draw_button(surface, scale, detail_x + 12, dy, 220, 28,
                         "SEND COMPLETION", mouse)
        else:
            f = get_font(scale.fs(18), light=True)
            txt = f.render("SELECT A MISSION", True, TEXT_DIM)
            # Center in the panel
            cx = scale.x(detail_x + detail_w // 2) - txt.get_width() // 2
            cy_mid = scale.y(detail_y + 310) - txt.get_height() // 2
            surface.blit(txt, (cx, cy_mid))

    def handle_event(self, event, scale, state):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            cy = CONTENT_Y + 42 + 28  # after title + header
            list_w = 560

            # Mission list clicks
            for i in range(len(state.missions)):
                y = cy + i * ROW_H
                row_rect = scale.rect(SCR_X, y, list_w, ROW_H - 2)
                if row_rect.collidepoint(event.pos):
                    self.selected = i
                    audio.play_sfx("popup")
                    return

            # Mission link clicks — connect to server
            for lk_rect, ip in self._link_rects:
                if lk_rect.collidepoint(event.pos):
                    self.net.server_connect(ip)
                    audio.play_sfx("bounce")
                    return

            # "Send Completion" button
            if (self._complete_btn_rect and
                    0 <= self.selected < len(state.missions) and
                    self._complete_btn_rect.collidepoint(event.pos)):
                m = state.missions[self.selected]
                contact = m.get("contact", "")
                desc = m.get("description", "")
                if contact and desc:
                    self.net.send_mail(contact, "Mission Complete", desc)
                    self.net.check_mission()
                    self.net.get_missions()
                    self.net.get_balance()
                    self.net.get_inbox()
                    audio.play_sfx("missionSuccess")
                    self.selected = -1
                    return


# ============================================================================
# BBS View — mission bulletin board with accept
# ============================================================================

class BBSView:
    def __init__(self, net, statusbar):
        self.net = net
        self.statusbar = statusbar
        self.scroll = 0
        self._data_requested = False

    def on_activate(self):
        self._data_requested = False
        self.net.get_bbs()

    def draw(self, surface, scale, state):
        if not self._data_requested:
            self._data_requested = True
            self.net.get_bbs()
            self.net.get_balance()

        mouse = pygame.mouse.get_pos()
        cy = CONTENT_Y

        cy = _draw_tab_title(surface, scale, cy, "U P L I N K   B B S", balance=state.balance)

        missions = state.bbs_missions
        if not missions:
            _draw_empty_state(surface, scale, cy,
                              "No missions available at this time.",
                              "New contracts are posted periodically. Check back later.")
            return

        columns = [("Payment", SCR_X + 10), ("Diff", SCR_X + 140),
                   ("Employer", SCR_X + 200), ("Description", SCR_X + 420),
                   ("", SCR_X + SCR_W - 120)]
        cy = _draw_header_row(surface, scale, cy, columns)

        f_row = get_font(scale.fs(14), light=True)
        f_pay = get_font(scale.fs(14))
        max_vis = 18
        visible = missions[self.scroll:self.scroll + max_vis]

        for i, m in enumerate(visible):
            y = cy + i * ROW_H
            row_rect = scale.rect(SCR_X, y, SCR_W, ROW_H - 2)
            hovered = row_rect.collidepoint(mouse)
            _draw_data_row(surface, scale, y, hovered, alt=i % 2 == 1)

            color = TEXT_WHITE if hovered else TEXT_DIM

            # Payment — always teal
            txt = f_pay.render(f"${m.get('payment', 0):,}", True, SUCCESS)
            surface.blit(txt, (scale.x(SCR_X + 10), scale.y(y + 7)))

            # Difficulty stars
            diff = m.get("difficulty", 0)
            diff_color = SUCCESS if diff <= 3 else ((255, 200, 50) if diff <= 6 else ALERT)
            txt = f_row.render(f"{'*' * diff}", True, diff_color)
            surface.blit(txt, (scale.x(SCR_X + 140), scale.y(y + 7)))

            # Employer
            txt = f_row.render(m.get("employer", "")[:20], True, color)
            surface.blit(txt, (scale.x(SCR_X + 200), scale.y(y + 7)))

            # Description
            txt = f_row.render(m.get("description", "")[:50], True, color)
            surface.blit(txt, (scale.x(SCR_X + 420), scale.y(y + 7)))

            # Accept button
            _draw_button(surface, scale, SCR_X + SCR_W - 120, y + 3, 100, 22, "ACCEPT", mouse)

        if len(missions) > max_vis:
            f_sm = get_font(scale.fs(13), light=True)
            txt = f_sm.render(f"{self.scroll + 1}-{min(self.scroll + max_vis, len(missions))} of {len(missions)}", True, TEXT_DIM)
            surface.blit(txt, (scale.x(SCR_X), scale.y(cy + max_vis * ROW_H + 4)))
            _draw_scrollbar(surface, scale, SCR_X + SCR_W - 8, cy, max_vis * ROW_H, self.scroll, len(missions), max_vis)

    def handle_event(self, event, scale, state):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            cy = CONTENT_Y + 42 + 28  # after title + header
            max_vis = 18
            missions = state.bbs_missions
            visible = missions[self.scroll:self.scroll + max_vis]
            for i, m in enumerate(visible):
                # Check accept button
                y = cy + i * ROW_H
                btn_rect = scale.rect(SCR_X + SCR_W - 120, y + 3, 100, 22)
                if btn_rect.collidepoint(event.pos):
                    self.net.accept_mission(m.get("index", self.scroll + i))
                    self.net.get_bbs()
                    self.net.get_missions()
                    self.net.get_balance()
                    self.net.get_links()  # mission may add new server links
                    audio.play_sfx("acceptMission")
                    self.statusbar.show(f"Mission accepted: {m.get('description', '')[:40]}")
                    return

        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(self.scroll - event.y, max(0, len(state.bbs_missions) - 18)))


# ============================================================================
# Software View — catalog with buy buttons
# ============================================================================

class SoftwareView:
    def __init__(self, net, statusbar):
        self.net = net
        self.statusbar = statusbar
        self.scroll = 0
        self._data_requested = False

    def on_activate(self):
        self._data_requested = False
        self.net.get_software_list()
        self.net.get_balance()

    def draw(self, surface, scale, state):
        if not self._data_requested:
            self._data_requested = True
            self.net.get_software_list()
            self.net.get_balance()

        mouse = pygame.mouse.get_pos()
        cy = CONTENT_Y

        cy = _draw_tab_title(surface, scale, cy, "S O F T W A R E   S A L E S", balance=state.balance)

        sw_list = state.software_list
        if not sw_list:
            _draw_empty_state(surface, scale, cy, "No software available.")
            return

        columns = [("Title", SCR_X + 10), ("Version", SCR_X + 500),
                   ("Size", SCR_X + 620), ("Cost", SCR_X + 740), ("", SCR_X + SCR_W - 120)]
        cy = _draw_header_row(surface, scale, cy, columns)

        f_row = get_font(scale.fs(14), light=True)
        f_name = get_font(scale.fs(14))
        max_vis = 18
        visible = sw_list[self.scroll:self.scroll + max_vis]

        for i, sw in enumerate(visible):
            y = cy + i * ROW_H
            row_rect = scale.rect(SCR_X, y, SCR_W, ROW_H - 2)
            hovered = row_rect.collidepoint(mouse)
            _draw_data_row(surface, scale, y, hovered, alt=i % 2 == 1)

            color = TEXT_WHITE if hovered else TEXT_DIM

            txt = f_name.render(sw.get("title", ""), True, color)
            surface.blit(txt, (scale.x(SCR_X + 10), scale.y(y + 7)))

            txt = f_row.render(f"v{sw.get('version', 1)}", True, SECONDARY)
            surface.blit(txt, (scale.x(SCR_X + 500), scale.y(y + 7)))

            txt = f_row.render(f"{sw.get('size', 0)} GQ", True, TEXT_DIM)
            surface.blit(txt, (scale.x(SCR_X + 620), scale.y(y + 7)))

            cost = sw.get("cost", 0)
            affordable = state.balance >= cost
            txt = f_row.render(f"${cost:,}", True, SUCCESS if affordable else ALERT)
            surface.blit(txt, (scale.x(SCR_X + 740), scale.y(y + 7)))

            _draw_button(surface, scale, SCR_X + SCR_W - 120, y + 3, 100, 22, "BUY", mouse, enabled=affordable)

        if len(sw_list) > max_vis:
            f_sm = get_font(scale.fs(13), light=True)
            txt = f_sm.render(f"{self.scroll + 1}-{min(self.scroll + max_vis, len(sw_list))} of {len(sw_list)}", True, TEXT_DIM)
            surface.blit(txt, (scale.x(SCR_X), scale.y(cy + max_vis * ROW_H + 4)))
            _draw_scrollbar(surface, scale, SCR_X + SCR_W - 8, cy, max_vis * ROW_H, self.scroll, len(sw_list), max_vis)

    def handle_event(self, event, scale, state):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            cy = CONTENT_Y + 42 + 28
            max_vis = 18
            sw_list = state.software_list
            visible = sw_list[self.scroll:self.scroll + max_vis]
            for i, sw in enumerate(visible):
                y = cy + i * ROW_H
                btn_rect = scale.rect(SCR_X + SCR_W - 120, y + 3, 100, 22)
                if btn_rect.collidepoint(event.pos):
                    cost = sw.get("cost", 0)
                    if state.balance >= cost:
                        self.net.buy_software(sw["title"])
                        self.net.get_balance()
                        self.net.get_gateway_files()
                        audio.play_sfx("buy")
                        self.statusbar.show(f"Purchased: {sw['title']}")
                    else:
                        audio.play_sfx("error")
                        self.statusbar.show("Insufficient funds")
                    return

        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(self.scroll - event.y, max(0, len(state.software_list) - 18)))


# ============================================================================
# Hardware View — catalog with buy buttons
# ============================================================================

class HardwareView:
    def __init__(self, net, statusbar):
        self.net = net
        self.statusbar = statusbar
        self.scroll = 0
        self._data_requested = False

    def on_activate(self):
        self._data_requested = False
        self.net.get_hardware_list()
        self.net.get_balance()

    def draw(self, surface, scale, state):
        if not self._data_requested:
            self._data_requested = True
            self.net.get_hardware_list()
            self.net.get_balance()

        mouse = pygame.mouse.get_pos()
        cy = CONTENT_Y

        cy = _draw_tab_title(surface, scale, cy, "H A R D W A R E   U P G R A D E S", balance=state.balance)

        hw_list = state.hardware_list
        if not hw_list:
            _draw_empty_state(surface, scale, cy, "No hardware available.")
            return

        columns = [("Component", SCR_X + 10), ("Cost", SCR_X + 600), ("", SCR_X + SCR_W - 120)]
        cy = _draw_header_row(surface, scale, cy, columns)

        f_row = get_font(scale.fs(14), light=True)
        f_name = get_font(scale.fs(14))
        max_vis = 18
        visible = hw_list[self.scroll:self.scroll + max_vis]

        for i, hw in enumerate(visible):
            y = cy + i * ROW_H
            row_rect = scale.rect(SCR_X, y, SCR_W, ROW_H - 2)
            hovered = row_rect.collidepoint(mouse)
            _draw_data_row(surface, scale, y, hovered, alt=i % 2 == 1)

            color = TEXT_WHITE if hovered else TEXT_DIM

            txt = f_name.render(hw.get("title", ""), True, color)
            surface.blit(txt, (scale.x(SCR_X + 10), scale.y(y + 7)))

            cost = hw.get("cost", 0)
            affordable = state.balance >= cost
            txt = f_row.render(f"${cost:,}", True, SUCCESS if affordable else ALERT)
            surface.blit(txt, (scale.x(SCR_X + 600), scale.y(y + 7)))

            _draw_button(surface, scale, SCR_X + SCR_W - 120, y + 3, 100, 22, "BUY", mouse, enabled=affordable)

        if len(hw_list) > max_vis:
            f_sm = get_font(scale.fs(13), light=True)
            txt = f_sm.render(f"{self.scroll + 1}-{min(self.scroll + max_vis, len(hw_list))} of {len(hw_list)}", True, TEXT_DIM)
            surface.blit(txt, (scale.x(SCR_X), scale.y(cy + max_vis * ROW_H + 4)))
            _draw_scrollbar(surface, scale, SCR_X + SCR_W - 8, cy, max_vis * ROW_H, self.scroll, len(hw_list), max_vis)

    def handle_event(self, event, scale, state):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            cy = CONTENT_Y + 42 + 28
            max_vis = 18
            hw_list = state.hardware_list
            visible = hw_list[self.scroll:self.scroll + max_vis]
            for i, hw in enumerate(visible):
                y = cy + i * ROW_H
                btn_rect = scale.rect(SCR_X + SCR_W - 120, y + 3, 100, 22)
                if btn_rect.collidepoint(event.pos):
                    cost = hw.get("cost", 0)
                    if state.balance >= cost:
                        self.net.buy_hardware(hw["title"])
                        self.net.get_balance()
                        self.net.get_gateway_info()
                        audio.play_sfx("buy")
                        self.statusbar.show(f"Installed: {hw['title']}")
                    else:
                        audio.play_sfx("error")
                        self.statusbar.show("Insufficient funds")
                    return

        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, min(self.scroll - event.y, max(0, len(state.hardware_list) - 18)))
