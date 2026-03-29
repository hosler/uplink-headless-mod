#!/usr/bin/env python3
"""Take screenshots of institutional database servers (Criminal, Academic, Social Security)
by searching InterNIC and navigating to them."""
import subprocess, os, sys, time, json, socket

DISPLAY = ":98"
SCREEN_W, SCREEN_H = 1280, 720
SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "screenshots")
DEBUG_LOG = "/tmp/uplink_db_screens_debug.json"
CLIENT_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_PATH = os.path.join(CLIENT_DIR, "uplink_client.py")
VENV_PYTHON = os.path.join(CLIENT_DIR, ".venv/bin/python3")

xvfb_proc = None
client_proc = None
env = None
bot = None  # API bot for searching InterNIC


class Bot:
    """API client for sending commands to find server IPs."""
    def __init__(self, name, host="127.0.0.1", port=9090):
        self.name = name
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.sock.settimeout(3)
        self.buf = ""

    def send(self, cmd):
        self.sock.sendall((json.dumps(cmd) + "\n").encode())

    def read_msgs(self):
        msgs = []
        try:
            data = self.sock.recv(65536).decode("utf-8", errors="replace")
            self.buf += data
        except socket.timeout:
            pass
        lines = self.buf.split("\n")
        self.buf = lines[-1]
        for l in lines[:-1]:
            l = l.strip()
            if l:
                try:
                    msgs.append(json.loads(l))
                except:
                    pass
        return msgs

    def cmd(self, c, wait_type="response"):
        self.send(c)
        time.sleep(0.5)
        for m in self.read_msgs():
            if m.get("type") == wait_type:
                return m
        return None

    def close(self):
        self.sock.close()


def start_xvfb():
    global xvfb_proc, env
    xvfb_proc = subprocess.Popen(
        ["Xvfb", DISPLAY, "-screen", "0", f"{SCREEN_W}x{SCREEN_H}x24", "-ac"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    assert xvfb_proc.poll() is None, "Xvfb failed"
    env_base = os.environ.copy()
    env_base["DISPLAY"] = DISPLAY
    env = env_base
    print(f"Xvfb on {DISPLAY}")


def start_client(*extra_args):
    global client_proc
    e = env.copy()
    e["SDL_VIDEODRIVER"] = "x11"
    client_proc = subprocess.Popen(
        [VENV_PYTHON, CLIENT_PATH, "--no-music", "--debug-log", DEBUG_LOG] + list(extra_args),
        env=e, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    time.sleep(4)
    assert client_proc.poll() is None, "Client crashed"
    print("Client running")


def cleanup():
    if bot:
        try: bot.close()
        except: pass
    for p in [client_proc, xvfb_proc]:
        if p and p.poll() is None:
            p.terminate()
            try: p.wait(timeout=3)
            except: p.kill()


def key(k):
    subprocess.run(["xdotool", "key", k], env=env, capture_output=True)
    time.sleep(0.3)


def type_t(t):
    subprocess.run(["xdotool", "type", "--delay", "50", t], env=env, capture_output=True)
    time.sleep(0.3)


def wait(s=1):
    time.sleep(s)


def state():
    try:
        with open(DEBUG_LOG) as f:
            return json.load(f)
    except:
        return {}


def screen_type():
    return state().get("screen_type", "")


def screenshot(name):
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    subprocess.run(["scrot", "-o", path], env=env, capture_output=True)
    st = screen_type()
    print(f"  [{name}] {st}")
    return path


try:
    start_xvfb()

    # Use a separate API bot to find server IPs via InterNIC search
    AGENT = "DBScreenBot"
    bot = Bot(AGENT)
    bot.cmd({"cmd": "join", "handle": AGENT, "password": "auto"})

    # Search for institutional databases
    targets = {}
    for query in ["Criminal", "Academic", "Social Security"]:
        m = bot.cmd({"cmd": "search", "query": query}, "search")
        if m:
            results = m.get("results", [])
            for r in results:
                name = r["name"]
                ip = r["ip"]
                print(f"  Found: {name} ({ip})")
                if "criminal" in name.lower():
                    targets["criminal"] = ip
                elif "academic" in name.lower():
                    targets["academic"] = ip
                elif "social" in name.lower():
                    targets["social"] = ip

    print(f"\nTargets: {targets}")

    # Start the pygame client
    start_client("--auto-join", AGENT)

    # For each database server, connect via API (to add to bookmarks),
    # then use keyboard to navigate
    for db_name, ip in targets.items():
        print(f"\n--- {db_name.upper()} DATABASE ({ip}) ---")

        # Connect via auto-connect by restarting client
        # Actually, let's use the API bot to add the link first
        bot.cmd({"cmd": "connect", "ip": ip})
        bot.cmd({"cmd": "disconnect"})
        wait(1)

        # Now connect the client via bookmark or direct
        # Easier: restart client with --auto-connect
        client_proc.terminate()
        try: client_proc.wait(timeout=3)
        except: client_proc.kill()
        wait(1)

        e = env.copy()
        e["SDL_VIDEODRIVER"] = "x11"
        client_proc = subprocess.Popen(
            [VENV_PYTHON, CLIENT_PATH, "--no-music", "--debug-log", DEBUG_LOG,
             "--auto-join", AGENT, "--auto-connect", ip, "--auto-crack"],
            env=e, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        time.sleep(8)

        if client_proc.poll() is not None:
            print(f"  Client crashed for {db_name}")
            continue

        st = screen_type()
        print(f"  Initial: {st}")
        screenshot(f"db_{db_name}_01_initial")

        # Navigate through screens — try Enter for Continue, then menu options
        for attempt in range(5):
            st = screen_type()
            if st == "MessageScreen":
                key("Return")
                wait(1)
            elif st == "MenuScreen":
                screenshot(f"db_{db_name}_02_menu")
                # Try each menu option
                opts = state().get("screen_options", [])
                print(f"  Menu options: {opts}")
                for i, opt in enumerate(opts):
                    key(str(i + 1))
                    wait(1.5)
                    st2 = screen_type()
                    sub = state().get("screen_subtitle", "")
                    print(f"  Option {i+1} ({opt}): {st2} - {sub}")
                    screenshot(f"db_{db_name}_opt{i+1}_{st2.lower()}")
                    key("BackSpace")
                    wait(1)
                break
            elif st in ("UserIDScreen", "PasswordScreen"):
                screenshot(f"db_{db_name}_02_auth")
                # Try typing password
                type_t("rosebud")
                key("Return")
                wait(1.5)
            elif st == "GenericScreen":
                screenshot(f"db_{db_name}_02_generic")
                break
            else:
                screenshot(f"db_{db_name}_02_{st.lower()}")
                break

        key("Escape")
        wait(1)

    bot.close()
    bot = None

    print(f"\nAll database screenshots saved to {SCREENSHOT_DIR}/")
    for f in sorted(os.listdir(SCREENSHOT_DIR)):
        if f.startswith('db_') and f.endswith('.png'):
            print(f"  {f}")

finally:
    cleanup()
