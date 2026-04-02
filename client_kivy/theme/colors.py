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
TEXT_DIM = _c(70, 130, 180)
TEXT_WHITE = _c(220, 230, 240)
PANEL_BG = _c(14, 24, 36)
PANEL_BORDER = _c(43, 170, 255, 80)
TOPBAR_BG = _c(14, 30, 46)
BLACK = _c(0, 0, 0)
WHITE = _c(255, 255, 255)
ROW_ALT = _c(18, 30, 44)
ROW_HOVER = _c(30, 55, 80)
ROW_SELECTED = _c(35, 75, 115)
TRANSPARENT = (0, 0, 0, 0)
