"""SoftwareView — categorized marketplace with version dropdowns."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.graphics import Color, Rectangle, Line

from theme.colors import (PRIMARY, SECONDARY, TEXT_WHITE, TEXT_DIM, PANEL_BG,
                          SUCCESS, ALERT, WARNING, ROW_ALT)
from widgets.hacker_button import HackerButton
from tabs.base_tab import BaseTabView

# Software type IDs from databank.h
SOFTWARETYPE_NONE = 0
SOFTWARETYPE_FILEUTIL = 1
SOFTWARETYPE_HWDRIVER = 2
SOFTWARETYPE_SECURITY = 3
SOFTWARETYPE_CRACKERS = 4
SOFTWARETYPE_BYPASSER = 5
SOFTWARETYPE_LANTOOL = 6
SOFTWARETYPE_HUDUPGRADE = 9
SOFTWARETYPE_OTHER = 10

CATEGORY_INFO = {
    SOFTWARETYPE_FILEUTIL: ("File Utilities", SUCCESS),
    SOFTWARETYPE_HWDRIVER: ("Hardware Drivers", TEXT_DIM),
    SOFTWARETYPE_SECURITY: ("Security", PRIMARY),
    SOFTWARETYPE_CRACKERS: ("Crackers", ALERT),
    SOFTWARETYPE_BYPASSER: ("Bypassers", WARNING),
    SOFTWARETYPE_LANTOOL:  ("LAN Tools", SECONDARY),
    SOFTWARETYPE_HUDUPGRADE: ("HUD Upgrades", (*WARNING[:3], 1)),
    SOFTWARETYPE_OTHER:    ("Other", TEXT_DIM),
    SOFTWARETYPE_NONE:     ("Uncategorized", TEXT_DIM),
}

# Display order for categories
CATEGORY_ORDER = [
    SOFTWARETYPE_CRACKERS, SOFTWARETYPE_SECURITY, SOFTWARETYPE_BYPASSER,
    SOFTWARETYPE_FILEUTIL, SOFTWARETYPE_LANTOOL, SOFTWARETYPE_HUDUPGRADE,
    SOFTWARETYPE_HWDRIVER, SOFTWARETYPE_OTHER, SOFTWARETYPE_NONE,
]


class SoftwareRow(BoxLayout):
    """Single software product row with version dropdown."""
    def __init__(self, title, versions, balance, cat_color, on_buy=None, **kwargs):
        super().__init__(orientation='horizontal', spacing=6, padding=[10, 2], **kwargs)
        self.size_hint = (1, None)
        self.height = 40
        self._title = title
        self._versions = versions
        self._on_buy = on_buy
        self._selected_idx = len(versions) - 1

        with self.canvas.before:
            Color(PANEL_BG[0], PANEL_BG[1], PANEL_BG[2], 0.95)
            self._bg = Rectangle(pos=self.pos, size=self.size)
            Color(*cat_color[:3], 0.6)
            self._accent = Line(points=[self.x, self.y, self.x, self.top], width=2)
        self.bind(pos=self._upd, size=self._upd)

        # Title — 40%
        display = title.replace("_", " ").upper()
        title_lbl = Label(text=display, font_name='AeroMatics', font_size='14sp',
                          color=TEXT_WHITE, size_hint_x=0.40, halign='left',
                          valign='middle')
        title_lbl.bind(size=title_lbl.setter('text_size'))

        # Version — 12%
        ver_labels = [f"v{v.get('version', 1):.0f}" for v in versions]
        if len(versions) > 1:
            self._spinner = Spinner(
                text=ver_labels[self._selected_idx],
                values=ver_labels,
                font_name='AeroMatics', font_size='13sp',
                size_hint_x=0.12, size_hint_y=None, height=30,
                background_color=(0.08, 0.18, 0.28, 1),
                color=PRIMARY,
            )
            self._spinner.bind(text=self._on_version_change)
        else:
            self._spinner = Label(
                text=ver_labels[0], font_name='AeroMatics', font_size='13sp',
                size_hint_x=0.12, color=TEXT_DIM, halign='center', valign='middle')
            self._spinner.bind(size=self._spinner.setter('text_size'))

        # Size — 12%
        sw = versions[self._selected_idx]
        self._size_lbl = Label(text=f"{sw.get('size', 0)} GQ",
                               font_name='AeroMaticsLight', font_size='12sp',
                               color=TEXT_DIM, size_hint_x=0.12, halign='center',
                               valign='middle')
        self._size_lbl.bind(size=self._size_lbl.setter('text_size'))

        # Price — 18%
        cost = sw.get("cost", 0)
        can_afford = balance >= cost
        self._price_lbl = Label(text=f"{cost:,}c", font_name='AeroMatics',
                                font_size='14sp',
                                color=SUCCESS if can_afford else ALERT,
                                size_hint_x=0.18, halign='right', valign='middle')
        self._price_lbl.bind(size=self._price_lbl.setter('text_size'))

        # BUY — 18%
        self._buy_btn = HackerButton(text='BUY', font_size='12sp',
                                     size_hint_x=0.18, size_hint_y=None, height=28,
                                     button_color=SUCCESS if can_afford else TEXT_DIM,
                                     disabled=not can_afford)
        self._buy_btn.bind(on_release=self._do_buy)

        self._balance = balance

        self.add_widget(title_lbl)
        self.add_widget(self._spinner)
        self.add_widget(self._size_lbl)
        self.add_widget(self._price_lbl)
        self.add_widget(self._buy_btn)

    def _upd(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._accent.points = [self.x, self.y, self.x, self.top]

    def _on_version_change(self, spinner, text):
        ver_labels = [f"v{v.get('version', 1):.0f}" for v in self._versions]
        if text in ver_labels:
            self._selected_idx = ver_labels.index(text)
            sw = self._versions[self._selected_idx]
            cost = sw.get("cost", 0)
            can_afford = self._balance >= cost
            self._size_lbl.text = f"{sw.get('size', 0)} GQ"
            self._price_lbl.text = f"{cost:,}c"
            self._price_lbl.color = SUCCESS if can_afford else ALERT
            self._buy_btn.button_color = SUCCESS if can_afford else TEXT_DIM
            self._buy_btn.disabled = not can_afford

    def _do_buy(self, *_):
        if self._on_buy:
            sw = self._versions[self._selected_idx]
            self._on_buy(self._title, sw.get("version"))


class SoftwareView(BaseTabView):
    tab_name = "Software"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._title_label.text = "S O F T W A R E   M A R K E T"
        self._software = []

        self._list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=2,
                               padding=[0, 0, 0, 10])
        self._list.bind(minimum_height=self._list.setter('height'))
        scroll = ScrollView(size_hint=(0.95, 0.85), pos_hint={'center_x': 0.5, 'y': 0.02})
        scroll.add_widget(self._list)
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
        self._list.clear_widgets()

        # Group by title, collect versions
        by_title = {}
        title_type = {}
        for sw in self._software:
            t = sw.get("title", "")
            if t not in by_title:
                by_title[t] = []
                title_type[t] = sw.get("type", SOFTWARETYPE_NONE)
            by_title[t].append(sw)

        for t in by_title:
            by_title[t].sort(key=lambda x: x.get("version", 0))

        # Organize into categories
        categories = {}
        for title, versions in by_title.items():
            type_id = title_type.get(title, SOFTWARETYPE_NONE)
            if type_id not in categories:
                categories[type_id] = []
            categories[type_id].append((title, versions))

        for type_id in categories:
            categories[type_id].sort(key=lambda x: x[0])

        # Build UI in category order
        for type_id in CATEGORY_ORDER:
            if type_id not in categories:
                continue
            cat_name, cat_color = CATEGORY_INFO.get(type_id, ("Other", TEXT_DIM))
            items = categories[type_id]

            # Category header
            header = BoxLayout(size_hint_y=None, height=34, padding=[10, 0])
            with header.canvas.before:
                Color(*cat_color[:3], 0.15)
                hdr_bg = Rectangle(pos=header.pos, size=header.size)
                Color(*cat_color[:3], 0.4)
                hdr_line = Line(points=[0, 0, 0, 0], width=1)
            def _upd_hdr(w, *_, bg=hdr_bg, ln=hdr_line):
                bg.pos = w.pos
                bg.size = w.size
                ln.points = [w.x, w.y, w.right, w.y]
            header.bind(pos=_upd_hdr, size=_upd_hdr)

            cat_lbl = Label(text=f"[ {cat_name.upper()} ]", font_name='AeroMatics',
                            font_size='14sp', color=cat_color, halign='left',
                            valign='middle', size_hint_x=0.7)
            cat_lbl.bind(size=cat_lbl.setter('text_size'))
            count_lbl = Label(text=f"{len(items)} tool{'s' if len(items) != 1 else ''}",
                              font_name='AeroMaticsLight', font_size='11sp',
                              color=(*cat_color[:3], 0.5), halign='right',
                              valign='middle', size_hint_x=0.3)
            count_lbl.bind(size=count_lbl.setter('text_size'))
            header.add_widget(cat_lbl)
            header.add_widget(count_lbl)
            self._list.add_widget(header)

            # Column headers
            col_header = BoxLayout(size_hint_y=None, height=20, spacing=6, padding=[10, 0])
            for text, w in [('SOFTWARE', 0.40), ('VER', 0.12), ('SIZE', 0.12),
                            ('COST', 0.18), ('', 0.18)]:
                lbl = Label(text=text, font_name='AeroMaticsLight', font_size='10sp',
                            color=(*TEXT_DIM[:3], 0.5), size_hint_x=w,
                            halign='left' if text == 'SOFTWARE' else 'center',
                            valign='middle')
                lbl.bind(size=lbl.setter('text_size'))
                col_header.add_widget(lbl)
            self._list.add_widget(col_header)

            # Software rows
            for title, versions in items:
                row = SoftwareRow(title, versions, balance, cat_color, on_buy=self._buy)
                self._list.add_widget(row)

    def _buy(self, title, version=None):
        if self.net:
            self.net.buy_software(title, version=version)
            if self.statusbar:
                ver_str = f" v{version:.0f}" if version else ""
                self.statusbar.show(f"Purchased {title}{ver_str}")
