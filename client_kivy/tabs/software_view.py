"""SoftwareView — card-style marketplace with dark cyberpunk cards."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle, Line

from theme.colors import (PRIMARY, SECONDARY, TEXT_WHITE, TEXT_DIM, PANEL_BG,
                          SUCCESS, ALERT, WARNING, ROW_ALT)
from widgets.hacker_button import HackerButton
from tabs.base_tab import BaseTabView

# Software category colors
CATEGORY_COLORS = {
    "Security": PRIMARY,
    "Cracker": ALERT,
    "Network": SECONDARY,
    "Utility": SUCCESS,
    "default": TEXT_DIM,
}


class SoftwareCard(BoxLayout):
    """Single software product card — dark themed with colored border."""
    def __init__(self, sw, balance, on_buy=None, **kwargs):
        super().__init__(orientation='vertical', spacing=4, padding=10, **kwargs)
        self.size_hint = (1, None)
        self.height = 130

        title = sw.get("title", "?")
        version = sw.get("version", "1.0")
        cost = sw.get("cost", 0)
        category = sw.get("category", "")
        description = sw.get("description", "")
        can_afford = balance >= cost

        cat_color = CATEGORY_COLORS.get(category, CATEGORY_COLORS["default"])

        # Dark card background with colored border
        with self.canvas.before:
            # Dark fill
            Color(PANEL_BG[0], PANEL_BG[1], PANEL_BG[2], 0.95)
            self._bg = Rectangle(pos=self.pos, size=self.size)
            # Colored border
            Color(*cat_color[:3], 0.5)
            self._border = Line(rectangle=[*self.pos, *self.size], width=1.1)
            # Top accent line (category color)
            Color(*cat_color[:3], 0.8)
            self._top_line = Line(points=[self.x, self.top, self.right, self.top], width=2)
        self.bind(pos=self._upd, size=self._upd)

        # Title
        title_lbl = Label(text=title.upper(), font_name='AeroMatics', font_size='14sp',
                          color=cat_color, size_hint_y=None, height=20, halign='left',
                          markup=False)
        title_lbl.bind(size=title_lbl.setter('text_size'))

        # Version + category
        meta = Label(text=f"v{version}  |  {category}", font_name='AeroMaticsLight',
                     font_size='10sp', color=TEXT_DIM, size_hint_y=None, height=14, halign='left')
        meta.bind(size=meta.setter('text_size'))

        # Description (truncated)
        desc_text = description[:50] + "..." if len(description) > 50 else description
        desc = Label(text=desc_text, font_name='AeroMaticsLight', font_size='11sp',
                     color=(*TEXT_DIM[:3], 0.7), halign='left', valign='top',
                     size_hint_y=1)
        desc.bind(size=desc.setter('text_size'))

        # Price + buy row
        bottom = BoxLayout(size_hint_y=None, height=28, spacing=8)
        price_color = SUCCESS if can_afford else ALERT
        price = Label(text=f"{cost:,}c", font_name='AeroMatics', font_size='14sp',
                      color=price_color, size_hint_x=0.5, halign='left')
        price.bind(size=price.setter('text_size'))
        buy_btn = HackerButton(text='BUY', font_size='11sp', size_hint_x=0.5,
                               button_color=SUCCESS if can_afford else TEXT_DIM,
                               disabled=not can_afford)
        buy_btn.bind(on_release=lambda *_: on_buy(title) if on_buy else None)
        bottom.add_widget(price)
        bottom.add_widget(buy_btn)

        self.add_widget(title_lbl)
        self.add_widget(meta)
        self.add_widget(desc)
        self.add_widget(bottom)

    def _upd(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._border.rectangle = [*self.pos, *self.size]
        self._top_line.points = [self.x, self.top, self.right, self.top]


class SoftwareView(BaseTabView):
    tab_name = "Software"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._title_label.text = "S O F T W A R E   M A R K E T"
        self._software = []

        self._grid = GridLayout(cols=3, spacing=10, size_hint_y=None, padding=10,
                                row_default_height=130, row_force_default=True)
        self._grid.bind(minimum_height=self._grid.setter('height'))
        scroll = ScrollView(size_hint=(0.95, 0.85), pos_hint={'center_x': 0.5, 'y': 0.02})
        scroll.add_widget(self._grid)
        self.add_widget(scroll)

    def on_activate(self):
        super().on_activate()
        if self.net:
            self.net.get_software_list()

    def on_state_update(self, state):
        sw = state.software_list
        keys = [(s.get("title", ""), s.get("version", "")) for s in sw]
        old_keys = [(s.get("title", ""), s.get("version", "")) for s in self._software]
        if keys != old_keys or state.balance != getattr(self, '_last_bal', -1):
            self._software = sw[:]
            self._last_bal = state.balance
            self._rebuild(state.balance)

    def _rebuild(self, balance):
        self._grid.clear_widgets()
        for sw in self._software:
            card = SoftwareCard(sw, balance, on_buy=self._buy)
            self._grid.add_widget(card)

    def _buy(self, title):
        if self.net:
            self.net.buy_software(title)
            if self.statusbar:
                self.statusbar.show(f"Purchased {title}")
