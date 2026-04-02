"""BaseRenderer — common base class for all server screen renderers."""
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import ObjectProperty
from kivy.graphics import Color, Line

from theme.colors import PRIMARY, SECONDARY, TEXT_DIM, TEXT_WHITE, PANEL_BG
from widgets.hacker_button import HackerButton


class BaseRenderer(RelativeLayout):
    """Base class for server screen renderers.

    Subclasses override on_state_update(state) to populate their UI.
    """
    net = ObjectProperty(None, allownone=True)
    statusbar = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._title_label = Label(
            text='', font_name='AeroMatics', font_size='20sp',
            color=PRIMARY, size_hint=(1, None), height=36,
            pos_hint={'top': 0.97}, halign='center',
        )
        self._title_label.bind(size=self._title_label.setter('text_size'))

        self._subtitle_label = Label(
            text='', font_name='AeroMaticsLight', font_size='14sp',
            color=TEXT_DIM, size_hint=(1, None), height=24,
            pos_hint={'top': 0.93}, halign='center',
        )
        self._subtitle_label.bind(size=self._subtitle_label.setter('text_size'))

        # Back button (top-left)
        self._back_btn = HackerButton(
            text='\u25c0 BACK', font_size='13sp',
            size_hint=(None, None), size=(90, 30),
            pos_hint={'x': 0.02, 'top': 0.97},
            button_color=SECONDARY,
        )
        self._back_btn.bind(on_release=lambda *_: self._go_back())

        self.add_widget(self._title_label)
        self.add_widget(self._subtitle_label)
        self.add_widget(self._back_btn)

    def _go_back(self):
        if self.net:
            self.net.back()

    def update_state(self, state):
        """Called each poll cycle. Update title and delegate to subclass."""
        self._title_label.text = state.screen_data.get("maintitle", "").upper()
        self._subtitle_label.text = state.screen_data.get("subtitle", "")
        self.on_state_update(state)

    def on_state_update(self, state):
        """Override in subclasses to handle state changes."""
        pass

    def on_enter(self):
        """Called when this renderer becomes active."""
        pass

    def on_leave(self):
        """Called when this renderer is being replaced."""
        pass
