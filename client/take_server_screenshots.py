#!/usr/bin/env python3
"""Take screenshots of all server screen types by navigating via xdotool."""
import subprocess, os, sys, time, json

DISPLAY = ":98"
SCREEN_W, SCREEN_H = 1280, 720
SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "screenshots")
DEBUG_LOG = "/tmp/uplink_server_screens_debug.json"
CLIENT_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_PATH = os.path.join(CLIENT_DIR, "uplink_client.py")
VENV_PYTHON = os.path.join(CLIENT_DIR, ".venv/bin/python3")

xvfb_proc = None
client_proc = None
env = None


def start_xvfb():
    global xvfb_proc, env
    xvfb_proc = subprocess.Popen(
        ["Xvfb", DISPLAY, "-screen", "0", f"{SCREEN_W}x{SCREEN_H}x24", "-ac"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    assert xvfb_proc.poll() is None, "Xvfb failed to start"
    env_base = os.environ.copy()
    env_base["DISPLAY"] = DISPLAY
    env = env_base
    print(f"Xvfb on {DISPLAY}")


def start_client():
    global client_proc
    e = env.copy()
    e["SDL_VIDEODRIVER"] = "x11"
    client_proc = subprocess.Popen(
        [VENV_PYTHON, CLIENT_PATH, "--no-music", "--debug-log", DEBUG_LOG],
        env=e, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    time.sleep(3)
    assert client_proc.poll() is None, "Client crashed on start"
    print("Client running")


def cleanup():
    for p in [client_proc, xvfb_proc]:
        if p and p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=3)
            except:
                p.kill()


def click(x, y):
    # Focus the window first, then move and click
    subprocess.run(["xdotool", "mousemove", str(x), str(y)],
                   env=env, capture_output=True)
    time.sleep(0.1)
    subprocess.run(["xdotool", "click", "1"],
                   env=env, capture_output=True)
    time.sleep(0.4)


def type_t(t):
    subprocess.run(["xdotool", "type", "--delay", "50", t], env=env, capture_output=True)
    time.sleep(0.3)


def key(k):
    subprocess.run(["xdotool", "key", k], env=env, capture_output=True)
    time.sleep(0.2)


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


def connect_bookmark(idx):
    """Connect to bookmark by index (1-9 keyboard shortcut)."""
    key(str(idx + 1))
    wait(2.5)


def disconnect():
    """Disconnect using Escape."""
    key("Escape")
    wait(1)


def click_back():
    """Go back using Backspace."""
    key("BackSpace")
    wait(1)


def click_continue():
    """Continue using Enter."""
    key("Return")
    wait(1)


def click_menu_option(idx):
    """Select menu option using 1-9 keyboard shortcut."""
    key(str(idx + 1))
    wait(1)


def submit_password(pw="rosebud"):
    """Tab to password field, type, press Enter."""
    key("Tab")
    wait(0.2)
    type_t(pw)
    key("Return")
    wait(1.5)


def login(handle):
    # Click handle field, type name, tab to password, type pw, click connect
    click(506, 306)
    wait(0.2)
    type_t(handle)
    key("Tab")
    type_t("test")
    click(640, 410)
    wait(4)
    print(f"  Logged in as {state().get('player_handle', '?')}")


try:
    start_xvfb()
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)

    start_client()

    # ================================================================
    # First, start without auto flags to capture login screen
    # Then restart with auto-join + auto-connect + auto-crack
    # ================================================================

    # Stop and restart with auto flags to get into Test Machine directly
    client_proc.terminate()
    try:
        client_proc.wait(timeout=3)
    except:
        client_proc.kill()
    time.sleep(1)

    # Start with auto-join, auto-connect to Test Machine, auto-crack
    e = env.copy()
    e["SDL_VIDEODRIVER"] = "x11"
    client_proc = subprocess.Popen(
        [VENV_PYTHON, CLIENT_PATH, "--no-music", "--debug-log", DEBUG_LOG,
         "--auto-join", "ScreenBot", "--auto-connect", "128.185.0.4", "--auto-crack"],
        env=e, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    time.sleep(8)  # Wait for auto-join + connect + crack
    assert client_proc.poll() is None, "Client crashed"
    print("Client running (auto-joined + connected to Test Machine)")

    # ================================================================
    # TEST MACHINE (128.185.0.4)
    # Auto-crack should have gotten us past UserID to MenuScreen
    # Menu: File Server, View records, View links, Admin
    # Admin: View logs, Security, Console, Exit
    # ================================================================
    print("\n--- Test Machine ---")

    # May still be on MessageScreen — need to click Continue
    st = screen_type()
    print(f"  Initial screen: {st}")
    if "Message" in st:
        screenshot("server_01_message")
        click_continue()
        wait(1)

    st = screen_type()
    print(f"  After continue: {st}")
    if "UserID" in st or "Password" in st:
        screenshot("server_02_userid")
        submit_password("rosebud")
        wait(1)

    st = screen_type()
    print(f"  After auth: {st}")
    screenshot("server_03_menu")
    opts = state().get("screen_options", [])
    print(f"  Menu options: {opts}")

    # File Server (option 0)
    click_menu_option(0)
    wait(1)
    screenshot("server_04_fileserver")

    click_back()
    wait(0.5)

    # Records (option 1)
    click_menu_option(1)
    wait(1)
    screenshot("server_05_records")

    click_back()
    wait(0.5)

    # Links (option 2)
    click_menu_option(2)
    wait(1)
    screenshot("server_06_links")

    click_back()
    wait(0.5)

    # Admin menu (option 3)
    click_menu_option(3)
    wait(0.5)
    screenshot("server_07_admin_menu")

    # Logs (admin option 0)
    click_menu_option(0)
    wait(1)
    screenshot("server_08_logs")

    click_back()
    wait(0.5)

    # Security (admin option 1)
    click_menu_option(1)
    wait(1)
    screenshot("server_09_security")

    click_back()
    wait(0.5)

    # Console (admin option 2)
    click_menu_option(2)
    wait(1)
    screenshot("server_10_console")

    click_back()
    wait(0.5)

    disconnect()

    # ================================================================
    # INTERNIC — LinksScreen with many servers
    # ================================================================
    print("\n--- InterNIC ---")
    connect_bookmark(2)  # InterNIC (3rd bookmark)

    st = screen_type()
    if "Message" in st:
        click_continue()

    screenshot("server_11_internic_menu")

    # Browse/Search (option 0) -> LinksScreen
    click_menu_option(0)
    wait(1)
    screenshot("server_12_links_full")

    click_back()
    disconnect()

    # ================================================================
    # BANK — MenuScreen, CompanyInfo, DialogScreen
    # ================================================================
    print("\n--- Bank ---")
    connect_bookmark(3)  # Uplink International Bank (4th bookmark)
    wait(1)

    screenshot("server_13_bank_menu")

    # About Us (option 0) -> CompanyInfo
    click_menu_option(0)
    wait(1)
    screenshot("server_14_companyinfo")

    click_back()
    wait(0.5)

    # Create Account (option 1) -> DialogScreen
    click_menu_option(1)
    wait(1)
    screenshot("server_15_dialog")

    click_back()
    wait(0.5)

    # Manage Account (option 2) -> UserIDScreen (for bank login)
    click_menu_option(2)
    wait(1)
    screenshot("server_16_bank_userid")

    click_back()
    disconnect()

    print(f"\nAll server screenshots saved to {SCREENSHOT_DIR}/")
    print("Server screen files:")
    for f in sorted(os.listdir(SCREENSHOT_DIR)):
        if f.startswith('server_') and f.endswith('.png'):
            print(f"  {f}")

finally:
    cleanup()
