"""HighSecurityRenderer — multi-factor authentication challenge UI."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle, Line

from theme.colors import (PRIMARY, SECONDARY, TEXT_WHITE, TEXT_DIM, PANEL_BG,
                          ALERT, SUCCESS, WARNING)
from widgets.hacker_button import HackerButton
from browser.renderers.base import BaseRenderer

# Challenge type colors
CHALLENGE_COLORS = {
    "password": ALERT,
    "pass": ALERT,
    "voice": SUCCESS,
    "cypher": WARNING,
    "elliptic": WARNING,
}

CHALLENGE_ICONS = {
    "password": "PASS",
    "pass": "PASS",
    "voice": "VOICE",
    "cypher": "CRYPT",
    "elliptic": "CRYPT",
}


class ChallengePanel(BoxLayout):
    """Single challenge entry with type icon and lock status."""
    def __init__(self, index, caption, challenge_type="", on_click=None, **kwargs):
        super().__init__(orientation='horizontal', size_hint_y=None, height=70,
                         padding=8, spacing=10, **kwargs)
        self._index = index
        self._on_click = on_click

        # Detect challenge type from caption
        cap_lower = caption.lower()
        ctype = "password"
        for key in CHALLENGE_COLORS:
            if key in cap_lower:
                ctype = key
                break

        color = CHALLENGE_COLORS.get(ctype, SECONDARY)
        icon_text = CHALLENGE_ICONS.get(ctype, "???")

        with self.canvas.before:
            Color(*PANEL_BG, 0.9)
            self._bg = Rectangle(pos=self.pos, size=self.size)
            Color(*color[:3], 0.4)
            self._border = Line(rectangle=[*self.pos, *self.size], width=1.2)
        self.bind(pos=self._upd, size=self._upd)

        # Icon box
        icon_box = BoxLayout(size_hint_x=None, width=60, orientation='vertical')
        icon_lbl = Label(text=icon_text, font_name='AeroMatics', font_size='16sp',
                         color=color, halign='center', valign='middle')
        icon_lbl.bind(size=icon_lbl.setter('text_size'))
        idx_lbl = Label(text=f"[{index + 1}]", font_name='AeroMatics', font_size='12sp',
                        color=SECONDARY, halign='center', size_hint_y=None, height=18)
        idx_lbl.bind(size=idx_lbl.setter('text_size'))
        icon_box.add_widget(icon_lbl)
        icon_box.add_widget(idx_lbl)

        # Caption + status
        info_box = BoxLayout(orientation='vertical')
        cap_lbl = Label(text=caption, font_name='AeroMatics', font_size='15sp',
                        color=TEXT_WHITE, halign='left', valign='middle')
        cap_lbl.bind(size=cap_lbl.setter('text_size'))
        status_lbl = Label(text='SYSTEM LOCKED', font_name='AeroMaticsLight',
                           font_size='12sp', color=ALERT, halign='left',
                           size_hint_y=None, height=18)
        status_lbl.bind(size=status_lbl.setter('text_size'))
        info_box.add_widget(cap_lbl)
        info_box.add_widget(status_lbl)

        # Lock indicator
        lock_box = BoxLayout(size_hint_x=None, width=80)
        lock_lbl = Label(text='LOCKED', font_name='AeroMatics', font_size='13sp',
                         color=ALERT, halign='center', valign='middle')
        lock_lbl.bind(size=lock_lbl.setter('text_size'))
        lock_box.add_widget(lock_lbl)

        self.add_widget(icon_box)
        self.add_widget(info_box)
        self.add_widget(lock_box)

    def _upd(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._border.rectangle = [*self.pos, *self.size]

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and touch.button == 'left':
            if self._on_click:
                self._on_click(self._index)
                return True
        return super().on_touch_down(touch)


class HighSecurityRenderer(BaseRenderer):
    """Renders HighSecurityScreen — multi-factor auth with challenge panels."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._auth_label = Label(
            text='SECURITY AUTHENTICATION REQUIRED',
            font_name='AeroMatics', font_size='20sp',
            color=ALERT, size_hint=(1, None), height=30,
            pos_hint={'top': 0.90}, halign='center',
        )
        self._auth_label.bind(size=self._auth_label.setter('text_size'))
        self.add_widget(self._auth_label)

        self._steps_label = Label(
            text='', font_name='AeroMaticsLight', font_size='14sp',
            color=TEXT_DIM, size_hint=(1, None), height=22,
            pos_hint={'top': 0.85}, halign='center',
        )
        self._steps_label.bind(size=self._steps_label.setter('text_size'))
        self.add_widget(self._steps_label)

        self._challenge_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=8)
        self._challenge_list.bind(minimum_height=self._challenge_list.setter('height'))
        scroll = ScrollView(size_hint=(0.6, 0.6), pos_hint={'center_x': 0.5, 'center_y': 0.4})
        scroll.add_widget(self._challenge_list)
        self.add_widget(scroll)
        self._last_options = []

    def on_state_update(self, state):
        options = state.screen_data.get("options", [])
        option_keys = [(o.get("caption", ""), o.get("target", "")) for o in options]
        if option_keys == self._last_options:
            return
        self._last_options = option_keys

        self._steps_label.text = f"{len(options)} verification step{'s' if len(options) != 1 else ''} remaining"

        self._challenge_list.clear_widgets()
        for i, opt in enumerate(options):
            caption = opt.get("caption", f"Challenge {i + 1}")
            panel = ChallengePanel(i, caption, on_click=self._select_challenge)
            self._challenge_list.add_widget(panel)

    def _select_challenge(self, index):
        if self.net:
            self.net.menu_select(index)

    def handle_number_key(self, num):
        idx = num - 1
        if 0 <= idx < len(self._last_options):
            self._select_challenge(idx)
            return True
        return False
