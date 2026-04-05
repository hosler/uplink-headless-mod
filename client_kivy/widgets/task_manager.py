"""TaskManager — floating overlay for CPU allocation across running processes."""
import math
import time
from kivy.uix.widget import Widget
from kivy.properties import BooleanProperty, ObjectProperty
from kivy.graphics import Color, Rectangle, Line, Ellipse
from kivy.core.text import Label as CoreLabel

from theme.colors import (PRIMARY, SECONDARY, TEXT_WHITE, TEXT_DIM, SUCCESS,
                          WARNING, ALERT, PANEL_BG)


class TaskManager(Widget):
    """Floating panel showing running processes with adjustable CPU shares."""
    visible = BooleanProperty(False)
    sidebar = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._max_cpus = 1
        self._gateway_info = {}
        self.bind(visible=self._on_visible, size=self._redraw, pos=self._redraw)

    def _on_visible(self, *_):
        self.opacity = 1 if self.visible else 0
        self.disabled = not self.visible
        if self.visible:
            self._redraw()

    def toggle(self):
        self.visible = not self.visible

    def update_state(self, state):
        gi = state.gateway_info
        if gi:
            self._max_cpus = max(1, gi.get("maxcpus", 1))
            self._gateway_info = gi
        if self.visible:
            self._redraw()

    def _get_running(self):
        if self.sidebar and hasattr(self.sidebar, 'running'):
            return [r for r in self.sidebar.running if r.active]
        return []

    def _ensure_cpu_shares(self, running):
        """Ensure all running apps have a cpu_share, distribute equally for new ones."""
        for r in running:
            if not hasattr(r, 'cpu_share'):
                r.cpu_share = 1

    def _redraw(self, *_args):
        self.canvas.clear()
        if not self.visible:
            return

        running = self._get_running()
        self._ensure_cpu_shares(running)

        pw, ph = self.size
        ox, oy = self.pos
        if pw < 50 or ph < 50:
            return

        # Panel dimensions — centered, sized to content
        panel_w = min(500, int(pw * 0.6))
        row_h = 42
        header_h = 36
        footer_h = 30
        padding = 12
        n_rows = max(len(running), 1)
        panel_h = header_h + n_rows * row_h + footer_h + padding * 2
        panel_h = min(panel_h, int(ph * 0.8))

        px = ox + (pw - panel_w) // 2
        py = oy + (ph - panel_h) // 2

        with self.canvas:
            # Dim background overlay
            Color(0, 0, 0, 0.5)
            Rectangle(pos=self.pos, size=self.size)

            # Panel background
            Color(8 / 255, 14 / 255, 22 / 255, 0.95)
            Rectangle(pos=(px, py), size=(panel_w, panel_h))

            # Panel border
            Color(*PRIMARY[:3], 0.6)
            Line(rectangle=[px, py, panel_w, panel_h], width=1.5)

            # Corner accents
            c = 12
            Color(*PRIMARY[:3], 0.8)
            Line(points=[px, py + c, px, py, px + c, py], width=1.5)
            Line(points=[px + panel_w - c, py, px + panel_w, py, px + panel_w, py + c], width=1.5)
            Line(points=[px, py + panel_h - c, px, py + panel_h, px + c, py + panel_h], width=1.5)
            Line(points=[px + panel_w - c, py + panel_h, px + panel_w, py + panel_h,
                         px + panel_w, py + panel_h - c], width=1.5)

            # Title
            title_cl = CoreLabel(text='T A S K   M A N A G E R', font_size=16,
                                  color=(*PRIMARY[:3], 1.0), bold=True)
            title_cl.refresh()
            ttex = title_cl.texture
            if ttex:
                Color(1, 1, 1, 1)
                ty = py + panel_h - header_h + (header_h - ttex.height) // 2
                Rectangle(texture=ttex,
                          pos=(px + padding, ty),
                          size=ttex.size)

            # CPU count label
            cpu_cl = CoreLabel(text=f'CPUs: {self._max_cpus}', font_size=12,
                                color=(*SECONDARY[:3], 0.8))
            cpu_cl.refresh()
            ctex = cpu_cl.texture
            if ctex:
                Color(1, 1, 1, 1)
                Rectangle(texture=ctex,
                          pos=(px + panel_w - ctex.width - padding, ty),
                          size=ctex.size)

            # Separator under title
            Color(*SECONDARY[:3], 0.3)
            sep_y = py + panel_h - header_h
            Line(points=[px + 8, sep_y, px + panel_w - 8, sep_y], width=0.7)

            # Column headers
            col_x_name = px + padding
            col_x_bar = px + padding + 140
            col_x_pct = px + panel_w - 70
            col_x_btns = px + panel_w - padding - 40

            if running:
                # Calculate total shares for percentage
                total_shares = sum(getattr(r, 'cpu_share', 1) for r in running)
                if total_shares <= 0:
                    total_shares = 1

                # Header labels
                hy = sep_y - 18
                for text, hx in [("PROCESS", col_x_name), ("CPU", col_x_bar), ("%", col_x_pct)]:
                    hcl = CoreLabel(text=text, font_size=10, color=(*TEXT_DIM[:3], 0.7))
                    hcl.refresh()
                    htex = hcl.texture
                    if htex:
                        Color(1, 1, 1, 1)
                        Rectangle(texture=htex, pos=(hx, hy), size=htex.size)

                # Process rows
                bar_w = col_x_pct - col_x_bar - 12
                self._row_rects = []
                for i, ra in enumerate(running):
                    ry = sep_y - 22 - (i + 1) * row_h
                    if ry < py + footer_h:
                        break

                    share = getattr(ra, 'cpu_share', 1)
                    pct = share / total_shares

                    # Row background (alternating)
                    if i % 2 == 0:
                        Color(12 / 255, 20 / 255, 32 / 255, 0.5)
                    else:
                        Color(8 / 255, 14 / 255, 22 / 255, 0.3)
                    Rectangle(pos=(px + 4, ry), size=(panel_w - 8, row_h - 2))

                    # Store row rect for click handling
                    self._row_rects.append((px + 4, ry, panel_w - 8, row_h - 2, i))

                    # Tool color accent
                    Color(*ra.color[:3], 0.7)
                    Line(points=[px + 4, ry, px + 4, ry + row_h - 2], width=2.5)

                    # Icon
                    ico_cl = CoreLabel(text=ra.icon, font_size=13,
                                        color=(*ra.color[:3], 1.0), bold=True)
                    ico_cl.refresh()
                    itex = ico_cl.texture
                    if itex:
                        Color(1, 1, 1, 1)
                        Rectangle(texture=itex,
                                  pos=(col_x_name, ry + (row_h - itex.height) // 2),
                                  size=itex.size)

                    # Name
                    name = ra.title.replace("_", " ")
                    ncl = CoreLabel(text=name, font_size=13, color=(*TEXT_WHITE[:3], 1.0))
                    ncl.refresh()
                    ntex = ncl.texture
                    if ntex:
                        Color(1, 1, 1, 1)
                        Rectangle(texture=ntex,
                                  pos=(col_x_name + 28, ry + (row_h - ntex.height) // 2),
                                  size=ntex.size)

                    # CPU bar background
                    bar_y = ry + (row_h - 14) // 2
                    Color(*PANEL_BG[:3], 0.8)
                    Rectangle(pos=(col_x_bar, bar_y), size=(bar_w, 14))

                    # CPU bar fill
                    fill_w = int(bar_w * pct)
                    if fill_w > 0:
                        Color(*ra.color[:3], 0.7)
                        Rectangle(pos=(col_x_bar, bar_y), size=(fill_w, 14))
                        # Segments
                        seg = 6
                        sx = col_x_bar + seg
                        while sx < col_x_bar + fill_w:
                            Color(*PANEL_BG[:3], 0.5)
                            Rectangle(pos=(sx, bar_y), size=(2, 14))
                            sx += seg + 2

                    # Bar border
                    Color(*SECONDARY[:3], 0.4)
                    Line(rectangle=[col_x_bar, bar_y, bar_w, 14], width=0.7)

                    # Percentage text
                    pct_text = f"{int(pct * 100)}%"
                    pcl = CoreLabel(text=pct_text, font_size=13, color=(*TEXT_WHITE[:3], 1.0))
                    pcl.refresh()
                    ptex = pcl.texture
                    if ptex:
                        Color(1, 1, 1, 1)
                        Rectangle(texture=ptex,
                                  pos=(col_x_pct, ry + (row_h - ptex.height) // 2),
                                  size=ptex.size)

                    # +/- buttons
                    btn_y = ry + (row_h - 18) // 2
                    # Minus
                    Color(*ALERT[:3], 0.8 if share > 1 else 0.3)
                    minus_x = col_x_btns
                    Rectangle(pos=(minus_x, btn_y), size=(18, 18))
                    mcl = CoreLabel(text='-', font_size=14, color=(0, 0, 0, 1), bold=True)
                    mcl.refresh()
                    mtex = mcl.texture
                    if mtex:
                        Color(1, 1, 1, 1)
                        Rectangle(texture=mtex,
                                  pos=(minus_x + (18 - mtex.width) // 2,
                                       btn_y + (18 - mtex.height) // 2),
                                  size=mtex.size)

                    # Plus
                    Color(*SUCCESS[:3], 0.8)
                    plus_x = col_x_btns + 22
                    Rectangle(pos=(plus_x, btn_y), size=(18, 18))
                    pcl2 = CoreLabel(text='+', font_size=14, color=(0, 0, 0, 1), bold=True)
                    pcl2.refresh()
                    ptex2 = pcl2.texture
                    if ptex2:
                        Color(1, 1, 1, 1)
                        Rectangle(texture=ptex2,
                                  pos=(plus_x + (18 - ptex2.width) // 2,
                                       btn_y + (18 - ptex2.height) // 2),
                                  size=ptex2.size)

            else:
                # No processes
                ncl = CoreLabel(text='No running processes', font_size=14,
                                 color=(*TEXT_DIM[:3], 0.6))
                ncl.refresh()
                ntex = ncl.texture
                if ntex:
                    Color(1, 1, 1, 1)
                    Rectangle(texture=ntex,
                              pos=(px + (panel_w - ntex.width) // 2,
                                   py + (panel_h - ntex.height) // 2),
                              size=ntex.size)
                self._row_rects = []

            # Footer separator
            Color(*SECONDARY[:3], 0.3)
            fy = py + footer_h
            Line(points=[px + 8, fy, px + panel_w - 8, fy], width=0.7)

            # Footer hint
            hint_cl = CoreLabel(text='[T] CLOSE    [-] / [+] ADJUST CPU    CLICK ROW TO TOGGLE',
                                 font_size=10, color=(*TEXT_DIM[:3], 0.6))
            hint_cl.refresh()
            htex = hint_cl.texture
            if htex:
                Color(1, 1, 1, 1)
                Rectangle(texture=htex,
                          pos=(px + (panel_w - htex.width) // 2,
                               py + (footer_h - htex.height) // 2),
                          size=htex.size)

    def on_touch_down(self, touch):
        if not self.visible:
            return False
        if not self.collide_point(*touch.pos):
            return False

        running = self._get_running()
        if not running:
            return True  # Consume touch but do nothing

        # Check +/- button clicks
        pw, ph = self.size
        ox, oy = self.pos
        panel_w = min(500, int(pw * 0.6))
        padding = 12
        col_x_btns = ox + (pw - panel_w) // 2 + panel_w - padding - 40

        for rx, ry, rw, rh, idx in getattr(self, '_row_rects', []):
            if idx >= len(running):
                continue
            ra = running[idx]
            if not hasattr(ra, 'cpu_share'):
                ra.cpu_share = 1

            btn_y = ry + (rh - 18) // 2
            tx, ty = touch.pos

            # Minus button
            if col_x_btns <= tx <= col_x_btns + 18 and btn_y <= ty <= btn_y + 18:
                if ra.cpu_share > 1:
                    ra.cpu_share -= 1
                    self._redraw()
                return True

            # Plus button
            plus_x = col_x_btns + 22
            if plus_x <= tx <= plus_x + 18 and btn_y <= ty <= btn_y + 18:
                ra.cpu_share += 1
                self._redraw()
                return True

        return True  # Consume all touches when visible (modal)
