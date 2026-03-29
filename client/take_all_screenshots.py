#!/usr/bin/env python3
"""Take verified screenshots of every screen type using debug log confirmation."""
import subprocess, os, sys, time, json

DISPLAY = ":98"
SCREEN_W, SCREEN_H = 1280, 720
SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "screenshots")
DEBUG_LOG = "/tmp/uplink_all_screens_debug.json"
CLIENT_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_PATH = os.path.join(CLIENT_DIR, "uplink_client.py")
VENV_PYTHON = os.path.join(CLIENT_DIR, ".venv/bin/python3")

xvfb_proc = None
client_proc = None
env = None


def setup():
    global xvfb_proc, env
    xvfb_proc = subprocess.Popen(
        ["Xvfb", DISPLAY, "-screen", "0", f"{SCREEN_W}x{SCREEN_H}x24", "-ac"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    env = os.environ.copy()
    env["DISPLAY"] = DISPLAY
    print(f"Xvfb on {DISPLAY}")


def start_client(*args):
    global client_proc
    if client_proc and client_proc.poll() is None:
        client_proc.terminate()
        try: client_proc.wait(timeout=3)
        except: client_proc.kill()
        time.sleep(1)
    e = env.copy()
    e["SDL_VIDEODRIVER"] = "x11"
    client_proc = subprocess.Popen(
        [VENV_PYTHON, CLIENT_PATH, "--no-music", "--debug-log", DEBUG_LOG] + list(args),
        env=e, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    time.sleep(4)
    assert client_proc.poll() is None, "Client crashed"


def cleanup():
    for p in [client_proc, xvfb_proc]:
        if p and p.poll() is None:
            p.terminate()
            try: p.wait(timeout=3)
            except: p.kill()


def key(k):
    subprocess.run(["xdotool", "key", k], env=env, capture_output=True)
    time.sleep(0.3)


def type_t(t):
    subprocess.run(["xdotool", "type", "--delay", "40", t], env=env, capture_output=True)
    time.sleep(0.2)


def state():
    try:
        with open(DEBUG_LOG) as f: return json.load(f)
    except: return {}


def screen_type():
    return state().get("screen_type", "")


def wait_for_screen(expected, timeout=8):
    """Wait until screen_type matches expected."""
    for _ in range(timeout * 5):
        if expected.lower() in screen_type().lower():
            return True
        time.sleep(0.2)
    print(f"    WARN: expected {expected}, got {screen_type()}")
    return False


def shot(name):
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    # Small delay to ensure render is complete
    time.sleep(0.3)
    subprocess.run(["scrot", "-o", path], env=env, capture_output=True)
    st = screen_type()
    print(f"  [{name}] {st}")
    return st


try:
    setup()
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    AGENT = "ScreenshotAgent"

    # ================================================================
    # SECTION 1: Content tabs (auto-join, no server connection)
    # ================================================================
    print("\n=== Content Tabs ===")
    start_client("--auto-join", AGENT)

    key("F1"); time.sleep(1)
    shot("01_login")  # Actually bookmarks after auto-join

    key("F2"); time.sleep(1)
    shot("04_map")

    key("F3"); time.sleep(1)
    shot("05_email")

    key("F4"); time.sleep(1)
    shot("06_gateway")

    key("F5"); time.sleep(1)
    shot("07_missions")

    key("F6"); time.sleep(1.5)
    shot("08_bbs")

    key("F7"); time.sleep(1)
    shot("09_software")

    key("F8"); time.sleep(1)
    shot("10_hardware")

    # Bookmarks view
    key("F1"); time.sleep(1)
    shot("03_gateway_browser")

    # ================================================================
    # SECTION 2: Test Machine - auto-crack gets us to menu
    # ================================================================
    print("\n=== Test Machine (auto-connect + auto-crack) ===")
    start_client("--auto-join", AGENT, "--auto-connect", "128.185.0.4", "--auto-crack")
    time.sleep(6)

    st = screen_type()
    print(f"  Initial: {st}")

    # Might be on MessageScreen (welcome) or MenuScreen (if auto-crack worked fully)
    if "Message" in st:
        shot("server_message")
        key("Return"); time.sleep(1)

    if "UserID" in screen_type() or "Password" in screen_type():
        shot("server_userid")
        # Auto-crack should have filled in, just need to type pw and submit
        type_t("rosebud")
        key("Return"); time.sleep(1.5)

    if "Menu" in screen_type():
        shot("server_menu")
        opts = state().get("screen_options", [])
        print(f"  Menu options: {opts}")

        # File server
        key("1"); time.sleep(1.5)
        shot("server_fileserver")
        key("BackSpace"); time.sleep(1)

        # Logs
        key("2"); time.sleep(1.5)
        shot("server_logs")
        key("BackSpace"); time.sleep(1)

        # Console
        key("3"); time.sleep(1)
        shot("server_console")
        key("BackSpace"); time.sleep(1)

    key("Escape"); time.sleep(1)

    # ================================================================
    # SECTION 3: InterNIC
    # ================================================================
    print("\n=== InterNIC ===")
    start_client("--auto-join", AGENT, "--auto-connect", "458.615.48.651")
    time.sleep(6)

    if "Message" in screen_type():
        shot("server_internic_welcome")
        key("Return"); time.sleep(1)

    if "Menu" in screen_type():
        shot("server_internic_menu")
        key("1"); time.sleep(1.5)  # Browse/Search -> LinksScreen
        shot("server_links")
        key("Escape"); time.sleep(1)

    # ================================================================
    # SECTION 4: Bank
    # ================================================================
    print("\n=== Bank ===")
    start_client("--auto-join", AGENT, "--auto-connect", "537.949.382.702")
    time.sleep(6)

    if "Menu" in screen_type():
        shot("server_bank_menu")

        # About Us -> CompanyInfo
        key("1"); time.sleep(1.5)
        shot("server_companyinfo")
        key("BackSpace"); time.sleep(1)

        # Create Account -> Dialog
        key("2"); time.sleep(1.5)
        shot("server_dialog")
        key("BackSpace"); time.sleep(1)

        # Manage Account -> UserID
        key("3"); time.sleep(1.5)
        shot("server_bank_userid")
        key("Escape"); time.sleep(1)

    # ================================================================
    # SECTION 5: Corporate ISM - Records + Security
    # ================================================================
    print("\n=== Corporate ISM ===")
    start_client("--auto-join", AGENT, "--auto-connect", "106.307.749.496", "--auto-crack")
    time.sleep(8)

    if "Menu" in screen_type():
        opts = state().get("screen_options", [])
        print(f"  ISM options: {opts}")

        for i, opt in enumerate(opts):
            key(str(i + 1)); time.sleep(1.5)
            st = screen_type()
            sub = state().get("screen_subtitle", "")
            name = opt.lower().replace(" ", "_").replace("/", "_")[:20]
            shot(f"server_ism_{name}")
            key("BackSpace"); time.sleep(1)

    key("Escape"); time.sleep(1)

    # ================================================================
    # SECTION 6: Connecting animation + Login screen
    # ================================================================
    print("\n=== Special screens ===")
    start_client()
    time.sleep(2)
    shot("01_login")

    # Type credentials for login screenshot
    type_t("Agent"); key("Tab"); type_t("test")
    shot("02_login_typed")

    # ================================================================
    # SECTION 7: Light theme
    # ================================================================
    print("\n=== Light Theme ===")
    start_client("--auto-join", AGENT, "--light-theme")
    time.sleep(4)

    key("F1"); time.sleep(1)
    shot("light_bookmarks")

    key("F4"); time.sleep(1)
    shot("light_gateway")

    key("F7"); time.sleep(1)
    shot("light_software")

    print(f"\nAll screenshots saved to {SCREENSHOT_DIR}/")
    for f in sorted(os.listdir(SCREENSHOT_DIR)):
        if f.endswith('.png') and not f.startswith(('full_', 'gameplay_', 'db_')):
            print(f"  {f}")

finally:
    cleanup()
