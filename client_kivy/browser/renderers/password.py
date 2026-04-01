"""PasswordRenderer — PasswordScreen/UserIDScreen + crack animation."""
import time
import random
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.app import App

from theme.colors import PRIMARY, SECONDARY, TEXT_WHITE, TEXT_DIM, SUCCESS, ALERT
from widgets.hacker_text_input import HackerTextInput
from widgets.hacker_button import HackerButton
from widgets.progress_bar import HackerProgressBar
from browser.renderers.base import BaseRenderer


class PasswordRenderer(BaseRenderer):
    """Renders PasswordScreen and UserIDScreen with crack animation."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cracking = False
        self._crack_start = 0
        self._crack_duration = 3.0
        self._crack_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        self._crack_event = None
        self._target_user = ""
        self._target_pass = ""

        # Center panel
        panel = BoxLayout(
            orientation='vertical', spacing=10, padding=[30, 20],
            size_hint=(0.45, None), height=320,
            pos_hint={'center_x': 0.5, 'center_y': 0.42},
        )

        self._auth_label = Label(
            text='AUTHENTICATION REQUIRED',
            font_name='AeroMatics', font_size='18sp',
            color=ALERT, size_hint_y=None, height=30,
            halign='center',
        )
        self._auth_label.bind(size=self._auth_label.setter('text_size'))

        # User ID field
        self._user_label = Label(
            text='USER ID', font_name='AeroMaticsLight', font_size='13sp',
            color=TEXT_DIM, size_hint_y=None, height=20,
            halign='left',
        )
        self._user_label.bind(size=self._user_label.setter('text_size'))
        self._user_input = HackerTextInput(
            hint_text='Enter username...', size_hint_y=None, height=40,
        )
        self._user_input.bind(on_text_validate=self._on_submit)

        # Password field
        self._pass_label = Label(
            text='PASSWORD', font_name='AeroMaticsLight', font_size='13sp',
            color=TEXT_DIM, size_hint_y=None, height=20,
            halign='left',
        )
        self._pass_label.bind(size=self._pass_label.setter('text_size'))
        self._pass_input = HackerTextInput(
            hint_text='Enter password...', password=True,
            size_hint_y=None, height=40,
        )
        self._pass_input.bind(on_text_validate=self._on_submit)

        # Crack display
        self._crack_label = Label(
            text='', font_name='AeroMatics', font_size='22sp',
            color=SUCCESS, size_hint_y=None, height=36,
            halign='center',
        )
        self._crack_label.bind(size=self._crack_label.setter('text_size'))

        # Progress bar (for cracking)
        self._crack_progress = HackerProgressBar(
            size_hint=(1, None), height=14,
            bar_color=PRIMARY,
        )
        self._crack_progress.opacity = 0

        # Submit button
        self._submit_btn = HackerButton(
            text='SUBMIT', size_hint_y=None, height=40,
        )
        self._submit_btn.bind(on_release=lambda *_: self._on_submit())

        panel.add_widget(self._auth_label)
        panel.add_widget(self._user_label)
        panel.add_widget(self._user_input)
        panel.add_widget(self._pass_label)
        panel.add_widget(self._pass_input)
        panel.add_widget(self._crack_label)
        panel.add_widget(self._crack_progress)
        panel.add_widget(self._submit_btn)

        self.add_widget(panel)

    def _on_submit(self, *_args):
        user = self._user_input.text.strip()
        pw = self._pass_input.text.strip()
        if self.net:
            if user:
                self.net.submit_password(pw, user)
            else:
                self.net.submit_password(pw)

    def on_state_update(self, state):
        screen_type = state.screen_type
        if screen_type == "UserIDScreen":
            self._user_label.opacity = 1
            self._user_input.opacity = 1
            self._user_input.disabled = False
        else:
            self._user_label.opacity = 0
            self._user_input.opacity = 0
            self._user_input.disabled = True

        # Check for credentials from cracking
        creds = state.credentials
        if creds and self._cracking:
            # Cracking finished — fill in results
            admin = next((c for c in creds if c.get("name") == "admin"), None)
            if admin:
                self._target_user = admin.get("name", "")
                self._target_pass = admin.get("password", "")

    def start_crack(self):
        """Begin the password cracking animation."""
        if self._cracking:
            return
        self._cracking = True
        self._crack_start = time.time()
        self._crack_progress.opacity = 1
        self._crack_label.text = "DECRYPTING..."
        if self.net:
            self.net.crack_password()
        self._crack_event = Clock.schedule_interval(self._animate_crack, 1 / 20)

    def _animate_crack(self, _dt):
        elapsed = time.time() - self._crack_start
        progress = min(1.0, elapsed / self._crack_duration)
        self._crack_progress.value = progress

        # Character cycling display
        if self._target_pass:
            revealed = int(len(self._target_pass) * progress)
            display = self._target_pass[:revealed]
            remaining = len(self._target_pass) - revealed
            display += ''.join(random.choice(self._crack_chars) for _ in range(remaining))
            self._crack_label.text = display

        if progress >= 1.0:
            self._finish_crack()

    def _finish_crack(self):
        if self._crack_event:
            self._crack_event.cancel()
        self._cracking = False
        self._crack_progress.opacity = 0

        if self._target_user and self._target_pass:
            self._user_input.text = self._target_user
            self._pass_input.text = self._target_pass
            self._crack_label.text = f"CRACKED: {self._target_user}/{self._target_pass}"
            self._crack_label.color = SUCCESS
            # Auto-submit
            if self.net:
                self.net.submit_password(self._target_pass, self._target_user)

    def on_leave(self):
        if self._crack_event:
            self._crack_event.cancel()
