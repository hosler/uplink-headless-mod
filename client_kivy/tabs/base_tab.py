"""BaseTabView — common base for content tab views."""
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.label import Label
from kivy.properties import StringProperty, ObjectProperty

from theme.colors import PRIMARY, SECONDARY, TEXT_DIM, SUCCESS


class BaseTabView(RelativeLayout):
    """Base class for content tab views (Email, Gateway, etc.)."""
    tab_name = StringProperty("")
    net = ObjectProperty(None, allownone=True)
    statusbar = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._data_requested = False
        self._title_label = Label(
            text='', font_name='AeroMatics', font_size='28sp',
            color=PRIMARY, size_hint=(None, None), size=(400, 40),
            pos_hint={'x': 0.04, 'top': 0.97},
        )
        self.add_widget(self._title_label)
        self._balance_label = Label(
            text='', font_name='AeroMatics', font_size='16sp',
            color=SUCCESS, size_hint=(None, None), size=(200, 28),
            pos_hint={'right': 0.96, 'top': 0.97},
            halign='right',
        )
        self._balance_label.bind(size=self._balance_label.setter('text_size'))
        self.add_widget(self._balance_label)

    def on_activate(self):
        """Called when this tab becomes active. Request data."""
        self._data_requested = False

    def update_state(self, state):
        """Called each poll cycle."""
        self._balance_label.text = f"Balance: {state.balance:,}c"
        self.on_state_update(state)

    def on_state_update(self, state):
        """Override in subclasses."""
        pass
