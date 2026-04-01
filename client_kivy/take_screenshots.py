#!/usr/bin/env python3
"""Take screenshots of key UI screens for the Kivy client."""
import subprocess, os, sys, time, json

DISPLAY = ":98"
SCREEN_W, SCREEN_H = 1280, 720
SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "screenshots_kivy")
DEBUG_LOG = "/tmp/uplink_kivy_debug.json"
CLIENT_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_PATH = os.path.join(CLIENT_DIR, "main.py")
# Use the currently active python (should be from the venv)
VENV_PYTHON = sys.executable

xvfb_proc = None
client_proc = None


def start_xvfb():
    global xvfb_proc
    xvfb_proc = subprocess.Popen(
        ["Xvfb", DISPLAY, "-screen", "0", f"{SCREEN_W}x{SCREEN_H}x24", "-ac"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    assert xvfb_proc.poll() is None, "Xvfb failed to start"
    print(f"Xvfb on {DISPLAY}")


def start_client(*extra_args):
    global client_proc
    env = os.environ.copy()
    env["DISPLAY"] = DISPLAY
    env["SDL_VIDEODRIVER"] = "x11"
    env["KIVY_NO_ARGS"] = "1"
    env["KIVY_NO_CONSOLELOG"] = "1"
    client_proc = subprocess.Popen(
        [VENV_PYTHON, CLIENT_PATH, "--no-music", "--debug-log", DEBUG_LOG] + list(extra_args),
        env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    time.sleep(4)
    if client_proc.poll() is not None:
        out = client_proc.stdout.read().decode()[:1000] if client_proc.stdout else "no output"
        raise RuntimeError(f"Client crashed (exit {client_proc.returncode}): {out}")
    print("Client running")


def stop_client():
    global client_proc
    if client_proc and client_proc.poll() is None:
        client_proc.terminate()
        try:
            client_proc.wait(timeout=3)
        except:
            client_proc.kill()
    client_proc = None


def cleanup():
    stop_client()
    if xvfb_proc and xvfb_proc.poll() is None:
        xvfb_proc.terminate()
        try:
            xvfb_proc.wait(timeout=3)
        except:
            xvfb_proc.kill()


def xenv():
    env = os.environ.copy()
    env["DISPLAY"] = DISPLAY
    return env


def click(x, y, btn=1):
    subprocess.run(["xdotool", "mousemove", str(x), str(y), "click", str(btn)],
                   env=xenv(), capture_output=True)
    time.sleep(0.4)


def type_text(text):
    subprocess.run(["xdotool", "type", "--delay", "50", text], env=xenv(), capture_output=True)
    time.sleep(0.3)


def press_key(key):
    subprocess.run(["xdotool", "key", key], env=xenv(), capture_output=True)
    time.sleep(0.3)


def screenshot(name):
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    subprocess.run(["scrot", "-o", path], env=xenv(), capture_output=True)
    print(f"  [{name}] saved")
    return path


def read_state():
    try:
        with open(DEBUG_LOG) as f:
            return json.load(f)
    except:
        return {}


def wait_for_state(key, value, timeout=10):
    for _ in range(timeout * 5):
        s = read_state()
        if value.lower() in str(s.get(key, "")).lower():
            return True
        time.sleep(0.2)
    return False


try:
    start_xvfb()
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    # ---- Session 1: Login screen ----
    print("\n--- Login screen ---")
    start_client()
    time.sleep(2)
    screenshot("01_login")

    # Type agent name — click handle field and type
    click(640, 380)
    time.sleep(0.3)
    type_text("Neuromancer")
    time.sleep(0.3)
    screenshot("02_login_typed")
    stop_client()

    # ---- Session 2: Auto-join and capture all tabs ----
    print("\n--- Main UI (auto-join) ---")
    start_client("--auto-join", "Neuromancer")
    time.sleep(4)

    # Should be at browser/bookmarks
    screenshot("03_browser_bookmarks")

    state = read_state()
    print(f"  State: screen={state.get('screen_type')}, handle={state.get('player_handle')}")

    # Use F-keys for tab switching (works with xdotool + Kivy)
    press_key("F2")
    time.sleep(1)
    screenshot("04_map")

    press_key("F3")
    time.sleep(1)
    screenshot("05_email")

    press_key("F4")
    time.sleep(1)
    screenshot("06_gateway")

    press_key("F5")
    time.sleep(1)
    screenshot("07_missions")

    press_key("F6")
    time.sleep(1)
    screenshot("08_bbs")

    press_key("F7")
    time.sleep(1)
    screenshot("09_software")

    press_key("F8")
    time.sleep(1)
    screenshot("10_hardware")

    # Back to browser, connect to a server via keyboard shortcut
    press_key("F1")
    time.sleep(1)
    # Press '1' to connect to first bookmark
    press_key("1")
    time.sleep(3)
    screenshot("11_server_connected")

    # Press Enter to continue past welcome message
    press_key("Return")
    time.sleep(1)
    screenshot("12_server_menu")

    stop_client()

    # ---- Session 3: Auto-connect + auto-crack for server screens ----
    print("\n--- Server screens (auto-connect) ---")
    start_client("--auto-join", "Neuromancer", "--auto-connect", "128.185.0.4", "--auto-crack")
    time.sleep(6)
    screenshot("13_authenticated")

    # Navigate around the server
    press_key("1")
    time.sleep(1)
    screenshot("14_server_screen")

    press_key("Escape")
    time.sleep(1)
    screenshot("15_disconnected")

    stop_client()

    print(f"\nAll screenshots saved to {SCREENSHOT_DIR}/")
    print("Files:")
    for f in sorted(os.listdir(SCREENSHOT_DIR)):
        if f.endswith('.png'):
            print(f"  {f}")

finally:
    cleanup()
