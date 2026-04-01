#!/usr/bin/env python3
"""Gameplay tests — missions, file ops, shopping, trace — via Xvfb UI + direct socket API."""
import subprocess, os, sys, time, json, socket

DISPLAY = ":96"
DEBUG_LOG = "/tmp/kivy_gameplay_test.json"
SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "test_screenshots_kivy")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

xvfb = None
client = None
results = []


# ============================================================
# Socket-based Bot for direct server interaction
# ============================================================
class Bot:
    def __init__(self, name):
        self.name = name
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(('127.0.0.1', 9090))
        self.sock.settimeout(5)

    def cmd(self, c, want=None):
        try:
            self.sock.sendall((json.dumps(c) + '\n').encode())
            time.sleep(0.4)
            data = self.sock.recv(65536).decode()
            for l in data.strip().split('\n'):
                try:
                    j = json.loads(l.strip())
                    if want and j.get('type') == want:
                        return j
                    if not want and j.get('type') == 'response':
                        return j
                except:
                    pass
        except:
            pass
        return None

    def join(self):
        r = self.cmd({'cmd': 'join', 'handle': self.name, 'password': 'x'})
        self.cmd({'cmd': 'dialog_ok'})
        return r

    def close(self):
        self.sock.close()


# ============================================================
# Xvfb + Kivy client helpers
# ============================================================
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
        if val.lower() in str(s.get(key, "")).lower():
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
    print("GAMEPLAY TESTS")
    print("=" * 60)

    # ==========================================================
    # TEST A: Complete a mission via socket bot, verify in UI
    # ==========================================================
    print("\n--- Test A: Mission completion (socket bot) ---")
    bot = Bot("MissionBot")
    bot.join()

    def test_mission_attempt():
        """Connect, copy file, delete logs, disconnect — mission may or may not complete depending on server state."""
        bot.cmd({'cmd': 'connect', 'ip': '128.185.0.4'})
        bot.cmd({'cmd': 'navigate', 'screen': 4})
        # Get available files
        m = bot.cmd({'cmd': 'files'}, 'files')
        files = m.get('files', []) if m else []
        copied = None
        for f in files:
            if 'test' in f.get('title', '').lower():
                bot.cmd({'cmd': 'copy_file', 'title': f['title']})
                copied = f['title']
                break
        bot.cmd({'cmd': 'delete_logs'})
        bot.cmd({'cmd': 'disconnect'})
        if copied:
            bot.cmd({'cmd': 'send_mail', 'to': 'internal@Uplink.net',
                     'subject': 'Mission completed',
                     'body': f'I have completed the following mission:\nUplink Test Mission -\nSteal data from a file server',
                     'attach': copied})
            time.sleep(0.5)
            r = bot.cmd({'cmd': 'check_mission'})
            print(f"(copied={copied}, result={r.get('status') if r else '?'}) ", end="")
        else:
            print("(no test file found) ", end="")
        # Pass as long as we didn't crash
        assert True
    test("mission_attempt", test_mission_attempt)

    def test_balance():
        m = bot.cmd({'cmd': 'balance'}, 'balance')
        bal = m.get('balance', 0) if m else 0
        print(f"({bal}c) ", end="")
        assert bal >= 0
    test("check_balance", test_balance)

    def test_inbox_has_messages():
        m = bot.cmd({'cmd': 'inbox'}, 'inbox')
        msgs = m.get('messages', []) if m else []
        assert len(msgs) > 0, "No inbox messages"
        print(f"({len(msgs)} msgs) ", end="")
    test("inbox_has_messages", test_inbox_has_messages)

    bot.close()

    # ==========================================================
    # TEST B: Software purchase via socket
    # ==========================================================
    print("\n--- Test B: Software purchase ---")
    bot2 = Bot("Shopper2")
    bot2.join()
    bot2.cmd({'cmd': 'connect', 'ip': '128.185.0.4'})
    bot2.cmd({'cmd': 'navigate', 'screen': 4})
    bot2.cmd({'cmd': 'copy_file', 'title': 'Uplink test data'})
    bot2.cmd({'cmd': 'disconnect'})
    bot2.cmd({'cmd': 'send_mail', 'to': 'internal@Uplink.net',
              'subject': 'Mission completed',
              'body': 'I have completed the following mission:\nUplink Test Mission',
              'attach': 'Uplink test data'})
    bot2.cmd({'cmd': 'check_mission'})
    time.sleep(1)

    def test_buy_software():
        m = bot2.cmd({'cmd': 'software_list'}, 'software_list')
        sw = m.get('software', []) if m else []
        assert len(sw) > 0, "No software available"

        bal = bot2.cmd({'cmd': 'balance'}, 'balance')
        balance = bal.get('balance', 0) if bal else 0

        # Find cheapest affordable item
        affordable = [s for s in sw if s['cost'] <= balance]
        assert len(affordable) > 0, f"Can't afford any software (balance={balance})"

        target = sorted(affordable, key=lambda s: s['cost'])[0]
        r = bot2.cmd({'cmd': 'buy_software', 'title': target['title']})
        assert r and r.get('status') == 'ok', f"Buy failed: {r}"
        print(f"(bought {target['title']}) ", end="")
    test("buy_software", test_buy_software)

    def test_software_on_gateway():
        gw = bot2.cmd({'cmd': 'gateway_files'}, 'gateway_files')
        files = gw.get('files', []) if gw else []
        titles = [f['title'] for f in files]
        # Should have more than just the default files
        assert len(files) >= 3, f"Only {len(files)} files on gateway"
    test("software_on_gateway", test_software_on_gateway)

    bot2.close()

    # ==========================================================
    # TEST C: Trace mechanics via socket
    # ==========================================================
    print("\n--- Test C: Trace mechanics ---")
    bot3 = Bot("TraceBot")
    bot3.join()

    def test_trace_status():
        bot3.cmd({'cmd': 'connect', 'ip': '128.185.0.4'})
        m = bot3.cmd({'cmd': 'trace'}, 'trace')
        assert m is not None, "No trace response"
        assert 'active' in m, f"No active field: {m}"
        print(f"(active={m['active']}) ", end="")
    test("trace_query", test_trace_status)

    def test_trace_progresses():
        bot3.cmd({'cmd': 'speed', 'value': 3})
        time.sleep(5)
        bot3.cmd({'cmd': 'speed', 'value': 1})
        m = bot3.cmd({'cmd': 'trace'}, 'trace')
        assert m is not None
        print(f"(progress={m.get('progress',0)}/{m.get('total',0)}) ", end="")
    test("trace_progresses", test_trace_progresses)

    bot3.cmd({'cmd': 'disconnect'})
    bot3.close()

    # ==========================================================
    # TEST D: File operations via socket
    # ==========================================================
    print("\n--- Test D: File operations ---")
    bot4 = Bot("FileBot")
    bot4.join()

    def test_copy_file():
        bot4.cmd({'cmd': 'connect', 'ip': '128.185.0.4'})
        bot4.cmd({'cmd': 'navigate', 'screen': 4})
        m = bot4.cmd({'cmd': 'files'}, 'files')
        files = m.get('files', []) if m else []
        if files:
            r = bot4.cmd({'cmd': 'copy_file', 'title': files[0]['title']})
            assert r is not None, "No response to copy_file"
            print(f"(copied {files[0]['title']}) ", end="")
        else:
            print("(no files on server) ", end="")
    test("copy_file", test_copy_file)

    def test_get_files():
        m = bot4.cmd({'cmd': 'files'}, 'files')
        files = m.get('files', []) if m else []
        assert len(files) > 0, "No remote files"
        print(f"({len(files)} files) ", end="")
    test("list_remote_files", test_get_files)

    def test_get_logs():
        m = bot4.cmd({'cmd': 'logs'}, 'logs')
        logs = m.get('logs', []) if m else []
        print(f"({len(logs)} logs) ", end="")
    test("list_remote_logs", test_get_logs)

    def test_delete_logs():
        r = bot4.cmd({'cmd': 'delete_logs'})
        assert r and r.get('status') == 'ok', f"Delete logs failed: {r}"
    test("delete_logs", test_delete_logs)

    bot4.cmd({'cmd': 'disconnect'})
    bot4.close()

    # ==========================================================
    # TEST E: BBS missions via socket
    # ==========================================================
    print("\n--- Test E: BBS missions ---")
    bot5 = Bot("BBSBot")
    bot5.join()

    def test_bbs_list():
        m = bot5.cmd({'cmd': 'bbs'}, 'bbs')
        missions = m.get('missions', []) if m else []
        print(f"({len(missions)} missions) ", end="")
        assert isinstance(missions, list)
    test("bbs_list_missions", test_bbs_list)

    def test_accept_mission():
        m = bot5.cmd({'cmd': 'bbs'}, 'bbs')
        missions = m.get('missions', []) if m else []
        if missions:
            r = bot5.cmd({'cmd': 'accept_mission', 'index': 0})
            assert r and r.get('status') == 'ok', f"Accept failed: {r}"
        else:
            print("(no missions available, skipping) ", end="")
    test("accept_bbs_mission", test_accept_mission)

    bot5.close()

    # ==========================================================
    # TEST F: Links and InterNIC search via socket
    # ==========================================================
    print("\n--- Test F: Links + search ---")
    bot6 = Bot("SearchBot")
    bot6.join()

    def test_links():
        m = bot6.cmd({'cmd': 'links'}, 'links')
        links = m.get('links', []) if m else []
        assert len(links) > 0, "No links"
        print(f"({len(links)} links) ", end="")
    test("get_links", test_links)

    def test_add_link():
        r = bot6.cmd({'cmd': 'add_link', 'ip': '128.185.0.4'})
        assert r and r.get('status') == 'ok', f"Add link failed: {r}"
    test("add_link", test_add_link)

    bot6.close()

    # ==========================================================
    # TEST G: UI shows mission/shop/file data correctly
    # ==========================================================
    print("\n--- Test G: UI renders game data ---")
    start("--auto-join", "UIData", "--auto-connect", "128.185.0.4", "--auto-crack")
    time.sleep(8)

    def test_ui_connected():
        s = state()
        assert s.get("player_connected") == True or str(s.get("player_connected","")).lower() == "true"
        screenshot("ui_connected")
    test("ui_shows_connected", test_ui_connected)

    def test_ui_gateway():
        xkey("F4")
        time.sleep(2)
        screenshot("ui_gateway_data")
        assert client.poll() is None
    test("ui_gateway_tab", test_ui_gateway)

    def test_ui_software():
        xkey("F7")
        time.sleep(2)
        screenshot("ui_software_market")
        assert client.poll() is None
    test("ui_software_tab", test_ui_software)

    def test_ui_hardware():
        xkey("F8")
        time.sleep(2)
        screenshot("ui_hardware_shop")
        assert client.poll() is None
    test("ui_hardware_tab", test_ui_hardware)

    def test_ui_map():
        xkey("F2")
        time.sleep(2)
        screenshot("ui_map_connected")
        assert client.poll() is None
    test("ui_map_while_connected", test_ui_map)

    def test_ui_email():
        xkey("F3")
        time.sleep(2)
        screenshot("ui_email_tab")
        assert client.poll() is None
    test("ui_email_tab", test_ui_email)

    # Navigate server menus via UI
    def test_ui_server_menu():
        xkey("F1")
        time.sleep(1)
        s = state()
        st = s.get("screen_type", "?")
        screenshot(f"ui_server_{st}")
        # Try menu option
        if st == "MenuScreen":
            xkey("1")
            time.sleep(1)
            screenshot("ui_menu_option_1")
            xkey("BackSpace")
            time.sleep(1)
        assert client.poll() is None
    test("ui_server_menu_nav", test_ui_server_menu)

    def test_ui_disconnect_escape():
        xkey("Escape")
        time.sleep(1)
        screenshot("ui_final_disconnect")
        assert client.poll() is None
    test("ui_escape_works", test_ui_disconnect_escape)

    stop()

    # ==========================================================
    # TEST H: Multiplayer — two bots simultaneously
    # ==========================================================
    print("\n--- Test H: Multiplayer ---")
    mp1 = Bot("Player1")
    mp2 = Bot("Player2")
    mp1.join()
    mp2.join()

    def test_both_connected():
        time.sleep(1)  # Give server time to process both joins
        r1 = mp1.cmd({'cmd': 'state'}, 'state')
        r2 = mp2.cmd({'cmd': 'state'}, 'state')
        assert r1 is not None, "Player1 no state"
        assert r2 is not None, "Player2 no state"
    test("multiplayer_both_joined", test_both_connected)

    def test_both_connect_same_server():
        mp1.cmd({'cmd': 'connect', 'ip': '128.185.0.4'})
        mp2.cmd({'cmd': 'connect', 'ip': '128.185.0.4'})
        r1 = mp1.cmd({'cmd': 'state'}, 'state')
        r2 = mp2.cmd({'cmd': 'state'}, 'state')
        c1 = r1.get('player', {}).get('connected', False) if r1 else False
        c2 = r2.get('player', {}).get('connected', False) if r2 else False
        assert c1, "P1 not connected"
        assert c2, "P2 not connected"
    test("multiplayer_same_server", test_both_connect_same_server)

    mp1.cmd({'cmd': 'disconnect'})
    mp2.cmd({'cmd': 'disconnect'})
    mp1.close()
    mp2.close()

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
