"""Color constants — Kivy 0-1 RGBA tuples."""

def _c(r, g, b, a=255):
    return (r / 255, g / 255, b / 255, a / 255)

BG_DARK = _c(11, 11, 11)
BG_LIGHT = _c(17, 43, 60)
PRIMARY = _c(43, 170, 255)
SECONDARY = _c(30, 98, 168)
ALERT = _c(211, 26, 26)
SUCCESS = _c(43, 255, 209)
WARNING = _c(255, 200, 50)
TEXT_DIM = _c(40, 100, 160)
TEXT_WHITE = _c(220, 230, 240)
PANEL_BG = _c(11, 21, 32)
PANEL_BORDER = _c(43, 170, 255, 80)
TOPBAR_BG = _c(14, 30, 46)
BLACK = _c(0, 0, 0)
WHITE = _c(255, 255, 255)
ROW_ALT = _c(15, 25, 38)
ROW_HOVER = _c(25, 50, 75)
ROW_SELECTED = _c(30, 70, 110)
TRANSPARENT = (0, 0, 0, 0)
