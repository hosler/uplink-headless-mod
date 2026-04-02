"""EmailView — two-panel inbox: message list + body reader."""
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle, Line

from theme.colors import (PRIMARY, SECONDARY, TEXT_WHITE, TEXT_DIM, ROW_ALT,
                          PANEL_BG, SUCCESS, ROW_HOVER, ROW_SELECTED)
from widgets.hacker_button import HackerButton
from widgets.hacker_text_input import HackerTextInput
from tabs.base_tab import BaseTabView


class EmailView(BaseTabView):
    tab_name = "Email"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._title_label.text = "E M A I L"
        self._selected = -1
        self._messages = []

        # Two-panel layout
        panels = BoxLayout(orientation='horizontal', spacing=10, padding=[20, 0, 20, 10],
                          size_hint=(1, 0.88), pos_hint={'center_x': 0.5, 'y': 0.02})

        # Left panel: message list
        left = BoxLayout(orientation='vertical', size_hint_x=0.4, spacing=4)

        # Header
        header = BoxLayout(size_hint_y=None, height=28, spacing=5)
        for text, w in [('FROM', 0.35), ('SUBJECT', 0.65)]:
            lbl = Label(text=text, font_name='AeroMatics', font_size='13sp',
                        color=PRIMARY, size_hint_x=w, halign='left')
            lbl.bind(size=lbl.setter('text_size'))
            header.add_widget(lbl)
        left.add_widget(header)

        self._msg_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=2)
        self._msg_list.bind(minimum_height=self._msg_list.setter('height'))
        msg_scroll = ScrollView()
        msg_scroll.add_widget(self._msg_list)
        left.add_widget(msg_scroll)

        # Right panel: body
        right = BoxLayout(orientation='vertical', size_hint_x=0.6, padding=[10, 0])

        self._body_from = Label(text='', font_name='AeroMatics', font_size='16sp',
                                color=TEXT_WHITE, size_hint_y=None, height=26, halign='left')
        self._body_from.bind(size=self._body_from.setter('text_size'))
        self._body_subject = Label(text='', font_name='AeroMatics', font_size='16sp',
                                   color=PRIMARY, size_hint_y=None, height=26, halign='left')
        self._body_subject.bind(size=self._body_subject.setter('text_size'))
        self._body_text = Label(text='Select a message to read', font_name='AeroMaticsLight',
                                font_size='15sp', color=TEXT_WHITE, halign='left', valign='top',
                                size_hint_y=None, markup=False)
        self._body_text.bind(texture_size=self._resize_body)

        body_scroll = ScrollView()
        body_scroll.add_widget(self._body_text)

        right.add_widget(self._body_from)
        right.add_widget(self._body_subject)
        right.add_widget(body_scroll)

        # Compose button
        self._compose_btn = HackerButton(
            text='COMPOSE EMAIL', size_hint=(None, None), size=(180, 34),
        )
        self._compose_btn.bind(on_release=lambda *_: self._start_compose())
        right.add_widget(self._compose_btn)

        panels.add_widget(left)
        panels.add_widget(right)
        self.add_widget(panels)

        # Compose state
        self._composing = False
        self._compose_widgets = None

    def _resize_body(self, *_):
        self._body_text.height = max(200, self._body_text.texture_size[1])

    def on_activate(self):
        super().on_activate()
        if self.net:
            self.net.get_inbox()

    def on_state_update(self, state):
        msgs = state.inbox
        if msgs != self._messages:
            self._messages = msgs[:]
            self._rebuild_list()

    def _rebuild_list(self):
        self._msg_list.clear_widgets()
        for i, msg in enumerate(self._messages):
            sender = msg.get("from", "")[:25]
            subject = msg.get("subject", "")[:50]

            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=34, spacing=5)
            with row.canvas.before:
                c = Color(*(ROW_ALT if i % 2 else PANEL_BG))
                bg = Rectangle(pos=row.pos, size=row.size)
            row.bind(pos=lambda w, *_, b=bg: setattr(b, 'pos', w.pos),
                     size=lambda w, *_, b=bg: setattr(b, 'size', w.size))

            from_lbl = Label(text=sender, font_name='AeroMatics', font_size='14sp',
                             color=TEXT_WHITE, size_hint_x=0.35, halign='left')
            from_lbl.bind(size=from_lbl.setter('text_size'))
            subj_lbl = Label(text=subject, font_name='AeroMaticsLight', font_size='13sp',
                             color=TEXT_DIM, size_hint_x=0.65, halign='left')
            subj_lbl.bind(size=subj_lbl.setter('text_size'))

            row.add_widget(from_lbl)
            row.add_widget(subj_lbl)

            idx = i
            row.bind(on_touch_down=lambda w, t, i=idx: self._select(i) if w.collide_point(*t.pos) else False)
            self._msg_list.add_widget(row)

    def _select(self, idx):
        self._selected = idx
        if 0 <= idx < len(self._messages):
            msg = self._messages[idx]
            self._body_from.text = f"From: {msg.get('from', '')}"
            self._body_subject.text = f"Subject: {msg.get('subject', '')}"
            body = msg.get("body", "")
            body = body.replace("\\n", "\n")
            if msg.get("hasdata"):
                body += "\n\n[ ATTACHMENT INCLUDED ]"
            self._body_text.text = body
            if self._body_text.parent:
                self._body_text.text_size = (self._body_text.parent.width - 20, None)

    def _start_compose(self):
        """Switch right panel to compose mode."""
        self._composing = True
        self._body_from.text = "COMPOSE EMAIL"
        self._body_subject.text = ""
        self._body_text.text = ""

        # Remove existing right panel content and replace with compose form
        right = self._body_from.parent
        if not right:
            return

        # Remove body scroll and compose button
        to_remove = [w for w in right.children if w not in (self._body_from,)]
        for w in to_remove:
            right.remove_widget(w)

        # Compose fields
        fields = BoxLayout(orientation='vertical', spacing=8, padding=[0, 5])

        for label_text, hint, key in [
            ("TO:", "recipient@company.net", "to"),
            ("SUBJECT:", "Subject", "subject"),
            ("BODY:", "Message body", "body"),
            ("ATTACH:", "Filename (optional)", "attach"),
        ]:
            lbl = Label(text=label_text, font_name='AeroMatics', font_size='13sp',
                        color=SECONDARY, size_hint_y=None, height=18, halign='left')
            lbl.bind(size=lbl.setter('text_size'))
            inp = HackerTextInput(hint_text=hint, size_hint_y=None, height=36)
            fields.add_widget(lbl)
            fields.add_widget(inp)
            if not hasattr(self, '_compose_inputs'):
                self._compose_inputs = {}
            self._compose_inputs[key] = inp

        # Buttons
        btn_row = BoxLayout(size_hint_y=None, height=38, spacing=10)
        send_btn = HackerButton(text='SEND', button_color=SUCCESS, font_size='14sp')
        send_btn.bind(on_release=lambda *_: self._do_send())
        cancel_btn = HackerButton(text='CANCEL', button_color=SECONDARY, font_size='14sp')
        cancel_btn.bind(on_release=lambda *_: self._cancel_compose())
        btn_row.add_widget(send_btn)
        btn_row.add_widget(cancel_btn)
        fields.add_widget(btn_row)

        right.add_widget(fields)
        self._compose_fields_widget = fields

        # Focus first field
        from kivy.clock import Clock
        Clock.schedule_once(lambda dt: setattr(self._compose_inputs["to"], 'focus', True), 0.2)

    def _do_send(self):
        if not self.net or not hasattr(self, '_compose_inputs'):
            return
        to = self._compose_inputs["to"].text.strip()
        subject = self._compose_inputs["subject"].text.strip() or "No subject"
        body = self._compose_inputs["body"].text.strip() or " "
        attach = self._compose_inputs["attach"].text.strip() or None
        if not to:
            return
        self.net.send_mail(to, subject, body, attach)
        self.net.get_inbox()
        self._cancel_compose()

    def _cancel_compose(self):
        self._composing = False
        self._compose_inputs = {}
        # Rebuild right panel
        right = self._body_from.parent
        if right and hasattr(self, '_compose_fields_widget'):
            right.remove_widget(self._compose_fields_widget)
        # Re-add body scroll and compose button
        right = self._body_from.parent
        if right:
            body_scroll = ScrollView()
            self._body_text.text = 'Select a message to read'
            body_scroll.add_widget(self._body_text)
            right.add_widget(body_scroll)
            right.add_widget(self._compose_btn)
