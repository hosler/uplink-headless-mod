"""Login screen — handle + password form."""
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, ObjectProperty
from kivy.clock import Clock
from kivy.app import App


class LoginScreen(Screen):
    error_text = StringProperty("")
    handle_input = ObjectProperty(None)
    password_input = ObjectProperty(None)

    def on_enter(self, *_args):
        """Focus handle input when screen shown."""
        # Schedule focus after a frame so KV bindings are resolved
        Clock.schedule_once(self._focus_handle, 0.2)

    def _focus_handle(self, _dt):
        if self.handle_input:
            self.handle_input.focus = True

    def on_leave(self, *_args):
        """Defocus all inputs when leaving login screen."""
        if self.handle_input:
            self.handle_input.focus = False
        if self.password_input:
            self.password_input.focus = False

    def do_join(self):
        app = App.get_running_app()
        handle = self.handle_input.text.strip() if self.handle_input else ""
        password = self.password_input.text.strip() if self.password_input else ""
        if not handle:
            self.error_text = "Enter a handle"
            return
        # Defocus inputs before transitioning
        if self.handle_input:
            self.handle_input.focus = False
        if self.password_input:
            self.password_input.focus = False
        app.attempt_join(handle, password)

    def set_error(self, msg):
        self.error_text = msg
