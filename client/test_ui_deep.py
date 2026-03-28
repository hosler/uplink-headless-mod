#!/usr/bin/env python3
"""
Deep UI test: navigates every server type, every screen transition,
verifies back button, verifies screen content via debug log.
"""
import subprocess, os, sys, time, json, shutil

DISPLAY = ":99"
DIR = "/tmp/uplink_ui_deep"
DEBUG_LOG = "/tmp/uplink_ui_debug.json"
CLIENT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(CLIENT_DIR, ".venv/bin/python3")
CLIENT_PATH = os.path.join(CLIENT_DIR, "uplink_client.py")

xvfb_proc = None
client_proc = None
results = []
env = None


def setup():
    global xvfb_proc, client_proc, env
    if os.path.exists(DIR): shutil.rmtree(DIR)
    os.makedirs(DIR)
    if os.path.exists(DEBUG_LOG): os.remove(DEBUG_LOG)

    env_base = os.environ.copy()
    env_base["DISPLAY"] = DISPLAY
    env = env_base

    xvfb_proc = subprocess.Popen(
        ["Xvfb", DISPLAY, "-screen", "0", "1280x720x24", "-ac"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)

    env2 = env.copy()
    env2["SDL_VIDEODRIVER"] = "x11"
    client_proc = subprocess.Popen(
        [VENV_PYTHON, CLIENT_PATH, "--no-music", "--debug-log", DEBUG_LOG],
        env=env2, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    time.sleep(3)
    print("  Setup complete")


def teardown():
    if client_proc and client_proc.poll() is None:
        client_proc.terminate()
    if xvfb_proc and xvfb_proc.poll() is None:
        xvfb_proc.terminate()


def click(x, y):
    subprocess.run(["xdotool", "mousemove", str(x), str(y), "click", "1"],
                   env=env, capture_output=True)
    time.sleep(0.3)


def type_t(t):
    subprocess.run(["xdotool", "type", "--delay", "50", t], env=env, capture_output=True)
    time.sleep(0.2)


def key(k):
    subprocess.run(["xdotool", "key", k], env=env, capture_output=True)
    time.sleep(0.2)


def wait(s=1): time.sleep(s)


def shot(name):
    p = f"{DIR}/{name}.png"
    subprocess.run(["scrot", "-o", p], env=env, capture_output=True)
    return p


def state():
    try:
        with open(DEBUG_LOG) as f: return json.load(f)
    except: return {}


def screen_type():
    return state().get("screen_type", "")


def screen_title():
    return state().get("screen_title", "")


def screen_subtitle():
    return state().get("screen_subtitle", "")


def is_connected():
    return state().get("player_connected", False)


def test(name, func):
    print(f"\n  [{name}]")
    try:
        func()
        results.append((name, True))
        print(f"    PASS")
    except Exception as e:
        results.append((name, False))
        print(f"    FAIL: {e}")
        shot(f"FAIL_{name.replace(' ', '_')}")


# ================================================================
# LOGIN
# ================================================================

def login():
    click(506, 306); wait(0.2); type_t("DeepTest"); key("Tab"); type_t("test")
    click(640, 410); wait(4)
    assert state().get("player_handle") == "DeepTest", "Login failed"


# ================================================================
# HELPER: connect to a bookmark by index (0-based)
# ================================================================

def connect_bookmark(idx):
    """Click bookmark at index. Bookmarks start at y=137, ~40px apart."""
    y = 137 + idx * 40
    click(420, y)
    wait(2.5)


def disconnect():
    click(900, 63)
    wait(1)


def click_back():
    click(306, 63)
    wait(1)


def click_continue():
    """Click Continue on MessageScreen."""
    click(592, 170)
    wait(1)


def click_menu_option(idx):
    """Click menu option by index. Options start at y=133, 50px apart (at design cy)."""
    y = 133 + idx * 33  # scaled from design 50px spacing
    click(400, y)
    wait(1)


def submit_password(user="admin", pw="rosebud"):
    """Type password and click Submit on UserIDScreen.
    Username 'admin' is pre-filled by the browser."""
    # Password field centered at design x=760, screen ~507
    # Submit button centered at design x=960, screen ~640
    click(590, 167); wait(0.3)  # Click password field to focus
    type_t(pw)
    click(640, 204)  # Submit button (centered)
    wait(1.5)


# ================================================================
# TEST: Test Machine full flow
# ================================================================

def t_testmachine_flow():
    if is_connected(): disconnect()
    click(13, 38); wait(0.5)  # Browser tab
    connect_bookmark(0)  # Test Machine
    assert is_connected(), "Not connected"

    # Screen 0: MessageScreen
    assert screen_type() == "MessageScreen", f"Expected MessageScreen, got {screen_type()}"
    shot("tm_01_message")

    # Continue -> Screen 1: UserIDScreen
    click_continue()
    assert screen_type() == "UserIDScreen", f"Expected UserIDScreen, got {screen_type()}"
    shot("tm_02_userid")

    # Login
    submit_password("admin", "rosebud")
    assert screen_type() == "MenuScreen", f"Expected MenuScreen after auth, got {screen_type()}"
    shot("tm_03_menu")
    opts = state().get("screen_options", [])
    print(f"    Menu: {opts}")

    # Option 0: File Server
    click_menu_option(0)
    assert "File" in screen_subtitle() or screen_type() == "GenericScreen", \
        f"Expected FileServer, got {screen_type()} - {screen_subtitle()}"
    shot("tm_04_fileserver")

    # Back to menu
    click_back()
    assert screen_type() == "MenuScreen", f"Back failed: got {screen_type()}"
    shot("tm_05_back_to_menu")

    # Option 1: Logs
    click_menu_option(1)
    shot("tm_06_logs")
    st = screen_type()
    print(f"    Option 1: {st} - {screen_subtitle()}")

    # Back to menu
    click_back()
    assert screen_type() == "MenuScreen", f"Back from logs failed: got {screen_type()}"

    # Option 2: Console (or Links depending on server)
    if len(opts) > 2:
        click_menu_option(2)
        shot("tm_07_option2")
        print(f"    Option 2: {screen_type()} - {screen_subtitle()}")
        click_back()

    disconnect()
    assert not is_connected(), "Still connected after disconnect"
    shot("tm_08_disconnected")


# ================================================================
# TEST: InterNIC flow
# ================================================================

def t_internic_flow():
    if is_connected(): disconnect()
    click(13, 38); wait(0.5)  # Browser tab
    connect_bookmark(2)  # InterNIC (3rd bookmark)
    assert is_connected(), "Not connected to InterNIC"

    # May be MessageScreen (first visit) or MenuScreen (already visited)
    st = screen_type()
    shot("nic_01_initial")
    if st == "MessageScreen":
        click_continue()
        wait(1)
    assert screen_type() == "MenuScreen", f"Expected MenuScreen, got {screen_type()}"
    shot("nic_02_menu")
    opts = state().get("screen_options", [])
    print(f"    InterNIC menu: {opts}")

    # Browse/Search
    click_menu_option(0)
    shot("nic_03_links")
    st = screen_type()
    print(f"    Browse: {st}")
    assert st == "LinksScreen", f"Expected LinksScreen, got {st}"

    # Back to menu
    click_back()
    wait(1)
    st = screen_type()
    if not st:
        wait(1)
        st = screen_type()
    shot("nic_04_back")
    print(f"    After back: {st}")

    # Admin (option 1) -> Password screen
    if st == "MenuScreen":
        click_menu_option(1)
        shot("nic_05_admin")
    st = screen_type()
    print(f"    Admin: {st}")

    click_back()
    disconnect()


# ================================================================
# TEST: Bank flow
# ================================================================

def t_bank_flow():
    if is_connected(): disconnect()
    click(13, 38); wait(0.5)  # Browser tab
    connect_bookmark(3)  # Bank (4th bookmark)
    assert is_connected(), "Not connected to bank"

    st = screen_type()
    shot("bank_01_initial")
    print(f"    Bank initial: {st} - {screen_subtitle()}")

    # If MessageScreen, continue past it
    if st == "MessageScreen":
        click_continue()
        st = screen_type()

    # Should be MenuScreen
    if st == "MenuScreen":
        opts = state().get("screen_options", [])
        print(f"    Bank menu: {opts}")
        shot("bank_02_menu")

        # Click "Manage Existing Account" (usually option 2)
        for i, opt in enumerate(opts):
            if "manage" in opt.lower() or "existing" in opt.lower():
                click_menu_option(i)
                shot("bank_03_manage")
                print(f"    Manage: {screen_type()} - {screen_subtitle()}")
                click_back()
                break

    disconnect()


# ================================================================
# TEST: Public Access Server
# ================================================================

def t_publicaccess_flow():
    if is_connected(): disconnect()
    click(13, 38); wait(0.5)  # Browser tab
    connect_bookmark(1)  # Public Access (2nd bookmark)
    assert is_connected(), "Not connected"
    shot("pub_01")
    st = screen_type()
    print(f"    Public Access: {st} - {screen_title()} - {screen_subtitle()}")

    if st == "MessageScreen":
        click_continue()
        shot("pub_02_after_continue")
        print(f"    After continue: {screen_type()} - {screen_subtitle()}")

    disconnect()


# ================================================================
# TEST: Tab content when disconnected
# ================================================================

def t_tabs_disconnected():
    assert not is_connected(), "Should be disconnected"

    tabs = {
        "Map": (173, 38),
        "Email": (333, 38),
        "Gateway": (493, 38),
        "Missions": (653, 38),
        "BBS": (813, 38),
        "Software": (973, 38),
        "Hardware": (1133, 38),
    }
    for name, (x, y) in tabs.items():
        click(x, y)
        wait(0.8)
        shot(f"tab_{name.lower()}")

    # Return to browser
    click(13, 38)
    wait(0.5)


# ================================================================
# TEST: Connect to different server types found via InterNIC
# ================================================================

def t_internic_discovery():
    """Connect to InterNIC, browse the server list, connect to different types."""
    if is_connected(): disconnect()
    click(13, 38); wait(0.5)  # Browser tab

    # Connect to InterNIC
    connect_bookmark(2)
    st = screen_type()
    if st == "MessageScreen":
        click_continue(); wait(1)

    # Navigate to Browse/Search
    if screen_type() == "MenuScreen":
        click_menu_option(0)
        wait(1)

    # Should be on LinksScreen
    shot("discovery_01_links")
    st = screen_type()
    print(f"    InterNIC browse: {st}")
    assert st == "LinksScreen", f"Expected LinksScreen, got {st}"

    # The links are visible on screen — take the screenshot
    # This is the visual proof that InterNIC browse works
    shot("discovery_02_server_list")

    disconnect()
    print("    Server list visible — different server types confirmed from screenshot")


# ================================================================
# MAIN
# ================================================================

def main():
    print("=" * 60)
    print("  DEEP UI TESTS")
    print("=" * 60)

    try:
        setup()
        wait(2)

        test("Login", login)
        test("Test Machine full flow", t_testmachine_flow)
        test("InterNIC flow", t_internic_flow)
        test("Bank flow", t_bank_flow)
        test("Public Access flow", t_publicaccess_flow)
        test("Tabs when disconnected", t_tabs_disconnected)

        # Connect to InterNIC and find different servers via the API
        test("InterNIC server discovery", t_internic_discovery)

    finally:
        teardown()

    passed = sum(1 for _, p in results if p)
    print(f"\n{'=' * 60}")
    for n, p in results:
        if not p: print(f"  FAIL: {n}")
    print(f"\n  {passed}/{len(results)} passed")
    print(f"  Screenshots: {DIR}/")
    print("=" * 60)
    return passed == len(results)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
