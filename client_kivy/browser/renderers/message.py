"""MessageRenderer — MessageScreen with panel text and CONTINUE button."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

from theme.colors import PRIMARY, TEXT_WHITE, TEXT_DIM
from widgets.hacker_button import HackerButton
from browser.renderers.base import BaseRenderer


class MessageRenderer(BaseRenderer):
    """Renders MessageScreen — informational panel with CONTINUE."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._body = Label(
            text='', font_name='AeroMaticsLight', font_size='16sp',
            color=TEXT_WHITE, halign='left', valign='top',
            size_hint=(1, None),
            text_size=(None, None),
            markup=True,
        )
        self._body.bind(texture_size=self._resize_body)

        scroll = ScrollView(
            size_hint=(0.6, 0.55),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
        )
        scroll.add_widget(self._body)

        self._continue_btn = HackerButton(
            text='CONTINUE',
            size_hint=(0.25, None), height=40,
            pos_hint={'center_x': 0.5, 'y': 0.08},
        )
        self._continue_btn.bind(on_release=lambda *_: self._on_continue())

        self.add_widget(scroll)
        self.add_widget(self._continue_btn)
        self._last_text = ""

    def _resize_body(self, *_args):
        self._body.height = max(self._body.texture_size[1], 100)

    def on_state_update(self, state):
        # Message body from screen_data
        body = state.screen_data.get("body", "")
        if not body:
            # Try options/items
            items = state.screen_data.get("options", [])
            body = "\n".join(o.get("caption", "") for o in items if o.get("caption"))
        if body != self._last_text:
            self._last_text = body
            self._body.text = body
            # Set text_size for wrapping
            self._body.text_size = (self._body.parent.width - 40 if self._body.parent else 600, None)

    def _on_continue(self):
        if self.net:
            # Click the messagescreen_click button (same as pygame client)
            for btn in self.net.state.buttons:
                if "messagescreen_click" in btn.get("name", ""):
                    self.net.send({"cmd": "click", "button": btn["name"]}, refresh_state=True)
                    return
            self.net.back()

    def handle_enter_key(self):
        self._on_continue()
        return True
