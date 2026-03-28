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

    def get_rect(self, scale: Scale) -> pygame.Rect:
        return scale.rect(self.dx, self.dy, self.dw, self.dh)

    def draw(self, surface, scale: Scale):
        if not self.visible:
            return
        rect = self.get_rect(scale)
        color = self.color if self.enabled else TEXT_DIM

        if self.hovered and self.enabled:
            pygame.draw.rect(surface, color, rect, 0, border_radius=3)
            font = get_font(scale.fs(self.size))
            txt = font.render(self.text, True, (0, 0, 0))
        else:
            pygame.draw.rect(surface, color, rect, 1, border_radius=3)
            font = get_font(scale.fs(self.size))
            txt = font.render(self.text, True, color)

        tx = rect.x + (rect.w - txt.get_width()) // 2
        ty = rect.y + (rect.h - txt.get_height()) // 2
        surface.blit(txt, (tx, ty))

    def handle_event(self, event, scale: Scale) -> bool:
        if not self.visible or not self.enabled:
            return False
        rect = self.get_rect(scale)
        if event.type == pygame.MOUSEMOTION:
            self.hovered = rect.collidepoint(event.pos)
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
        pygame.draw.rect(surface, PANEL_BG, rect)
        pygame.draw.rect(surface, SECONDARY, rect, 1)

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
            ir = pygame.Rect(rect.x, iy, rect.w, ih)

            # Row background
            if idx == self.selected:
                pygame.draw.rect(surface, ROW_SELECTED, ir)
            elif idx == self.hovered:
                pygame.draw.rect(surface, ROW_HOVER, ir)
            elif idx % 2 == 1:
                pygame.draw.rect(surface, ROW_ALT, ir)

            if render_item:
                render_item(surface, scale, item, ir, idx == self.selected)
            else:
                font = get_font(scale.fs(18), light=True)
                txt = font.render(str(item), True, TEXT_WHITE)
                surface.blit(txt, (ir.x + 8, ir.y + (ih - txt.get_height()) // 2))

        surface.set_clip(clip)

        # Scrollbar
        if len(self.items) > vis:
            sb_h = max(20, rect.h * vis // len(self.items))
            sb_y = rect.y + int(rect.h * self.scroll / len(self.items))
            sb_rect = pygame.Rect(rect.x + rect.w - 6, sb_y, 4, sb_h)
            pygame.draw.rect(surface, SECONDARY, sb_rect, border_radius=2)

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
        return False


class ProgressBar:
    def __init__(self, dx, dy, dw, dh, color=PRIMARY, bg=PANEL_BG):
        self.dx, self.dy, self.dw, self.dh = dx, dy, dw, dh
        self.color = color
        self.bg = bg
        self.value = 0.0  # 0-1

    def draw(self, surface, scale: Scale):
        rect = scale.rect(self.dx, self.dy, self.dw, self.dh)
        pygame.draw.rect(surface, self.bg, rect)
        fill_w = int(rect.w * max(0, min(1, self.value)))
        if fill_w > 0:
            pygame.draw.rect(surface, self.color, pygame.Rect(rect.x, rect.y, fill_w, rect.h))
        pygame.draw.rect(surface, SECONDARY, rect, 1)
