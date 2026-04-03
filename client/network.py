"""Network layer: TCP connection, recv thread, GameState cache."""
import socket
import json
import threading
import queue
from dataclasses import dataclass, field


@dataclass
class GameState:
    screen_type: str = "none"
    screen_data: dict = field(default_factory=dict)
    player: dict = field(default_factory=dict)
    connection: dict = field(default_factory=dict)
    date: str = ""
    speed: int = 0
    buttons: list = field(default_factory=list)
    # Cached query responses
    links: list = field(default_factory=list)
    missions: list = field(default_factory=list)
    bbs_missions: list = field(default_factory=list)
    inbox: list = field(default_factory=list)
    gateway_info: dict = field(default_factory=dict)
    gateway_files: list = field(default_factory=list)
    software_list: list = field(default_factory=list)
    hardware_list: list = field(default_factory=list)
    remote_files: list = field(default_factory=list)
    remote_logs: list = field(default_factory=list)
    balance: int = 0
    trace: dict = field(default_factory=dict)
    search_results: list = field(default_factory=list)
    screen_links: list = field(default_factory=list)
    credentials: list = field(default_factory=list)
    lan_data: dict = field(default_factory=dict)
    news: list = field(default_factory=list)


class Network:
    def __init__(self, host="127.0.0.1", port=9090):
        self.host = host
        self.port = port
        self.sock: socket.socket | None = None
        self.connected = False
        self.joined = False
        self.state = GameState()
        self._queue: queue.Queue = queue.Queue()
        self._responses: list[dict] = []
        self._thread: threading.Thread | None = None
        self._running = False
        self._buf = ""
        self._debug_log = None

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.sock.settimeout(0.1)
            self.connected = True
            self._running = True
            self._thread = threading.Thread(target=self._recv_loop, daemon=True)
            self._thread.start()
            return True
        except Exception as e:
            print(f"Network: connect failed: {e}")
            return False

    def close(self):
        self._running = False
        self.connected = False
        self.joined = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None

    def send(self, cmd: dict, refresh_state=False):
        if not self.connected or not self.sock:
            return
        try:
            self.sock.sendall((json.dumps(cmd) + "\n").encode())
            if refresh_state:
                # Immediately request fresh state after state-changing commands
                self.sock.sendall(b'{"cmd":"state"}\n')
        except Exception:
            self.connected = False

    def _recv_loop(self):
        buf = ""
        while self._running:
            try:
                data = self.sock.recv(65536)
                if not data:
                    self.connected = False
                    break
                buf += data.decode("utf-8", errors="replace")
                lines = buf.split("\n")
                buf = lines[-1]
                for line in lines[:-1]:
                    line = line.strip()
                    if line:
                        try:
                            msg = json.loads(line)
                            self._queue.put(msg)
                        except json.JSONDecodeError:
                            pass
            except socket.timeout:
                continue
            except Exception:
                self.connected = False
                break

    def poll(self) -> list[dict]:
        """Drain queue, update state, return new responses."""
        self._responses.clear()
        while not self._queue.empty():
            try:
                msg = self._queue.get_nowait()
                self._process(msg)
            except queue.Empty:
                break
        responses = list(self._responses)
        self._responses.clear()

        # Write state to debug log for UI testing
        if self._debug_log:
            self._write_debug_log()

        return responses

    def enable_debug_log(self, path: str):
        """Enable writing state to a JSON file each poll."""
        self._debug_log = path

    def _write_debug_log(self):
        import json as _json
        try:
            s = self.state
            data = {
                "screen_type": s.screen_type,
                "screen_title": s.screen_data.get("maintitle", ""),
                "screen_subtitle": s.screen_data.get("subtitle", ""),
                "screen_options": [o.get("caption", "") for o in s.screen_data.get("options", [])],
                "player_handle": s.player.get("handle", ""),
                "player_connected": s.player.get("connected", False),
                "player_remotehost": s.player.get("remotehost", ""),
                "balance": s.balance,
                "date": s.date,
                "speed": s.speed,
                "links_count": len(s.links),
                "missions_count": len(s.missions),
                "bbs_count": len(s.bbs_missions),
                "inbox_count": len(s.inbox),
                "files_count": len(s.remote_files),
                "logs_count": len(s.remote_logs),
                "active_tab": "browser",  # client sets this
            }
            with open(self._debug_log, "w") as f:
                _json.dump(data, f, indent=2)
        except Exception:
            pass

    def _process(self, msg: dict):
        t = msg.get("type", "")
        if t == "state":
            s = self.state
            s.screen_type = msg.get("screen", {}).get("type", "none")
            s.screen_data = msg.get("screen", {})
            s.player = msg.get("player", {})
            s.connection = msg.get("connection", {})
            s.date = msg.get("date", "")
            s.speed = msg.get("speed", 0)
            s.buttons = msg.get("buttons", [])
        elif t == "response":
            self._responses.append(msg)
        elif t == "links":
            self.state.links = msg.get("links", [])
        elif t == "missions":
            self.state.missions = msg.get("missions", [])
        elif t == "bbs":
            self.state.bbs_missions = msg.get("missions", [])
        elif t == "inbox":
            self.state.inbox = msg.get("messages", [])
        elif t == "news":
            self.state.news = msg.get("stories", [])
        elif t == "balance":
            self.state.balance = msg.get("balance", 0)
        elif t == "gateway_info":
            self.state.gateway_info = msg
        elif t == "gateway_files":
            self.state.gateway_files = msg.get("files", [])
        elif t == "software_list":
            self.state.software_list = msg.get("software", [])
        elif t == "hardware_list":
            self.state.hardware_list = msg.get("hardware", [])
        elif t == "files":
            self.state.remote_files = msg.get("files", [])
        elif t == "logs":
            self.state.remote_logs = msg.get("logs", [])
        elif t == "trace":
            self.state.trace = msg
        elif t == "credentials":
            self.state.credentials = msg.get("accounts", [])
        elif t == "search":
            self.state.search_results = msg.get("results", [])
        elif t == "screen_links":
            self.state.screen_links = msg.get("links", [])
        elif t == "lan_scan":
            self.state.lan_data = msg

    # ---- Convenience commands ----

    def join(self, handle, password=""):
        self.send({"cmd": "join", "handle": handle, "password": password})

    def request_state(self):
        self.send({"cmd": "state"})

    def server_connect(self, ip):
        self.send({"cmd": "connect", "ip": ip}, refresh_state=True)

    def server_disconnect(self):
        self.send({"cmd": "disconnect"}, refresh_state=True)

    def navigate(self, screen):
        self.send({"cmd": "navigate", "screen": screen}, refresh_state=True)

    def back(self):
        self.send({"cmd": "back"}, refresh_state=True)

    def menu_select(self, option):
        self.send({"cmd": "menu", "option": option}, refresh_state=True)

    def dialog_ok(self):
        self.send({"cmd": "dialog_ok"}, refresh_state=True)

    def submit_password(self, password, user=None):
        cmd = {"cmd": "password", "value": password}
        if user:
            cmd["user"] = user
        self.send(cmd, refresh_state=True)

    def crack_password(self):
        self.send({"cmd": "crack_password"})

    def set_speed(self, speed):
        self.send({"cmd": "speed", "value": speed})

    def get_links(self):
        self.send({"cmd": "links"})

    def add_link(self, ip):
        self.send({"cmd": "add_link", "ip": ip}, refresh_state=True)

    def get_missions(self):
        self.send({"cmd": "missions"})

    def get_bbs(self):
        self.send({"cmd": "bbs"})

    def get_inbox(self):
        self.send({"cmd": "inbox"})

    def get_news(self):
        self.send({"cmd": "news"})

    def get_balance(self):
        self.send({"cmd": "balance"})

    def get_files(self):
        self.send({"cmd": "files"})

    def get_logs(self):
        self.send({"cmd": "logs"})

    def copy_file(self, title):
        self.send({"cmd": "copy_file", "title": title}, refresh_state=True)

    def delete_file(self, title):
        self.send({"cmd": "delete_file", "title": title}, refresh_state=True)

    def delete_logs(self):
        self.send({"cmd": "delete_logs"}, refresh_state=True)

    def delete_log(self, index):
        self.send({"cmd": "delete_log", "index": index}, refresh_state=True)

    def send_mail(self, to, subject, body, attach=None):
        cmd = {"cmd": "send_mail", "to": to, "subject": subject, "body": body}
        if attach:
            cmd["attach"] = attach
        self.send(cmd)

    def check_mission(self):
        self.send({"cmd": "check_mission"})

    def type_text(self, text):
        self.send({"cmd": "type", "text": text})

    def send_key(self, code):
        self.send({"cmd": "key", "code": code})

    def set_field(self, button, value):
        self.send({"cmd": "set_field", "button": button, "value": value}, refresh_state=True)

    def delete_gateway_file(self, title):
        self.send({"cmd": "delete_gateway_file", "title": title})

    def accept_mission(self, index):
        self.send({"cmd": "accept_mission", "index": index}, refresh_state=True)

    def get_gateway_info(self):
        self.send({"cmd": "gateway_info"})

    def get_gateway_files(self):
        self.send({"cmd": "gateway_files"})

    def get_software_list(self):
        self.send({"cmd": "software_list"})

    def get_hardware_list(self):
        self.send({"cmd": "hardware_list"})

    def buy_software(self, title, version=None):
        msg = {"cmd": "buy_software", "title": title}
        if version is not None:
            msg["version"] = version
        self.send(msg, refresh_state=True)

    def buy_hardware(self, title):
        self.send({"cmd": "buy_hardware", "title": title}, refresh_state=True)

    def search(self, query=""):
        self.send({"cmd": "search", "query": query})

    def get_trace(self):
        self.send({"cmd": "trace"})

    def lan_scan(self):
        self.send({"cmd": "lan_scan"})

    def get_screen_links(self):
        self.send({"cmd": "screen_links"})

    def connect_bounce(self, target, bounces):
        self.send({"cmd": "connect_bounce", "target": target, "bounces": bounces})
