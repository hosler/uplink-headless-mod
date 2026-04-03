"""GatewayView — model stats, memory bar, hardware list, file table."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle

from theme.colors import (PRIMARY, SECONDARY, TEXT_WHITE, TEXT_DIM, ROW_ALT,
                          PANEL_BG, SUCCESS, ALERT)
from widgets.hacker_button import HackerButton
from widgets.progress_bar import HackerProgressBar
from tabs.base_tab import BaseTabView


class GatewayView(BaseTabView):
    tab_name = "Gateway"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._title_label.text = "G A T E W A Y"

        content = BoxLayout(orientation='vertical', spacing=8, padding=[20, 0, 20, 10],
                           size_hint=(1, 0.88), pos_hint={'center_x': 0.5, 'y': 0.02})

        # Model name
        self._model_label = Label(text='', font_name='AeroMatics', font_size='22sp',
                                  color=TEXT_WHITE, size_hint_y=None, height=34, halign='left')
        self._model_label.bind(size=self._model_label.setter('text_size'))
        content.add_widget(self._model_label)

        # Stats row
        stats_row = BoxLayout(size_hint_y=None, height=50, spacing=20)
        self._stat_labels = {}
        for stat in ["Modem", "Memory", "Bandwidth", "Max CPUs", "Max Memory"]:
            col = BoxLayout(orientation='vertical')
            lbl = Label(text=stat.upper(), font_name='AeroMatics', font_size='12sp',
                        color=SECONDARY, halign='left', size_hint_y=0.4)
            lbl.bind(size=lbl.setter('text_size'))
            val = Label(text='--', font_name='AeroMatics', font_size='15sp',
                        color=TEXT_WHITE, halign='left', size_hint_y=0.6)
            val.bind(size=val.setter('text_size'))
            col.add_widget(lbl)
            col.add_widget(val)
            self._stat_labels[stat] = val
            stats_row.add_widget(col)
        content.add_widget(stats_row)

        # Memory bar
        mem_row = BoxLayout(size_hint_y=None, height=32, spacing=10)
        mem_lbl = Label(text='MEMORY:', font_name='AeroMatics', font_size='13sp',
                        color=SECONDARY, size_hint_x=None, width=80)
        self._mem_bar = HackerProgressBar(bar_color=PRIMARY, size_hint_x=1,
                                          size_hint_y=None, height=22)
        self._mem_text = Label(text='', font_name='AeroMatics', font_size='13sp',
                               color=TEXT_WHITE, size_hint_x=None, width=120)
        mem_row.add_widget(mem_lbl)
        mem_row.add_widget(self._mem_bar)
        mem_row.add_widget(self._mem_text)
        content.add_widget(mem_row)

        # File list header
        file_header = BoxLayout(size_hint_y=None, height=26, spacing=5)
        for text, w in [('FILENAME', None), ('SIZE', 80), ('ENC', 50), ('CMP', 50)]:
            lbl = Label(text=text, font_name='AeroMatics', font_size='13sp',
                        color=PRIMARY, halign='left',
                        size_hint_x=None if w else 1, width=w or 0)
            lbl.bind(size=lbl.setter('text_size'))
            file_header.add_widget(lbl)
        content.add_widget(file_header)

        # File list
        self._file_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=2)
        self._file_list.bind(minimum_height=self._file_list.setter('height'))
        file_scroll = ScrollView()
        file_scroll.add_widget(self._file_list)
        content.add_widget(file_scroll)

        self.add_widget(content)
        self._last_info = {}
        self._last_files = []

    def on_activate(self):
        super().on_activate()
        if self.net:
            self.net.get_gateway_info()
            self.net.get_gateway_files()

    def on_state_update(self, state):
        gi = state.gateway_info
        if gi and gi != self._last_info:
            self._last_info = gi
            self._model_label.text = gi.get("model", "Unknown Gateway").strip()
            self._stat_labels["Modem"].text = f"{gi.get('modemspeed', 0)} GHz"
            self._stat_labels["Memory"].text = f"{gi.get('memorysize', 0)} GQ"
            self._stat_labels["Bandwidth"].text = f"{gi.get('bandwidth', 0)} GQs"
            self._stat_labels["Max CPUs"].text = str(gi.get("maxcpus", "?"))
            self._stat_labels["Max Memory"].text = f"{gi.get('maxmemory', 0)} GQ"

        # Calculate memory usage from file sizes
        files = state.gateway_files
        total_mem = gi.get("memorysize", 24) if gi else 24
        used_mem = sum(f.get("size", 0) for f in files)
        self._mem_bar.value = used_mem / max(total_mem, 1)
        self._mem_text.text = f"{used_mem}/{total_mem} GQ"

        files = state.gateway_files
        keys = [(f.get("title", ""), f.get("size", 0)) for f in files]
        if keys != self._last_files:
            self._last_files = keys
            self._file_list.clear_widgets()
            for i, f in enumerate(files):
                row = BoxLayout(orientation='horizontal', size_hint_y=None, height=32, spacing=5)
                with row.canvas.before:
                    Color(*(ROW_ALT if i % 2 else PANEL_BG))
                    bg = Rectangle(pos=row.pos, size=row.size)
                row.bind(pos=lambda w, *_, b=bg: setattr(b, 'pos', w.pos),
                         size=lambda w, *_, b=bg: setattr(b, 'size', w.size))

                name = Label(text=f.get("title", "?"), font_name='AeroMatics', font_size='14sp',
                             color=TEXT_WHITE, halign='left')
                name.bind(size=name.setter('text_size'))
                sz = Label(text=f"{f.get('size', 0)} GQ", font_name='AeroMaticsLight',
                           font_size='12sp', color=TEXT_DIM, size_hint_x=None, width=80, halign='right')
                sz.bind(size=sz.setter('text_size'))
                enc = Label(text='ENC' if f.get("encrypted") else '', font_name='AeroMatics',
                            font_size='11sp', color=ALERT if f.get("encrypted") else TEXT_DIM,
                            size_hint_x=None, width=50)
                cmp = Label(text='CMP' if f.get("compressed") else '', font_name='AeroMatics',
                            font_size='11sp', color=SECONDARY if f.get("compressed") else TEXT_DIM,
                            size_hint_x=None, width=50)

                row.add_widget(name)
                row.add_widget(sz)
                row.add_widget(enc)
                row.add_widget(cmp)
                self._file_list.add_widget(row)
