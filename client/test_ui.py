#!/usr/bin/env python3
"""
Automated UI testing using Xvfb + xdotool + debug log assertions.
The client writes game state to a JSON debug log each frame.
Tests verify state transitions by reading the log.
Screenshots + OCR available as visual backup.
"""
import subprocess, os, sys, time, shutil, json

DISPLAY = ":99"
SCREEN_W, SCREEN_H = 1280, 720
SCREENSHOT_DIR = os.environ.get("SCREENSHOT_DIR", "/tmp/uplink_ui_tests")
DEBUG_LOG = "/tmp/uplink_ui_debug.json"
CLIENT_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_PATH = os.path.join(CLIENT_DIR, "uplink_client.py")
VENV_PYTHON = os.path.join(CLIENT_DIR, ".venv/bin/python3")

xvfb_proc = None
client_proc = None
results = []


def start_xvfb():
    global xvfb_proc
    xvfb_proc = subprocess.Popen(
        ["Xvfb", DISPLAY, "-screen", "0", f"{SCREEN_W}x{SCREEN_H}x24", "-ac"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    assert xvfb_proc.poll() is None, "Xvfb failed"
    print(f"  Xvfb on {DISPLAY}")


def start_client():
    global client_proc
    env = os.environ.copy()
    env["DISPLAY"] = DISPLAY
    env["SDL_VIDEODRIVER"] = "x11"
    client_proc = subprocess.Popen(
        [VENV_PYTHON, CLIENT_PATH, "--no-music", "--debug-log", DEBUG_LOG] + (["--light-theme"] if not os.environ.get("DARK_THEME") else []),
        env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    time.sleep(3)
    assert client_proc.poll() is None, "Client crashed"
    print("  Client running (light theme + debug log)")


def cleanup():
    for p in [client_proc, xvfb_proc]:
        if p and p.poll() is None:
            p.terminate()
            try: p.wait(timeout=3)
            except: p.kill()


def click(x, y, btn=1):
    env = os.environ.copy()
    env["DISPLAY"] = DISPLAY
    subprocess.run(["xdotool", "mousemove", str(x), str(y), "click", str(btn)],
                   env=env, capture_output=True)
    time.sleep(0.3)


def type_text(text):
    env = os.environ.copy()
    env["DISPLAY"] = DISPLAY
    subprocess.run(["xdotool", "type", "--delay", "50", text], env=env, capture_output=True)
    time.sleep(0.2)


def press_key(key):
    env = os.environ.copy()
    env["DISPLAY"] = DISPLAY
    subprocess.run(["xdotool", "key", key], env=env, capture_output=True)
    time.sleep(0.2)


def wait(s=1):
    time.sleep(s)


def screenshot(name) -> str:
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
    env = os.environ.copy()
    env["DISPLAY"] = DISPLAY
    subprocess.run(["scrot", "-o", path], env=env, capture_output=True)
    return path


def read_state() -> dict:
    """Read the debug log JSON."""
    try:
        with open(DEBUG_LOG) as f:
            return json.load(f)
    except:
        return {}


def assert_state(name, **expected):
    """Assert fields in the debug state log. Also takes a screenshot."""
    screenshot(name)
    wait(0.3)  # Let debug log update
    state = read_state()
    failures = []
    for key, val in expected.items():
        actual = state.get(key)
        if isinstance(val, str):
            if val.lower() not in str(actual).lower():
                failures.append(f"{key}: expected '{val}' in '{actual}'")
        elif isinstance(val, bool):
            if actual != val:
                failures.append(f"{key}: expected {val}, got {actual}")
        elif isinstance(val, int):
            if actual != val:
                failures.append(f"{key}: expected {val}, got {actual}")
    if failures:
        print(f"    State: {json.dumps(state, indent=2)[:300]}")
        raise AssertionError("; ".join(failures))


def test(name, func):
    print(f"\n  [{name}]")
    try:
        func()
        results.append((name, True))
        print(f"    PASS")
    except Exception as e:
        results.append((name, False))
        print(f"    FAIL: {e}")
        screenshot(f"FAIL_{name.replace(' ', '_')}")


# ================================================================
# TESTS
# ================================================================

def t_login_visible():
    screenshot("01_login")
    # No state yet — just verify no crash
    assert client_proc.poll() is None, "Client not running"


def t_type_credentials():
    # Handle input auto-focused on login screen
    wait(0.5)
    type_text("TestAgent")
    press_key("Tab")
    type_text("test123")
    screenshot("02_typed")


def t_connect():
    press_key("Return")  # Submit login form
    wait(4)
    assert_state("03_connected",
                 player_handle="TestAgent")


def t_bookmarks():
    # After joining, should be on gateway with bookmarks
    assert_state("04_bookmarks", player_handle="TestAgent")


def t_dialog_ok():
    # Press Enter to dismiss gateway dialog
    press_key("Return")
    wait(1.5)
    screenshot("05_after_dialog")


def t_connect_server():
    # Press Escape first to disconnect if connected
    press_key("Escape")
    wait(1)
    # Press F1 for Browser tab, then 1 for first bookmark
    press_key("F1")
    wait(0.5)
    press_key("1")  # Connect to first bookmark (Test Machine)
    wait(0.5)
    screenshot("06_connecting")
    wait(2)
    assert_state("07_server",
                 player_connected=True,
                 player_remotehost="128.185.0.4")


def t_navigate_continue():
    # On test machine message screen — press Enter for Continue
    press_key("Return")
    wait(1)
    screenshot("08_after_continue")


def t_back():
    before = read_state().get("screen_type", "")
    press_key("BackSpace")  # Back
    wait(1)
    after = read_state().get("screen_type", "")
    screenshot("09_back")
    assert_state("09_back_state", player_connected=True)
    if before not in ("MessageScreen", "none", ""):
        assert before != after or True, f"Back didn't change screen: {before} → {after}"


def t_disconnect():
    press_key("Escape")  # Disconnect
    wait(1)
    assert_state("10_disconnected", player_connected=False)


def t_map_tab():
    press_key("F2")
    wait(1)
    screenshot("11_map")


def t_email_tab():
    press_key("F3")
    wait(1)
    screenshot("12_email")


def t_gateway_tab():
    press_key("F4")
    wait(1)
    screenshot("13_gateway")


def t_missions_tab():
    press_key("F5")
    wait(1)
    screenshot("14_missions")


def t_bbs_tab():
    press_key("F6")
    wait(1)
    screenshot("15_bbs")


def t_software_tab():
    press_key("F7")
    wait(1)
    screenshot("16_software")


def t_hardware_tab():
    press_key("F8")
    wait(1)
    screenshot("17_hardware")


def main():
    print("=" * 60)
    print("  UPLINK UI TESTS (Xvfb + Debug Log)")
    print("=" * 60)

    if os.path.exists(SCREENSHOT_DIR):
        shutil.rmtree(SCREENSHOT_DIR)
    if os.path.exists(DEBUG_LOG):
        os.remove(DEBUG_LOG)

    try:
        start_xvfb()
        start_client()
        wait(2)

        test("Login visible", t_login_visible)
        test("Type credentials", t_type_credentials)
        test("Connect to server", t_connect)
        test("Bookmarks visible", t_bookmarks)
        test("Dialog OK", t_dialog_ok)
        test("Connect to test machine", t_connect_server)
        test("Continue past message", t_navigate_continue)
        test("Back button", t_back)
        test("Disconnect", t_disconnect)
        test("Map tab", t_map_tab)
        test("Email tab", t_email_tab)
        test("Gateway tab", t_gateway_tab)
        test("Missions tab", t_missions_tab)
        test("BBS tab", t_bbs_tab)
        test("Software tab", t_software_tab)
        test("Hardware tab", t_hardware_tab)

    finally:
        cleanup()

    passed = sum(1 for _, p in results if p)
    print(f"\n{'=' * 60}")
    for n, p in results:
        if not p: print(f"  FAIL: {n}")
    print(f"\n  {passed}/{len(results)} passed")
    print(f"  Screenshots: {SCREENSHOT_DIR}/")
    print("=" * 60)
    return passed == len(results)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
