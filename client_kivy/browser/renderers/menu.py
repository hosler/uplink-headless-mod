"""MenuRenderer — renders MenuScreen and HighSecurityScreen options."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.app import App

from theme.colors import PRIMARY, SECONDARY, TEXT_WHITE, TEXT_DIM, ROW_ALT, PANEL_BG, ROW_HOVER
from kivy.graphics import Color, Rectangle, Triangle
from browser.renderers.base import BaseRenderer


class MenuOptionRow(BoxLayout):
    """Single menu option with triangle pointer and number shortcut."""

    def __init__(self, index, caption, target, on_click=None, **kwargs):
        super().__init__(orientation='horizontal', size_hint_y=None, height=44, **kwargs)
        self._index = index
        self._target = target
        self._on_click = on_click
        self._hovered = False

        with self.canvas.before:
            self._bg_color = Color(*(ROW_ALT if index % 2 else PANEL_BG))
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update, size=self._update)

        # Number shortcut
        num = Label(
            text=f"[{index + 1}]" if index < 9 else "",
            font_name='AeroMatics', font_size='14sp',
            color=SECONDARY, size_hint_x=None, width=44,
            halign='center', valign='middle',
        )
        num.bind(size=num.setter('text_size'))

        # Triangle pointer
        self._pointer = Label(
            text='\u25b6', font_size='12sp',
            color=PRIMARY, size_hint_x=None, width=30,
            halign='center', valign='middle',
        )
        self._pointer.bind(size=self._pointer.setter('text_size'))

        # Caption
        cap = Label(
            text=caption, font_name='AeroMatics', font_size='18sp',
            color=TEXT_WHITE, halign='left', valign='middle',
        )
        cap.bind(size=cap.setter('text_size'))

        self.add_widget(num)
        self.add_widget(self._pointer)
        self.add_widget(cap)

    def _update(self, *_args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if self._on_click:
                self._on_click(self._target, self._index)
            return True
        return super().on_touch_down(touch)


class MenuRenderer(BaseRenderer):
    """Renders MenuScreen — vertical list of navigable options."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._list_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self._list_layout.bind(minimum_height=self._list_layout.setter('height'))

        scroll = ScrollView(
            size_hint=(0.55, 0.7),
            pos_hint={'center_x': 0.5, 'center_y': 0.42},
        )
        scroll.add_widget(self._list_layout)
        self.add_widget(scroll)
        self._last_options = []

    def on_state_update(self, state):
        options = state.screen_data.get("options", [])
        # Only rebuild if options changed
        option_keys = [(o.get("caption", ""), o.get("target", "")) for o in options]
        if option_keys == self._last_options:
            return
        self._last_options = option_keys

        self._list_layout.clear_widgets()
        for i, opt in enumerate(options):
            caption = opt.get("caption", f"Option {i + 1}")
            target = opt.get("target", "")
            row = MenuOptionRow(i, caption, target, on_click=self._select_option)
            self._list_layout.add_widget(row)

    def _select_option(self, target, index):
        if self.net:
            self.net.menu_select(index)

    def handle_number_key(self, num):
        """Handle 1-9 key for menu selection."""
        options = self._last_options
        idx = num - 1
        if 0 <= idx < len(options):
            target = options[idx][1]
            self._select_option(target, idx)
            return True
        return False
