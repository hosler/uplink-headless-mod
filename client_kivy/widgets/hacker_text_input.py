"""HackerTextInput — cyan-bordered text input widget."""
from kivy.uix.textinput import TextInput
from kivy.properties import ColorProperty
from kivy.app import App
from theme.colors import PRIMARY, PANEL_BG, TEXT_WHITE


class HackerTextInput(TextInput):
    border_color = ColorProperty(PRIMARY)

    def __init__(self, **kwargs):
        kwargs.setdefault('font_name', 'AeroMatics')
        kwargs.setdefault('font_size', '18sp')
        kwargs.setdefault('multiline', False)
        kwargs.setdefault('background_color', (*PANEL_BG[:3], 0.9))
        kwargs.setdefault('foreground_color', TEXT_WHITE)
        kwargs.setdefault('cursor_color', PRIMARY)
        kwargs.setdefault('padding', [10, 8])
        kwargs.setdefault('background_normal', '')
        kwargs.setdefault('background_active', '')
        super().__init__(**kwargs)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.focus = True
        return super().on_touch_down(touch)

    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        """Override to forward Enter/Escape/F-keys to the app."""
        key = keycode[0] if isinstance(keycode, tuple) else keycode
        # Enter: let on_text_validate fire, then also notify the app
        if key == 13:
            # Call parent to trigger on_text_validate
            result = super().keyboard_on_key_down(window, keycode, text, modifiers)
            # Also forward to app's key handler for dialog/message progression
            app = App.get_running_app()
            if app and hasattr(app, '_on_key_down'):
                app._on_key_down(window, key, keycode[1] if isinstance(keycode, tuple) else 0, '', modifiers)
            return result
        # Escape: forward to app, don't consume
        if key == 27:
            self.focus = False
            app = App.get_running_app()
            if app and hasattr(app, '_on_key_down'):
                app._on_key_down(window, key, 0, '', modifiers)
            return True
        # F-keys: forward to app
        if 282 <= key <= 289:
            app = App.get_running_app()
            if app and hasattr(app, '_on_key_down'):
                app._on_key_down(window, key, 0, '', modifiers)
            return True
        return super().keyboard_on_key_down(window, keycode, text, modifiers)
