#!/usr/bin/env python3
"""
Uplink Headless API Test Client

Connects to the headless game server and interacts using semantic commands.
"""

import socket
import json
import time
import sys

HOST = "127.0.0.1"
PORT = 9090


class UplinkClient:
    def __init__(self, host=HOST, port=PORT):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.sock.settimeout(2.0)
        self.buf = ""
        print(f"Connected to {host}:{port}")

    def close(self):
        self.sock.close()

    def send_cmd(self, cmd: dict):
        line = json.dumps(cmd) + "\n"
        self.sock.sendall(line.encode())

    # ---- Semantic commands ----

    def connect_to(self, ip: str):
        """Connect to a remote server."""
        self.send_cmd({"cmd": "connect", "ip": ip})

    def disconnect(self):
        """Disconnect from current server."""
        self.send_cmd({"cmd": "disconnect"})

    def navigate(self, screen_index: int):
        """Navigate to a screen index on current computer."""
        self.send_cmd({"cmd": "navigate", "screen": screen_index})

    def menu_select(self, option: int):
        """Select a menu option by index."""
        self.send_cmd({"cmd": "menu", "option": option})

    def dialog_ok(self):
        """Click OK on a dialog screen."""
        self.send_cmd({"cmd": "dialog_ok"})

    def submit_password(self, password: str):
        """Submit a password on a password screen."""
        self.send_cmd({"cmd": "password", "value": password})

    def set_speed(self, speed: int):
        """Set game speed (0=paused, 1=normal, 2=fast, 3=megafast)."""
        self.send_cmd({"cmd": "speed", "value": speed})

    def get_links(self):
        """Request list of known server IPs."""
        self.send_cmd({"cmd": "links"})

    def get_missions(self):
        """Request list of active missions."""
        self.send_cmd({"cmd": "missions"})

    def get_state(self):
        """Request full state dump."""
        self.send_cmd({"cmd": "state"})

    # ---- Low-level commands ----

    def click(self, button_name: str):
        self.send_cmd({"cmd": "click", "button": button_name})

    def type_text(self, text: str):
        self.send_cmd({"cmd": "type", "text": text})

    def press_key(self, keycode: int):
        self.send_cmd({"cmd": "key", "code": keycode})

    # ---- State reading ----

    def read_messages(self, timeout=2.0) -> list[dict]:
        """Read all pending messages from server."""
        msgs = []
        self.sock.settimeout(timeout)
        try:
            data = self.sock.recv(65536).decode("utf-8", errors="replace")
            if data:
                self.buf += data
        except socket.timeout:
            pass

        lines = self.buf.split("\n")
        self.buf = lines[-1]
        for line in lines[:-1]:
            line = line.strip()
            if line:
                try:
                    msgs.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return msgs

    def read_state(self) -> dict | None:
        """Read messages and return the latest state update."""
        msgs = self.read_messages()
        for msg in reversed(msgs):
            if msg.get("type") == "state":
                return msg
        return None

    def drain_and_read(self, delay=1.0) -> dict | None:
        """Drain buffered data, wait, then read fresh state."""
        # Drain old data (read a few times to empty buffer)
        old_timeout = self.sock.gettimeout()
        self.sock.settimeout(0.1)
        for _ in range(50):
            try:
                self.sock.recv(65536)
            except (socket.timeout, BlockingIOError, OSError):
                break
        self.buf = ""
        self.sock.settimeout(old_timeout)
        # Wait for fresh state
        time.sleep(delay)
        return self.read_state()

    def read_response(self) -> dict | None:
        """Read messages and return the latest response."""
        msgs = self.read_messages()
        for msg in reversed(msgs):
            if msg.get("type") == "response":
                return msg
        return None

    def get_buttons(self, state: dict) -> dict[str, dict]:
        buttons = {}
        for b in state.get("buttons", []):
            buttons[b["name"]] = b
        return buttons

    def dump_state(self, state: dict):
        if not state:
            print("  (no state)")
            return
        screen = state.get("screen", {})
        print(f"  Screen: {screen.get('type', '?')}: {screen.get('maintitle', '')}")
        if screen.get("subtitle"):
            print(f"          {screen['subtitle']}")
        if screen.get("options"):
            for i, opt in enumerate(screen["options"]):
                print(f"    [{i}] {opt['caption']} (→screen {opt['nextpage']})")
        if screen.get("widgets"):
            for w in screen["widgets"]:
                cap = w.get("caption", "")
                if cap:
                    print(f"    widget: {w['name']} = '{cap}'")
        player = state.get("player", {})
        if player:
            print(f"  Player: {player.get('handle', '?')} @ {player.get('remotehost', '?')}")
            r = player.get("rating", {})
            print(f"  Rating: uplink={r.get('uplink', 0)}")
        conn = state.get("connection", {})
        if conn and conn.get("nodes"):
            print(f"  Connection: {' → '.join(conn['nodes'])}")
        if "date" in state:
            print(f"  Date: {state['date']}  Speed: {state.get('speed', '?')}")


def run_test():
    """Automated test: click through gateway dialog, explore menus."""
    print("=== Uplink Headless API Test ===\n")
    c = UplinkClient()
    time.sleep(1)

    # Read initial state
    print("--- 1. Initial State ---")
    state = c.read_state()
    c.dump_state(state)

    if not state:
        print("No state received!")
        c.close()
        return

    # Click through dialogs until we reach a menu or other screen
    for step in range(5):
        screen = state.get("screen", {}) if state else {}
        stype = screen.get("type", "")

        if stype == "DialogScreen":
            print(f"\n--- {step+2}. Dialog: clicking OK ---")
            c.dialog_ok()
            state = c.drain_and_read(1.5)
            c.dump_state(state)
            # Also show any responses
            msgs = c.read_messages()
            for m in msgs:
                if m.get("type") == "response":
                    print(f"  Response: {m.get('status')}: {m.get('detail')}")
        elif stype == "MenuScreen":
            print(f"\n--- {step+2}. Menu Screen ---")
            c.dump_state(state)
            break
        elif stype == "PasswordScreen":
            print(f"\n--- {step+2}. Password Screen ---")
            c.dump_state(state)
            break
        else:
            print(f"\n--- {step+2}. Screen: {stype} ---")
            c.dump_state(state)
            break

    # Get known links
    print("\n--- Known Links ---")
    c.get_links()
    time.sleep(0.5)
    msgs = c.read_messages()
    for m in msgs:
        if m.get("type") == "links":
            for link in m.get("links", []):
                print(f"  {link['ip']} - {link['name']}")

    # Get missions
    print("\n--- Active Missions ---")
    c.get_missions()
    time.sleep(0.5)
    msgs = c.read_messages()
    for m in msgs:
        if m.get("type") == "missions":
            if not m.get("missions"):
                print("  (none)")
            for mission in m.get("missions", []):
                print(f"  [{mission['type']}] {mission['description']} (${mission['payment']})")

    # If on menu, try selecting an option
    screen = state.get("screen", {}) if state else {}
    if screen.get("type") == "MenuScreen" and screen.get("options"):
        print("\n--- Selecting first menu option ---")
        c.menu_select(0)
        state = c.drain_and_read(1.5)
        c.dump_state(state)

    print("\n--- Final State ---")
    state = c.drain_and_read(1.0)
    c.dump_state(state)

    c.close()
    print("\nDone.")


def interactive():
    """Interactive mode for manual testing."""
    print("=== Uplink Interactive Client ===")
    c = UplinkClient()
    time.sleep(1)

    print("\nCommands:")
    print("  state / s          — show current state")
    print("  buttons / b        — list all buttons")
    print("  connect <ip>       — connect to server")
    print("  disconnect         — disconnect")
    print("  menu <n>           — select menu option")
    print("  dialog_ok          — click dialog OK")
    print("  password <pw>      — submit password")
    print("  navigate <n>       — navigate to screen index")
    print("  links              — show known servers")
    print("  missions           — show active missions")
    print("  speed <0-4>        — set game speed")
    print("  click <name>       — click Eclipse button")
    print("  type <text>        — type text")
    print("  raw                — show raw JSON state")
    print("  quit / q           — exit")

    c.sock.settimeout(0.5)
    while True:
        try:
            cmd = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not cmd:
            continue

        parts = cmd.split(None, 1)
        verb = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if verb in ("quit", "q"):
            break
        elif verb in ("state", "s"):
            state = c.read_state()
            c.dump_state(state)
        elif verb in ("buttons", "b"):
            state = c.read_state()
            if state:
                for name, b in sorted(c.get_buttons(state).items()):
                    cap = b.get("caption", "")
                    print(f"  [{name}] '{cap}'")
        elif verb == "connect" and arg:
            c.connect_to(arg)
        elif verb == "disconnect":
            c.disconnect()
        elif verb == "menu" and arg:
            c.menu_select(int(arg))
        elif verb == "dialog_ok":
            c.dialog_ok()
        elif verb == "password" and arg:
            c.submit_password(arg)
        elif verb == "navigate" and arg:
            c.navigate(int(arg))
        elif verb == "links":
            c.get_links()
            time.sleep(0.3)
            msgs = c.read_messages()
            for m in msgs:
                if m.get("type") == "links":
                    for link in m["links"]:
                        print(f"  {link['ip']} - {link['name']}")
        elif verb == "missions":
            c.get_missions()
            time.sleep(0.3)
            msgs = c.read_messages()
            for m in msgs:
                if m.get("type") == "missions":
                    if not m["missions"]:
                        print("  (no active missions)")
                    for mission in m["missions"]:
                        print(f"  {mission['description']} (${mission['payment']})")
        elif verb == "speed" and arg:
            c.set_speed(int(arg))
        elif verb == "click" and arg:
            c.click(arg)
        elif verb == "type" and arg:
            c.type_text(arg)
        elif verb == "raw":
            state = c.read_state()
            if state:
                print(json.dumps(state, indent=2)[:3000])
        else:
            print(f"Unknown: {verb}")

        # Read responses
        time.sleep(0.3)
        msgs = c.read_messages()
        for m in msgs:
            if m.get("type") == "response":
                print(f"  → {m['status']}: {m.get('detail', '')}")

    c.close()
    print("Disconnected.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "-i":
        interactive()
    else:
        run_test()
