"""Visual theme: colors, fonts, scaling."""
import os
import pygame

# Colors
BG_DARK = (11, 11, 11)
BG_LIGHT = (17, 43, 60)
PRIMARY = (43, 170, 255)
SECONDARY = (30, 98, 168)
ALERT = (211, 26, 26)
SUCCESS = (43, 255, 209)
TEXT_DIM = (40, 100, 160)
TEXT_WHITE = (220, 230, 240)
PANEL_BG = (11, 21, 32)
PANEL_BORDER = (43, 170, 255, 80)
TOPBAR_BG = (14, 30, 46)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
ROW_ALT = (15, 25, 38)
ROW_HOVER = (25, 50, 75)
ROW_SELECTED = (30, 70, 110)

# Design resolution
DESIGN_W = 1920
DESIGN_H = 1080
TOPBAR_H = 40
TAB_H = 36
STATUSBAR_H = 32

# Font paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONT_REGULAR = os.path.join(PROJECT_ROOT, "game/uplinkHD/fonts/AeroMaticsRegular.ttf")
FONT_LIGHT = os.path.join(PROJECT_ROOT, "game/uplinkHD/fonts/AeroMaticsLightRegular.ttf")

_font_cache: dict[tuple, pygame.font.Font] = {}


def get_font(size: int, light: bool = False) -> pygame.font.Font:
    path = FONT_LIGHT if light else FONT_REGULAR
    key = (path, size)
    if key not in _font_cache:
        try:
            _font_cache[key] = pygame.font.Font(path, size)
        except Exception:
            _font_cache[key] = pygame.font.SysFont("monospace", size)
    return _font_cache[key]


class Scale:
    def __init__(self, win_w: int, win_h: int):
        self.win_w = win_w
        self.win_h = win_h
        self.factor = min(win_w / DESIGN_W, win_h / DESIGN_H)
        self.ox = int((win_w - DESIGN_W * self.factor) / 2)
        self.oy = int((win_h - DESIGN_H * self.factor) / 2)

    def x(self, dx: int) -> int:
        return self.ox + int(dx * self.factor)

    def y(self, dy: int) -> int:
        return self.oy + int(dy * self.factor)

    def w(self, dw: int) -> int:
        return max(1, int(dw * self.factor))

    def h(self, dh: int) -> int:
        return max(1, int(dh * self.factor))

    def fs(self, design_size: int) -> int:
        return max(8, int(design_size * self.factor))

    def rect(self, dx, dy, dw, dh) -> pygame.Rect:
        return pygame.Rect(self.x(dx), self.y(dy), self.w(dw), self.h(dh))


_gradient_cache: pygame.Surface | None = None
_gradient_size: tuple[int, int] = (0, 0)


def draw_gradient(surface: pygame.Surface):
    """Draw vertical gradient background."""
    global _gradient_cache, _gradient_size
    w, h = surface.get_size()
    if _gradient_cache is None or _gradient_size != (w, h):
        _gradient_cache = pygame.Surface((w, h))
        for y in range(h):
            t = y / max(h - 1, 1)
            r = int(BG_DARK[0] + (BG_LIGHT[0] - BG_DARK[0]) * t)
            g = int(BG_DARK[1] + (BG_LIGHT[1] - BG_DARK[1]) * t)
            b = int(BG_DARK[2] + (BG_LIGHT[2] - BG_DARK[2]) * t)
            pygame.draw.line(_gradient_cache, (r, g, b), (0, y), (w, y))
        _gradient_size = (w, h)
    surface.blit(_gradient_cache, (0, 0))


_scanline_cache: pygame.Surface | None = None


def draw_scanlines(surface: pygame.Surface):
    """Draw subtle horizontal scanlines and vignette."""
    global _scanline_cache
    w, h = surface.get_size()
    if _scanline_cache is None or _scanline_cache.get_size() != (w, h):
        _scanline_cache = pygame.Surface((w, h), pygame.SRCALPHA)
        # Scanlines
        for y in range(0, h, 3):
            pygame.draw.line(_scanline_cache, (0, 0, 0, 15), (0, y), (w, y))
        # Vignette (smooth gradient)
        for i in range(40):
            alpha = int(60 * (1 - i / 40)**1.5)
            # Draw concentric frames with decreasing alpha
            pygame.draw.rect(_scanline_cache, (0, 0, 0, alpha), (0, 0, w, h), (i + 1) * 8)
    surface.blit(_scanline_cache, (0, 0))


def invalidate_gradient():
    global _gradient_cache, _scanline_cache
    _gradient_cache = None
    _scanline_cache = None
