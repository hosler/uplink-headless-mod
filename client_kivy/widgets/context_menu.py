"""Context menu — right-click popup with options."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, Line
from kivy.core.window import Window

from theme.colors import PRIMARY, TEXT_WHITE, TEXT_DIM, PANEL_BG, SECONDARY


class ContextMenu(BoxLayout):
    """Popup context menu at a given position."""

    def __init__(self, items, pos, on_dismiss=None, **kwargs):
        """items: list of (label, callback) tuples."""
        super().__init__(orientation='vertical', size_hint=(None, None),
                         spacing=1, padding=2, **kwargs)
        self.width = 200
        self.height = len(items) * 30 + 4
        self._on_dismiss = on_dismiss
        self._items = items

        with self.canvas.before:
            Color(15/255, 25/255, 40/255, 0.95)
            self._bg = Rectangle(pos=self.pos, size=self.size)
            Color(*PRIMARY[:3], 0.7)
            self._border = Line(rectangle=[*self.pos, *self.size], width=1)
        self.bind(pos=self._upd, size=self._upd)

        for label_text, callback in items:
            item = ContextMenuItem(label_text, callback, on_dismiss=self.dismiss)
            self.add_widget(item)

        # Position near click — pos should be in parent-local coords
        x = min(pos[0], Window.width - self.width - 5)
        y = max(pos[1] - self.height, 5)
        self.pos = (x, y)
        # Store window pos for dismissal hit-test
        self._window_pos = pos

    def _upd(self, *_):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._border.rectangle = [*self.pos, *self.size]

    def show(self, parent=None):
        """Add to window root so positioning uses window coords."""
        Window.add_widget(self)

    def dismiss(self):
        if self.parent:
            self.parent.remove_widget(self)
        if self._on_dismiss:
            self._on_dismiss()

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        # Click outside dismisses
        self.dismiss()
        return True


class ContextMenuItem(BoxLayout):
    """Single item in a context menu."""

    def __init__(self, text, callback, on_dismiss=None, **kwargs):
        super().__init__(size_hint_y=None, height=28, padding=[8, 2], **kwargs)
        self._callback = callback
        self._on_dismiss = on_dismiss

        self._label = Label(text=text, font_name='AeroMatics', font_size='13sp',
                            color=PRIMARY, halign='left', valign='middle')
        self._label.bind(size=self._label.setter('text_size'))
        self.add_widget(self._label)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and touch.button == 'left':
            if self._callback:
                self._callback()
            if self._on_dismiss:
                self._on_dismiss()
            return True
        return super().on_touch_down(touch)
