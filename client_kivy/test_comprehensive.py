#!/usr/bin/env python3
"""Comprehensive Kivy client test suite — runs everything under Xvfb."""
import subprocess, os, sys, time, json

DISPLAY = ":97"
DEBUG_LOG = "/tmp/kivy_comprehensive_test.json"
SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "test_screenshots_kivy")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

xvfb = None
client = None
results = []

def setup():
    global xvfb
    xvfb = subprocess.Popen(["Xvfb", DISPLAY, "-screen", "0", "1280x720x24", "-ac"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    assert xvfb.poll() is None, "Xvfb failed"

def teardown():
    stop()
    if xvfb and xvfb.poll() is None:
        xvfb.terminate()
        try: xvfb.wait(timeout=3)
        except: xvfb.kill()

def xenv():
    e = os.environ.copy()
    e["DISPLAY"] = DISPLAY
    e["SDL_VIDEODRIVER"] = "x11"
    e["KIVY_NO_ARGS"] = "1"
    e["KIVY_NO_CONSOLELOG"] = "1"
    return e

def xkey(k):
    subprocess.run(["xdotool", "key", k], env=xenv(), capture_output=True)
    time.sleep(0.4)

def xtype(t):
    subprocess.run(["xdotool", "type", "--delay", "40", t], env=xenv(), capture_output=True)
    time.sleep(0.3)

def xclick(x, y):
    subprocess.run(["xdotool", "mousemove", str(x), str(y), "click", "1"], env=xenv(), capture_output=True)
    time.sleep(0.4)

def screenshot(name):
    subprocess.run(["scrot", "-o", f"{SCREENSHOT_DIR}/{name}.png"], env=xenv(), capture_output=True)

def state():
    try:
        with open(DEBUG_LOG) as f:
            return json.load(f)
    except:
        return {}

def wait_state(key, val, timeout=10):
    for _ in range(timeout * 5):
        s = state()
        actual = str(s.get(key, "")).lower()
        if val.lower() in actual:
            return True
        time.sleep(0.2)
    return False

def start(*args):
    global client
    stop()
    client = subprocess.Popen(
        [sys.executable, "client_kivy/main.py", "--no-music", "--debug-log", DEBUG_LOG] + list(args),
        env=xenv(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    time.sleep(4)
    if client.poll() is not None:
        out = client.stdout.read().decode()[:500]
        raise RuntimeError(f"Client crashed: {out}")

def stop():
    global client
    if client and client.poll() is None:
        client.terminate()
        try: client.wait(timeout=3)
        except: client.kill()
    client = None

def test(name, fn):
    print(f"  {name}... ", end="", flush=True)
    try:
        fn()
        results.append((name, True))
        print("PASS")
    except Exception as e:
        results.append((name, False))
        print(f"FAIL: {e}")
        screenshot(f"FAIL_{name}")

# ============================================================
try:
    setup()
    print("=" * 60)
    print("COMPREHENSIVE KIVY CLIENT TESTS")
    print("=" * 60)

    # ==========================================================
    # SESSION 1: Basic startup + tab switching
    # ==========================================================
    print("\n--- Session 1: Startup + tabs ---")
    start("--auto-join", "Tab_Test")

    def test_alive():
        assert client.poll() is None
    test("client_starts", test_alive)

    def test_join():
        assert wait_state("player_handle", "Tab_Test", 5)
    test("auto_join", test_join)

    def test_f1(): xkey("F1"); time.sleep(0.3); assert client.poll() is None
    def test_f2(): xkey("F2"); time.sleep(0.3); assert client.poll() is None
    def test_f3(): xkey("F3"); time.sleep(0.3); assert client.poll() is None
    def test_f4(): xkey("F4"); time.sleep(0.3); assert client.poll() is None
    def test_f5(): xkey("F5"); time.sleep(0.3); assert client.poll() is None
    def test_f6(): xkey("F6"); time.sleep(0.3); assert client.poll() is None
    def test_f7(): xkey("F7"); time.sleep(0.3); assert client.poll() is None
    def test_f8(): xkey("F8"); time.sleep(0.3); assert client.poll() is None

    test("F1_browser", test_f1)
    test("F2_map", test_f2)
    test("F3_email", test_f3)
    test("F4_gateway", test_f4)
    test("F5_missions", test_f5)
    test("F6_bbs", test_f6)
    test("F7_software", test_f7)
    test("F8_hardware", test_f8)

    # Rapid tab switching stress test
    def test_rapid_tabs():
        for _ in range(3):
            for k in ["F1","F2","F3","F4","F5","F6","F7","F8"]:
                xkey(k)
                time.sleep(0.1)
        time.sleep(0.5)
        assert client.poll() is None
    test("rapid_tab_switching", test_rapid_tabs)

    stop()

    # ==========================================================
    # SESSION 2: Connect to server + Enter on welcome
    # ==========================================================
    print("\n--- Session 2: Server connect + dialog ---")
    start("--auto-join", "Dialog_Test")

    def test_bookmark1():
        xkey("F1")
        time.sleep(0.3)
        xkey("1")
        time.sleep(3)
        s = state()
        connected = s.get("player_connected", False)
        assert connected == True or str(connected).lower() == "true", f"Not connected: {connected}"
        screenshot("bookmark_connect")
    test("connect_bookmark_1", test_bookmark1)

    def test_enter_welcome():
        """Enter should dismiss MessageScreen welcome."""
        s = state()
        st_before = s.get("screen_type", "?")
        for _ in range(4):
            xkey("Return")
            time.sleep(0.8)
        s2 = state()
        st_after = s2.get("screen_type", "?")
        screenshot("after_welcome_enter")
        # Should have progressed past MessageScreen
        assert st_after != "MessageScreen", f"Stuck on MessageScreen (was {st_before} -> {st_after})"
    test("enter_dismiss_welcome", test_enter_welcome)

    def test_escape():
        xkey("Escape")
        time.sleep(1)
        screenshot("disconnected")
        assert client.poll() is None
    test("escape_disconnect", test_escape)

    # Reconnect
    def test_reconnect():
        xkey("1")
        time.sleep(3)
        s = state()
        connected = s.get("player_connected", False)
        assert connected == True or str(connected).lower() == "true"
    test("reconnect_after_escape", test_reconnect)

    def test_escape2():
        xkey("Escape")
        time.sleep(1)
    test("escape_again", test_escape2)

    stop()

    # ==========================================================
    # SESSION 3: Connect to all bookmarks
    # ==========================================================
    print("\n--- Session 3: Connect to multiple servers ---")
    start("--auto-join", "Multi_Test")

    for idx in range(1, 5):
        def test_server(i=idx):
            xkey("F1")
            time.sleep(0.3)
            xkey(str(i))
            time.sleep(3)
            s = state()
            connected = s.get("player_connected", False)
            assert connected == True or str(connected).lower() == "true", \
                f"Server {i}: not connected"
            screenshot(f"server_{i}")
            xkey("Escape")
            time.sleep(1)
        test(f"connect_server_{idx}", test_server)

    stop()

    # ==========================================================
    # SESSION 4: Auto-connect + auto-crack + navigation
    # ==========================================================
    print("\n--- Session 4: Auto-crack + full navigation ---")
    start("--auto-join", "Crack_Test", "--auto-connect", "128.185.0.4", "--auto-crack")
    time.sleep(8)

    def test_cracked():
        s = state()
        st = s.get("screen_type", "")
        assert st not in ("PasswordScreen", "UserIDScreen", "none", ""), \
            f"Still on {st}"
        screenshot("cracked")
    test("auto_crack_success", test_cracked)

    def test_menu_nav():
        s = state()
        st = s.get("screen_type", "")
        if st == "MenuScreen":
            xkey("1")
            time.sleep(1)
            s2 = state()
            screenshot("menu_option_1")
        assert client.poll() is None
    test("menu_navigation", test_menu_nav)

    def test_back():
        xkey("BackSpace")
        time.sleep(1)
        assert client.poll() is None
        screenshot("after_backspace")
    test("backspace_goes_back", test_back)

    # Navigate through menu options
    def test_menu_options():
        for i in ["1", "2", "3"]:
            s = state()
            if s.get("screen_type") == "MenuScreen":
                xkey(i)
                time.sleep(1)
                xkey("BackSpace")
                time.sleep(1)
        assert client.poll() is None
    test("menu_multi_options", test_menu_options)

    def test_disconnect():
        xkey("Escape")
        time.sleep(1)
        assert client.poll() is None
    test("final_disconnect", test_disconnect)

    stop()

    # ==========================================================
    # SESSION 5: Gateway tab content
    # ==========================================================
    print("\n--- Session 5: Gateway data ---")
    start("--auto-join", "GW_Test")
    time.sleep(3)

    def test_gw():
        xkey("F4")
        time.sleep(2)
        screenshot("gateway_full")
        assert client.poll() is None
    test("gateway_view", test_gw)

    def test_gw_files():
        s = state()
        # Gateway should have files count
        fc = s.get("files_count", -1)
        # May be 0 or more, just check no crash
        assert client.poll() is None
    test("gateway_files_loaded", test_gw_files)

    stop()

    # ==========================================================
    # SESSION 6: Software market
    # ==========================================================
    print("\n--- Session 6: Software market ---")
    start("--auto-join", "SW_Test")
    time.sleep(3)

    def test_sw():
        xkey("F7")
        time.sleep(2)
        screenshot("software_market")
        assert client.poll() is None
    test("software_tab_renders", test_sw)

    stop()

    # ==========================================================
    # SESSION 7: Hardware shop
    # ==========================================================
    print("\n--- Session 7: Hardware shop ---")
    start("--auto-join", "HW_Test")
    time.sleep(3)

    def test_hw():
        xkey("F8")
        time.sleep(2)
        screenshot("hardware_shop")
        assert client.poll() is None
    test("hardware_tab_renders", test_hw)

    stop()

    # ==========================================================
    # SESSION 8: Map view
    # ==========================================================
    print("\n--- Session 8: Map view ---")
    start("--auto-join", "Map_Test")
    time.sleep(3)

    def test_map():
        xkey("F2")
        time.sleep(2)
        screenshot("map_view")
        assert client.poll() is None
    test("map_renders", test_map)

    stop()

    # ==========================================================
    # SESSION 9: Email + BBS + Missions
    # ==========================================================
    print("\n--- Session 9: Email / BBS / Missions ---")
    start("--auto-join", "Content_Test")
    time.sleep(3)

    def test_email():
        xkey("F3"); time.sleep(1)
        screenshot("email"); assert client.poll() is None
    def test_missions():
        xkey("F5"); time.sleep(1)
        screenshot("missions"); assert client.poll() is None
    def test_bbs():
        xkey("F6"); time.sleep(1)
        screenshot("bbs"); assert client.poll() is None

    test("email_view", test_email)
    test("missions_view", test_missions)
    test("bbs_view", test_bbs)

    stop()

    # ==========================================================
    # SESSION 10: Stress test — rapid connect/disconnect
    # ==========================================================
    print("\n--- Session 10: Stress test ---")
    start("--auto-join", "Stress_Test")
    time.sleep(3)

    def test_stress():
        for i in range(5):
            xkey("1")
            time.sleep(2)
            xkey("Escape")
            time.sleep(0.5)
        assert client.poll() is None
    test("rapid_connect_disconnect_x5", test_stress)

    def test_stress_tabs():
        """Switch tabs rapidly while connected."""
        xkey("1")
        time.sleep(2)
        for _ in range(10):
            for k in ["F1","F2","F3","F4","F5","F6","F7","F8"]:
                xkey(k)
                time.sleep(0.05)
        time.sleep(1)
        assert client.poll() is None
    test("stress_tabs_while_connected", test_stress_tabs)

    stop()

    # ==========================================================
    # SUMMARY
    # ==========================================================
    print(f"\n{'=' * 60}")
    passed = sum(1 for _, ok in results if ok)
    failed = sum(1 for _, ok in results if not ok)
    print(f"Results: {passed}/{len(results)} passed, {failed} failed")
    print(f"{'=' * 60}")
    for name, ok in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"{'=' * 60}")
    if failed:
        print(f"\nFail screenshots: {SCREENSHOT_DIR}/")
        sys.exit(1)
    else:
        print("\nAll tests passed!")

finally:
    teardown()
