#!/usr/bin/env python3
"""Take screenshots of key UI screens for the README."""
import subprocess, os, sys, time, json

DISPLAY = ":98"
SCREEN_W, SCREEN_H = 1280, 720
SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "screenshots")
DEBUG_LOG = "/tmp/uplink_screenshots_debug.json"
CLIENT_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_PATH = os.path.join(CLIENT_DIR, "uplink_client.py")
VENV_PYTHON = os.path.join(CLIENT_DIR, ".venv/bin/python3")

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
    client_proc = subprocess.Popen(
        [VENV_PYTHON, CLIENT_PATH, "--no-music", "--debug-log", DEBUG_LOG] + list(extra_args),
        env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    time.sleep(3)
    assert client_proc.poll() is None, "Client crashed on start"
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

    # Type agent name and connect
    # The login screen has a text field - click it and type
    click(640, 400)
    time.sleep(0.3)
    type_text("Neuromancer")
    time.sleep(0.3)
    screenshot("02_login_typed")
    stop_client()

    # ---- Session 2: Auto-join and capture tabs ----
    print("\n--- Main UI (auto-join) ---")
    start_client("--auto-join", "Neuromancer")
    time.sleep(3)

    # Should be at gateway/browser
    screenshot("03_gateway_browser")

    # Click Map tab (tab index 1, roughly x=200 area in tab bar)
    # Tab bar is near top. Let's read state to understand layout
    state = read_state()
    print(f"  State: tab={state.get('active_tab')}, screen={state.get('screen_type')}")

    # Design coords: TOPBAR_H=40, TAB_H=36, tab zones 240 wide starting at x=10
    # Scale factor: 1280/1920 = 0.667
    # Tab y center: (40+18)*0.667 = 39
    tab_y = 39
    # Tab zone centers: (10 + i*240 + 120) * 0.667
    tab_positions = {
        "browser": 87,
        "map": 247,
        "email": 407,
        "gateway": 567,
        "missions": 727,
        "bbs": 887,
        "software": 1047,
        "hardware": 1207,
    }

    # Map tab
    click(tab_positions["map"], tab_y)
    time.sleep(1)
    screenshot("04_map")

    # Email tab
    click(tab_positions["email"], tab_y)
    time.sleep(1)
    screenshot("05_email")

    # Gateway tab
    click(tab_positions["gateway"], tab_y)
    time.sleep(1)
    screenshot("06_gateway")

    # Missions tab
    click(tab_positions["missions"], tab_y)
    time.sleep(1)
    screenshot("07_missions")

    # BBS tab
    click(tab_positions["bbs"], tab_y)
    time.sleep(1)
    screenshot("08_bbs")

    # Software tab
    click(tab_positions["software"], tab_y)
    time.sleep(1)
    screenshot("09_software")

    # Hardware tab
    click(tab_positions["hardware"], tab_y)
    time.sleep(1)
    screenshot("10_hardware")

    # Now connect to a server via browser
    click(tab_positions["browser"], tab_y)
    time.sleep(1)

    # Auto-connect to InterNIC - use the bookmarks. Click on InterNIC entry
    # Bookmarks are in the browser panel. Let's click on one.
    # Typical bookmark list starts around y=150, entries ~30px apart
    # InterNIC is usually 3rd bookmark
    click(640, 230)
    time.sleep(3)
    screenshot("11_server_connected")

    # Navigate to a menu - click Continue on welcome message
    click(640, 500)
    time.sleep(1)
    screenshot("12_server_menu")

    stop_client()

    # ---- Session 3: Connect to test machine for file server view ----
    print("\n--- Server screens (auto-connect) ---")
    start_client("--auto-join", "Neuromancer", "--auto-connect", "128.185.0.4", "--auto-crack")
    time.sleep(6)
    screenshot("13_file_server")
    stop_client()

    print(f"\nAll screenshots saved to {SCREENSHOT_DIR}/")
    print("Files:")
    for f in sorted(os.listdir(SCREENSHOT_DIR)):
        if f.endswith('.png'):
            print(f"  {f}")

finally:
    cleanup()
