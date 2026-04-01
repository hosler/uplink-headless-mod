"""Font registration for Kivy."""
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONT_DIR = os.path.join(PROJECT_ROOT, "game", "uplinkHD", "fonts")
FONT_REGULAR = os.path.join(FONT_DIR, "AeroMaticsRegular.ttf")
FONT_LIGHT = os.path.join(FONT_DIR, "AeroMaticsLightRegular.ttf")


def register_fonts():
    from kivy.core.text import LabelBase
    if os.path.isfile(FONT_REGULAR):
        LabelBase.register(name="AeroMatics", fn_regular=FONT_REGULAR)
    if os.path.isfile(FONT_LIGHT):
        LabelBase.register(name="AeroMaticsLight", fn_regular=FONT_LIGHT)
