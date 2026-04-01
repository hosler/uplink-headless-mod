"""DialogRenderer — DialogScreen with dynamic form fields."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.core.window import Window

from theme.colors import PRIMARY, TEXT_DIM, TEXT_WHITE, SECONDARY
from widgets.hacker_text_input import HackerTextInput
from widgets.hacker_button import HackerButton
from browser.renderers.base import BaseRenderer


class DialogRenderer(BaseRenderer):
    """Renders DialogScreen — form with text fields and OK button."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._fields = {}  # button_name -> TextInput
        self._panel = BoxLayout(
            orientation='vertical', spacing=10, padding=[30, 20],
            size_hint=(0.5, None), height=400,
            pos_hint={'center_x': 0.5, 'center_y': 0.42},
        )

        # Body text (for dialogs with just a message)
        self._body_label = Label(
            text='', font_name='AeroMaticsLight', font_size='15sp',
            color=TEXT_WHITE, halign='left', valign='top',
            size_hint_y=None, height=0,
        )
        self._body_label.bind(size=self._body_label.setter('text_size'),
                              texture_size=self._resize_body)

        self._ok_btn = HackerButton(
            text='CONTINUE', size_hint_y=None, height=44,
            font_size='16sp',
        )
        self._ok_btn.bind(on_release=lambda *_: self._on_ok())

        self.add_widget(self._panel)
        self._last_buttons = []
        self._kb_bound = False

    def _resize_body(self, *_):
        self._body_label.height = max(0, self._body_label.texture_size[1] + 10)

    def on_state_update(self, state):
        buttons = state.buttons
        btn_keys = [(b.get("name", ""), b.get("caption", "")) for b in buttons]
        if btn_keys == self._last_buttons:
            return
        self._last_buttons = btn_keys

        self._panel.clear_widgets()
        self._fields.clear()

        # Show body/message text from screen data
        body = state.screen_data.get("body", "")
        if not body:
            # Some dialogs put the message in options
            options = state.screen_data.get("options", [])
            body = "\n".join(o.get("caption", "") for o in options if o.get("caption"))

        if body:
            self._body_label.text = body
            self._panel.add_widget(self._body_label)

        for btn in buttons:
            name = btn.get("name", "")
            caption = btn.get("caption", name)
            value = btn.get("value", "")

            # Skip non-input buttons or internal eclipse buttons
            if not name or name.startswith("_"):
                continue
            # Skip buttons that look like display-only (no editable field)
            if not caption and not value:
                continue

            lbl = Label(
                text=caption.upper(),
                font_name='AeroMaticsLight', font_size='13sp',
                color=TEXT_DIM, size_hint_y=None, height=20,
                halign='left',
            )
            lbl.bind(size=lbl.setter('text_size'))

            inp = HackerTextInput(
                text=value, hint_text=f'Enter {caption}...',
                size_hint_y=None, height=38,
            )
            inp.bind(on_text_validate=lambda *_: self._on_ok())
            self._fields[name] = inp
            self._panel.add_widget(lbl)
            self._panel.add_widget(inp)

        self._panel.add_widget(self._ok_btn)

        # Adjust panel height
        body_h = self._body_label.height if body else 0
        self._panel.height = body_h + len(self._fields) * 60 + 100

    def _on_ok(self):
        if self.net:
            for name, inp in self._fields.items():
                val = inp.text.strip()
                if val:
                    self.net.set_field(name, val)
            self.net.dialog_ok()

    def handle_enter_key(self):
        self._on_ok()
        return True
