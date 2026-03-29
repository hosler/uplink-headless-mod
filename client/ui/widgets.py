"""Reusable UI widgets: Button, TextInput, Label, ScrollableList, ProgressBar."""
import pygame
import time
from ui.theme import get_font, PRIMARY, SECONDARY, TEXT_WHITE, TEXT_DIM, PANEL_BG, ALERT, \
    ROW_ALT, ROW_HOVER, ROW_SELECTED, SUCCESS, Scale


class Label:
    def __init__(self, text="", size=24, color=TEXT_WHITE, light=False):
        self.text = text
        self.size = size
        self.color = color
        self.light = light

    def draw(self, surface, scale: Scale, dx, dy, align="left", max_w=0):
        font = get_font(scale.fs(self.size), self.light)
        rendered = font.render(self.text, True, self.color)
        x = scale.x(dx)
        y = scale.y(dy)
        if align == "center" and max_w:
            x = scale.x(dx) + (scale.w(max_w) - rendered.get_width()) // 2
        elif align == "right" and max_w:
            x = scale.x(dx) + scale.w(max_w) - rendered.get_width()
        surface.blit(rendered, (x, y))
        return rendered.get_height()


class HackerPanel:
    """A decorative panel with corner accents and optional title bar."""
    def __init__(self, dx, dy, dw, dh, title="", color=SECONDARY):
        self.dx, self.dy, self.dw, self.dh = dx, dy, dw, dh
        self.title = title
        self.color = color

    def draw(self, surface, scale: Scale):
        rect = scale.rect(self.dx, self.dy, self.dw, self.dh)
        
        # Translucent background
        bg = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        bg.fill((*PANEL_BG, 200))
        surface.blit(bg, rect.topleft)
        
        # Main border (very thin)
        pygame.draw.rect(surface, (*self.color, 80), rect, 1)
        
        # Corner accents (thicker)
        cl = scale.w(15) # corner length
        cw = scale.w(2)  # corner width
        # Top-left
        pygame.draw.line(surface, self.color, (rect.x, rect.y), (rect.x + cl, rect.y), cw)
        pygame.draw.line(surface, self.color, (rect.x, rect.y), (rect.x, rect.y + cl), cw)
        # Top-right
        pygame.draw.line(surface, self.color, (rect.right, rect.y), (rect.right - cl, rect.y), cw)
        pygame.draw.line(surface, self.color, (rect.right, rect.y), (rect.right, rect.y + cl), cw)
        # Bottom-left
        pygame.draw.line(surface, self.color, (rect.x, rect.bottom), (rect.x + cl, rect.bottom), cw)
        pygame.draw.line(surface, self.color, (rect.x, rect.bottom), (rect.x, rect.bottom - cl), cw)
        # Bottom-right
        pygame.draw.line(surface, self.color, (rect.right, rect.bottom), (rect.right - cl, rect.bottom), cw)
        pygame.draw.line(surface, self.color, (rect.right, rect.bottom), (rect.right, rect.bottom - cl), cw)

        # Title bar
        if self.title:
            font = get_font(scale.fs(16))
            txt = font.render(self.title.upper(), True, self.color)
            # Title background
            tw = txt.get_width() + 20
            th = scale.h(24)
            tr = pygame.Rect(rect.x, rect.y - th, tw, th)
            # Angled title tab
            points = [(tr.x, tr.bottom), (tr.x, tr.y), (tr.right - 10, tr.y), (tr.right, tr.bottom)]
            pygame.draw.polygon(surface, PANEL_BG, points)
            pygame.draw.lines(surface, self.color, False, points, 1)
            surface.blit(txt, (tr.x + 10, tr.y + (th - txt.get_height()) // 2))


class Button:
    def __init__(self, text, dx, dy, dw, dh, callback=None, color=PRIMARY, size=20):
        self.text = text
        self.dx, self.dy, self.dw, self.dh = dx, dy, dw, dh
        self.callback = callback
        self.color = color
        self.size = size
        self.hovered = False
        self.enabled = True
        self.visible = True
        self._hover_start = 0.0

    def get_rect(self, scale: Scale) -> pygame.Rect:
        return scale.rect(self.dx, self.dy, self.dw, self.dh)

    def draw(self, surface, scale: Scale):
        if not self.visible:
            return
        rect = self.get_rect(scale)
        color = self.color if self.enabled else TEXT_DIM

        if self.enabled:
            # Subtle resting fill (12 alpha)
            rest_fill = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            rest_fill.fill((*color, 15))
            surface.blit(rest_fill, rect.topleft)
            
            # Complex border with corner tabs
            pygame.draw.rect(surface, (*SECONDARY, 100), rect, 1)
            cw, ch = scale.w(10), scale.h(10)
            
            # Hover effect
            if self.hovered:
                # Brighter hover glow (50 alpha)
                fill = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                fill.fill((*color, 60))
                surface.blit(fill, rect.topleft)
                pygame.draw.rect(surface, color, rect, 1)
                
                # Expanding corner accents
                t = (time.time() - self._hover_start) * 4
                offset = min(scale.w(4), int(scale.w(4) * t))
                pygame.draw.line(surface, self.color, (rect.x - offset, rect.y - offset), (rect.x + cw - offset, rect.y - offset), 2)
                pygame.draw.line(surface, self.color, (rect.x - offset, rect.y - offset), (rect.x - offset, rect.y + ch - offset), 2)
                pygame.draw.line(surface, self.color, (rect.right + offset - 1, rect.bottom + offset - 1), (rect.right - cw + offset - 1, rect.bottom + offset - 1), 2)
                pygame.draw.line(surface, self.color, (rect.right + offset - 1, rect.bottom + offset - 1), (rect.right + offset - 1, rect.bottom - ch + offset - 1), 2)
            else:
                # Static corners
                pygame.draw.line(surface, color, (rect.x, rect.y), (rect.x + cw, rect.y), 2)
                pygame.draw.line(surface, color, (rect.x, rect.y), (rect.x, rect.y + ch), 2)
                pygame.draw.line(surface, color, (rect.right-1, rect.bottom-1), (rect.right - cw, rect.bottom-1), 2)
                pygame.draw.line(surface, color, (rect.right-1, rect.bottom-1), (rect.right-1, rect.bottom - ch), 2)

            font = get_font(scale.fs(self.size))
            txt_color = color if self.hovered else TEXT_WHITE
            txt = font.render(self.text, True, txt_color)
        else:
            pygame.draw.rect(surface, TEXT_DIM, rect, 1)
            font = get_font(scale.fs(self.size))
            txt = font.render(self.text, True, TEXT_DIM)

        tx = rect.x + (rect.w - txt.get_width()) // 2
        ty = rect.y + (rect.h - txt.get_height()) // 2
        surface.blit(txt, (tx, ty))

    def handle_event(self, event, scale: Scale) -> bool:
        if not self.visible or not self.enabled:
            return False
        rect = self.get_rect(scale)
        if event.type == pygame.MOUSEMOTION:
            prev_hover = self.hovered
            self.hovered = rect.collidepoint(event.pos)
            if self.hovered and not prev_hover:
                self._hover_start = time.time()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if rect.collidepoint(event.pos) and self.callback:
                self.callback()
                return True
        return False


class TextInput:
    def __init__(self, dx, dy, dw, dh, placeholder="", masked=False, size=22):
        self.dx, self.dy, self.dw, self.dh = dx, dy, dw, dh
        self.text = ""
        self.placeholder = placeholder
        self.masked = masked
        self.size = size
        self.focused = False
        self.cursor_pos = 0
        self._blink_time = 0

    def get_rect(self, scale: Scale) -> pygame.Rect:
        return scale.rect(self.dx, self.dy, self.dw, self.dh)

    def draw(self, surface, scale: Scale):
        rect = self.get_rect(scale)
        border_color = PRIMARY if self.focused else SECONDARY
        pygame.draw.rect(surface, PANEL_BG, rect)
        pygame.draw.rect(surface, border_color, rect, 1)

        font = get_font(scale.fs(self.size))
        if self.text:
            display = "*" * len(self.text) if self.masked else self.text
            txt = font.render(display, True, TEXT_WHITE)
        else:
            txt = font.render(self.placeholder, True, TEXT_DIM)
        surface.blit(txt, (rect.x + 8, rect.y + (rect.h - txt.get_height()) // 2))

        # Cursor
        if self.focused and (time.time() * 2) % 2 < 1:
            display = "*" * self.cursor_pos if self.masked else self.text[:self.cursor_pos]
            cx = rect.x + 8 + font.size(display)[0]
            pygame.draw.line(surface, PRIMARY, (cx, rect.y + 4), (cx, rect.y + rect.h - 4), 1)

    def handle_event(self, event, scale: Scale) -> str | None:
        """Returns 'submit' if Enter pressed, None otherwise."""
        rect = self.get_rect(scale)
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.focused = rect.collidepoint(event.pos)
        elif event.type == pygame.KEYDOWN and self.focused:
            if event.key == pygame.K_RETURN:
                return "submit"
            elif event.key == pygame.K_BACKSPACE:
                if self.cursor_pos > 0:
                    self.text = self.text[:self.cursor_pos - 1] + self.text[self.cursor_pos:]
                    self.cursor_pos -= 1
            elif event.key == pygame.K_DELETE:
                self.text = self.text[:self.cursor_pos] + self.text[self.cursor_pos + 1:]
            elif event.key == pygame.K_LEFT:
                self.cursor_pos = max(0, self.cursor_pos - 1)
            elif event.key == pygame.K_RIGHT:
                self.cursor_pos = min(len(self.text), self.cursor_pos + 1)
            elif event.key == pygame.K_HOME:
                self.cursor_pos = 0
            elif event.key == pygame.K_END:
                self.cursor_pos = len(self.text)
            elif event.key == pygame.K_TAB:
                return "tab"
            elif event.unicode and event.unicode.isprintable():
                self.text = self.text[:self.cursor_pos] + event.unicode + self.text[self.cursor_pos:]
                self.cursor_pos += 1
        return None


class ScrollableList:
    def __init__(self, dx, dy, dw, dh, item_height=30):
        self.dx, self.dy, self.dw, self.dh = dx, dy, dw, dh
        self.item_height = item_height
        self.items: list[dict] = []
        self.scroll = 0
        self.selected = -1
        self.hovered = -1
        self.on_select = None

    def get_rect(self, scale: Scale) -> pygame.Rect:
        return scale.rect(self.dx, self.dy, self.dw, self.dh)

    def visible_count(self, scale: Scale) -> int:
        return max(1, scale.h(self.dh) // scale.h(self.item_height))

    def draw(self, surface, scale: Scale, render_item=None):
        rect = self.get_rect(scale)
        # Background
        pygame.draw.rect(surface, PANEL_BG, rect)
        
        ih = scale.h(self.item_height)
        vis = self.visible_count(scale)

        clip = surface.get_clip()
        surface.set_clip(rect)

        for i in range(vis):
            idx = self.scroll + i
            if idx >= len(self.items):
                break
            item = self.items[idx]
            iy = rect.y + i * ih
            # Inset row slightly for border
            ir = pygame.Rect(rect.x + scale.w(2), iy + scale.h(2), rect.w - scale.w(24), ih - scale.h(4))

            # Row background
            if idx == self.selected:
                pygame.draw.rect(surface, ROW_SELECTED, ir)
            elif idx == self.hovered:
                pygame.draw.rect(surface, ROW_HOVER, ir)
            elif idx % 2 == 1:
                pygame.draw.rect(surface, ROW_ALT, ir)
            
            # Row border (hacker style)
            pygame.draw.rect(surface, (*SECONDARY, 80), ir, 1)

            # Diamond icon
            icon_size = scale.w(8)
            ix = ir.x + scale.w(12)
            iy_center = ir.y + ir.h // 2
            points = [(ix, iy_center - icon_size // 2), (ix + icon_size // 2, iy_center),
                      (ix, iy_center + icon_size // 2), (ix - icon_size // 2, iy_center)]
            icon_color = PRIMARY if idx == self.selected else (SECONDARY if idx == self.hovered else TEXT_DIM)
            pygame.draw.polygon(surface, icon_color, points)

            if render_item:
                # Adjust rect for render_item to skip the icon space
                item_rect = pygame.Rect(ir.x + scale.w(24), ir.y, ir.w - scale.w(24), ir.h)
                render_item(surface, scale, item, item_rect, idx == self.selected)
            else:
                font = get_font(scale.fs(18), light=True)
                txt = font.render(str(item), True, TEXT_WHITE)
                surface.blit(txt, (ir.x + scale.w(30), ir.y + (ir.h - txt.get_height()) // 2))

        surface.set_clip(clip)

        # Border around the whole list
        pygame.draw.rect(surface, SECONDARY, rect, 1)

        # Scrollbar
        if len(self.items) > vis:
            sb_w = scale.w(6)
            sb_rect = pygame.Rect(rect.x + rect.w - scale.w(12), rect.y + scale.h(4), sb_w, rect.h - scale.h(8))
            # Track
            track = pygame.Surface((sb_rect.w, sb_rect.h), pygame.SRCALPHA)
            track.fill((*SECONDARY, 40))
            surface.blit(track, sb_rect.topleft)
            # Thumb
            thumb_h = max(scale.h(20), sb_rect.h * vis // len(self.items))
            thumb_y = sb_rect.y + int((sb_rect.h - thumb_h) * self.scroll / max(len(self.items) - vis, 1))
            thumb_rect = pygame.Rect(sb_rect.x, thumb_y, sb_w, thumb_h)
            pygame.draw.rect(surface, PRIMARY, thumb_rect, border_radius=scale.w(1))

    def handle_event(self, event, scale: Scale) -> bool:
        rect = self.get_rect(scale)
        if event.type == pygame.MOUSEMOTION:
            if rect.collidepoint(event.pos):
                ih = scale.h(self.item_height)
                self.hovered = self.scroll + (event.pos[1] - rect.y) // ih
                if self.hovered >= len(self.items):
                    self.hovered = -1
            else:
                self.hovered = -1
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if rect.collidepoint(event.pos):
                if event.button == 1:
                    ih = scale.h(self.item_height)
                    idx = self.scroll + (event.pos[1] - rect.y) // ih
                    if 0 <= idx < len(self.items):
                        self.selected = idx
                        if self.on_select:
                            self.on_select(idx)
                        return True
                elif event.button == 4:  # scroll up
                    self.scroll = max(0, self.scroll - 1)
                elif event.button == 5:  # scroll down
                    vis = self.visible_count(scale)
                    self.scroll = min(max(0, len(self.items) - vis), self.scroll + 1)
        elif event.type == pygame.MOUSEWHEEL:
            if rect.collidepoint(pygame.mouse.get_pos()):
                vis = self.visible_count(scale)
                self.scroll = max(0, min(self.scroll - event.y, max(0, len(self.items) - vis)))
                return True
        return False


class ProgressBar:
    def __init__(self, dx, dy, dw, dh, color=PRIMARY, bg=PANEL_BG, segments=False):
        self.dx, self.dy, self.dw, self.dh = dx, dy, dw, dh
        self.color = color
        self.bg = bg
        self.value = 0.0  # 0-1
        self.segments = segments

    def draw(self, surface, scale: Scale):
        rect = scale.rect(self.dx, self.dy, self.dw, self.dh)
        
        # Background track with subtle depth
        pygame.draw.rect(surface, self.bg, rect)
        track_fill = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        track_fill.fill((*SECONDARY, 20))
        surface.blit(track_fill, rect.topleft)
        
        fill_pct = max(0.0, min(1.0, self.value))
        fill_w = int(rect.w * fill_pct)
        
        if fill_w > 0:
            # Main fill with slight transparency for a neon look
            fill_surf = pygame.Surface((fill_w, rect.h), pygame.SRCALPHA)
            fill_surf.fill((*self.color, 160))
            surface.blit(fill_surf, rect.topleft)
            
            # Subtle top-edge highlight for "glass" effect
            pygame.draw.line(surface, self.color, (rect.x, rect.y + 1), (rect.x + fill_w - 1, rect.y + 1), 1)

            # Segments
            if self.segments:
                seg_w = scale.w(12)
                gap = scale.w(2)
                for sx in range(seg_w, fill_w, seg_w + gap):
                    pygame.draw.line(surface, self.bg, (rect.x + sx, rect.y), (rect.x + sx, rect.y + rect.h), max(1, gap))

        # Border
        pygame.draw.rect(surface, SECONDARY, rect, 1, border_radius=1)
