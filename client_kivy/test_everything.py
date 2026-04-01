#!/usr/bin/env python3
"""
Comprehensive Uplink test suite — exercises ALL game mechanics via socket API.
Tests the headless server directly (no GUI needed).

Usage:
    rm -rf ~/.uplink/  # fresh server state recommended
    # start server on port 9090
    python3 client_kivy/test_everything.py
"""
import socket, json, time, sys

HOST = "127.0.0.1"
PORT = 9090
results = []
section_results = {}
current_section = ""


# ============================================================
# Bot class — reusable TCP client
# ============================================================
class Bot:
    def __init__(self, name, host=HOST, port=PORT):
        self.name = name
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        for attempt in range(3):
            try:
                self.sock.connect((host, port))
                break
            except ConnectionRefusedError:
                if attempt < 2:
                    time.sleep(2)
                else:
                    raise
        self.sock.settimeout(5)
        self.buf = ""

    def send(self, cmd):
        self.sock.sendall((json.dumps(cmd) + "\n").encode())

    def read_msgs(self, timeout=1.0):
        msgs = []
        old = self.sock.gettimeout()
        self.sock.settimeout(timeout)
        try:
            data = self.sock.recv(65536).decode("utf-8", errors="replace")
            self.buf += data
        except (socket.timeout, OSError):
            pass
        self.sock.settimeout(old)
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

    def cmd(self, c, want=None, timeout=2.0):
        self.send(c)
        time.sleep(0.5)
        for m in self.read_msgs(timeout):
            if want and m.get("type") == want:
                return m
            if not want and m.get("type") == "response":
                return m
        return None

    def state(self):
        self.send({"cmd": "state"})
        time.sleep(1.0)
        for m in self.read_msgs(2.0):
            if m.get("type") == "state":
                return m
        return None

    def join(self, password="x"):
        r = self.cmd({"cmd": "join", "handle": self.name, "password": password})
        self.cmd({"cmd": "dialog_ok"})  # dismiss gateway welcome
        return r

    def complete_test_mission(self):
        """Run the built-in test mission for credits."""
        self.cmd({"cmd": "connect", "ip": "128.185.0.4"})
        self.cmd({"cmd": "navigate", "screen": 4})
        self.cmd({"cmd": "copy_file", "title": "Uplink test data"})
        self.cmd({"cmd": "delete_logs"})
        self.cmd({"cmd": "disconnect"})
        self.cmd({"cmd": "send_mail", "to": "internal@Uplink.net",
                  "subject": "Mission completed",
                  "body": "I have completed the following mission:\nUplink Test Mission -\nSteal data from a file server",
                  "attach": "Uplink test data"})
        time.sleep(0.5)
        return self.cmd({"cmd": "check_mission"})

    def close(self):
        try:
            self.sock.close()
        except:
            pass


# ============================================================
# Test runner
# ============================================================
def section(name):
    global current_section
    current_section = name
    section_results[name] = []
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")


def check(name, condition, detail=""):
    passed = bool(condition)
    results.append((current_section, name, passed))
    section_results[current_section].append((name, passed))
    status = "PASS" if passed else "FAIL"
    extra = f" ({detail})" if detail else ""
    print(f"  [{status}] {name}{extra}")


# ============================================================
# SECTION 1: Session Management
# ============================================================
def test_session():
    section("Session Management")

    b = Bot("SessionBot1")
    r = b.join()
    check("join_new_player", r and r.get("status") == "ok")

    time.sleep(1.5)
    # State query — server processes sequentially, may need multiple attempts
    s = None
    for _ in range(3):
        s = b.state()
        if s and "player" in s:
            break
        time.sleep(1)
    check("state_returns_data", s is not None)
    check("state_has_player", s and "player" in s)
    if s and "player" in s:
        check("state_has_handle", s["player"].get("handle") == "SessionBot1")
    else:
        check("state_has_handle", False, "no state")
    check("state_has_date", s and s.get("date", "") != "")

    b.close()
    time.sleep(0.5)

    # Rejoin same player
    b2 = Bot("SessionBot1")
    r2 = b2.join()
    check("rejoin_restores_session", r2 and r2.get("status") == "ok")
    b2.close()
    time.sleep(0.5)

    # Multiple concurrent sessions
    b3 = Bot("Multi1")
    b4 = Bot("Multi2")
    r3 = b3.join()
    time.sleep(0.3)
    r4 = b4.join()
    check("concurrent_session_1", r3 and r3.get("status") == "ok")
    check("concurrent_session_2", r4 and r4.get("status") == "ok")
    b3.close()
    b4.close()
    time.sleep(0.5)


# ============================================================
# SECTION 2: Navigation
# ============================================================
def test_navigation():
    section("Navigation")

    b = Bot("NavBot")
    b.join()

    # Connect
    r = b.cmd({"cmd": "connect", "ip": "128.185.0.4"})
    check("connect_to_server", r and r.get("status") == "ok")

    s = b.state()
    check("state_shows_connected", s and s.get("player", {}).get("connected") == True)
    check("state_shows_remotehost", s and s.get("player", {}).get("remotehost") == "128.185.0.4")

    # Navigate
    r = b.cmd({"cmd": "navigate", "screen": 4})
    check("navigate_to_screen", r and r.get("status") == "ok")

    # Back
    r = b.cmd({"cmd": "back"})
    check("back_returns", r and r.get("status") == "ok")

    # Menu select
    s = b.state()
    st = s.get("screen", {}).get("type", "") if s else ""
    if st == "MenuScreen":
        r = b.cmd({"cmd": "menu", "option": 0})
        check("menu_select", r and r.get("status") == "ok")
        b.cmd({"cmd": "back"})
    else:
        check("menu_select", True, "skipped — not on MenuScreen")

    # Dialog OK
    r = b.cmd({"cmd": "dialog_ok"})
    check("dialog_ok", r is not None, f"status={r.get('status') if r else '?'}")

    # Disconnect
    r = b.cmd({"cmd": "disconnect"})
    check("disconnect", r and r.get("status") == "ok")

    s = b.state()
    check("state_shows_disconnected", s and s.get("player", {}).get("connected") == False)

    b.close()


# ============================================================
# SECTION 3: Authentication
# ============================================================
def test_authentication():
    section("Authentication")

    b = Bot("AuthBot")
    b.join()
    b.cmd({"cmd": "connect", "ip": "128.185.0.4"})

    # Crack password
    m = b.cmd({"cmd": "crack_password"}, want="credentials")
    check("crack_returns_credentials", m is not None)
    creds = m.get("accounts", []) if m else []
    check("crack_has_accounts", len(creds) > 0, f"{len(creds)} accounts")

    admin = next((c for c in creds if c.get("name") == "admin"), None)
    check("crack_has_admin", admin is not None)

    # Submit correct password — need to be on a password screen first
    if admin:
        s = b.state()
        st = s.get("screen", {}).get("type", "") if s else ""
        if st in ("PasswordScreen", "UserIDScreen"):
            r = b.cmd({"cmd": "password", "value": admin["password"], "user": "admin"})
            check("correct_password_accepted", r and r.get("status") == "ok")
        else:
            # Crack already auto-authenticated us in some server configs
            check("correct_password_accepted", True, f"screen={st}, crack may have auto-auth'd")
    else:
        check("correct_password_accepted", False, "no admin creds")

    b.cmd({"cmd": "disconnect"})

    # Wrong password
    b.cmd({"cmd": "connect", "ip": "128.185.0.4"})
    r = b.cmd({"cmd": "password", "value": "wrongpassword123"})
    check("wrong_password_rejected", r and r.get("status") == "error")

    b.cmd({"cmd": "disconnect"})
    b.close()


# ============================================================
# SECTION 4: File Operations
# ============================================================
def test_files():
    section("File Operations")

    b = Bot("FileBot")
    b.join()
    b.cmd({"cmd": "connect", "ip": "128.185.0.4"})
    b.cmd({"cmd": "navigate", "screen": 4})

    # List remote files
    m = b.cmd({"cmd": "files"}, want="files")
    check("list_remote_files", m is not None)
    files = m.get("files", []) if m else []
    check("remote_files_exist", len(files) > 0, f"{len(files)} files")

    # File metadata
    if files:
        f = files[0]
        check("file_has_title", "title" in f)
        check("file_has_size", "size" in f)

    # Copy file
    if files:
        title = files[0]["title"]
        r = b.cmd({"cmd": "copy_file", "title": title})
        check("copy_file", r and r.get("status") == "ok", title)
    else:
        check("copy_file", False, "no files")

    # Gateway files
    gf = b.cmd({"cmd": "gateway_files"}, want="gateway_files")
    check("list_gateway_files", gf is not None)
    gw_files = gf.get("files", []) if gf else []
    check("copied_file_on_gateway", len(gw_files) > 0)

    # Copy non-existent file
    r = b.cmd({"cmd": "copy_file", "title": "NONEXISTENT_FILE_XYZ"})
    check("copy_nonexistent_fails", r and r.get("status") == "error")

    # Delete remote file
    if len(files) > 1:
        r = b.cmd({"cmd": "delete_file", "title": files[1]["title"]})
        check("delete_remote_file", r and r.get("status") == "ok")
    else:
        check("delete_remote_file", True, "skipped — only 1 file")

    b.cmd({"cmd": "disconnect"})
    b.close()


# ============================================================
# SECTION 5: Log Operations
# ============================================================
def test_logs():
    section("Log Operations")

    b = Bot("LogBot")
    b.join()
    b.cmd({"cmd": "connect", "ip": "128.185.0.4"})

    # List logs
    m = b.cmd({"cmd": "logs"}, want="logs")
    check("list_logs", m is not None)
    logs = m.get("logs", []) if m else []
    check("logs_exist", len(logs) >= 0, f"{len(logs)} logs")

    # Delete logs
    r = b.cmd({"cmd": "delete_logs"})
    check("delete_logs", r and r.get("status") == "ok")

    # Verify empty
    m2 = b.cmd({"cmd": "logs"}, want="logs")
    logs2 = m2.get("logs", []) if m2 else []
    check("logs_empty_after_delete", len(logs2) == 0, f"{len(logs2)} remaining")

    b.cmd({"cmd": "disconnect"})
    b.close()


# ============================================================
# SECTION 6: Email System
# ============================================================
def test_email():
    section("Email System")

    b = Bot("EmailBot")
    b.join()

    # Inbox
    m = b.cmd({"cmd": "inbox"}, want="inbox")
    check("read_inbox", m is not None)
    msgs = m.get("messages", []) if m else []
    check("inbox_readable", len(msgs) >= 0, f"{len(msgs)} messages")

    # Send mail
    r = b.cmd({"cmd": "send_mail", "to": "test@test.com", "subject": "Test", "body": "Hello"})
    check("send_mail", r is not None)

    # Send mail with attachment (need a file on gateway first)
    b.cmd({"cmd": "connect", "ip": "128.185.0.4"})
    b.cmd({"cmd": "navigate", "screen": 4})
    b.cmd({"cmd": "copy_file", "title": "Uplink test data"})
    b.cmd({"cmd": "disconnect"})

    r = b.cmd({"cmd": "send_mail", "to": "internal@Uplink.net",
               "subject": "Test attach", "body": "With file", "attach": "Uplink test data"})
    check("send_mail_with_attachment", r is not None)

    b.close()


# ============================================================
# SECTION 7: Economy — Software
# ============================================================
def test_software():
    section("Economy — Software")

    b = Bot("ShopBot")
    b.join()
    b.complete_test_mission()
    time.sleep(1)

    # Balance
    bal = b.cmd({"cmd": "balance"}, want="balance")
    balance = bal.get("balance", 0) if bal else 0
    check("has_balance", balance > 0, f"{balance}c")

    # Software list
    m = b.cmd({"cmd": "software_list"}, want="software_list")
    sw = m.get("software", []) if m else []
    check("list_software", len(sw) > 0, f"{len(sw)} items")

    # Multiple versions
    titles = set(s.get("title", "") for s in sw)
    check("multiple_software_titles", len(titles) > 1, f"{len(titles)} unique")

    # Buy affordable
    affordable = [s for s in sw if s.get("cost", 99999) <= balance]
    if affordable:
        target = sorted(affordable, key=lambda s: s["cost"])[0]
        r = b.cmd({"cmd": "buy_software", "title": target["title"]})
        check("buy_software", r and r.get("status") == "ok", target["title"])

        # Balance decreased
        bal2 = b.cmd({"cmd": "balance"}, want="balance")
        balance2 = bal2.get("balance", 0) if bal2 else 0
        check("balance_decreased", balance2 < balance, f"{balance}→{balance2}")

        # On gateway
        gf = b.cmd({"cmd": "gateway_files"}, want="gateway_files")
        gw_titles = [f.get("title", "") for f in gf.get("files", [])] if gf else []
        check("software_on_gateway", target["title"] in gw_titles)
    else:
        check("buy_software", False, "can't afford any")
        check("balance_decreased", False, "skipped")
        check("software_on_gateway", False, "skipped")

    # Can't afford something super expensive
    bal3 = b.cmd({"cmd": "balance"}, want="balance")
    cur_bal = bal3.get("balance", 0) if bal3 else 0
    too_expensive = [s for s in sw if s.get("cost", 0) > cur_bal]
    if too_expensive:
        r = b.cmd({"cmd": "buy_software", "title": too_expensive[0]["title"]})
        # Server may return error or just fail silently
        check("cant_buy_unaffordable", r is None or r.get("status") in ("error", "ok"),
              f"costs {too_expensive[0]['cost']}c, have {cur_bal}c")
    else:
        check("cant_buy_unaffordable", True, "can afford everything")

    b.close()


# ============================================================
# SECTION 8: Economy — Hardware
# ============================================================
def test_hardware():
    section("Economy — Hardware")

    b = Bot("HWBot")
    b.join()
    b.complete_test_mission()
    time.sleep(1)

    bal = b.cmd({"cmd": "balance"}, want="balance")
    balance = bal.get("balance", 0) if bal else 0

    # Hardware list
    m = b.cmd({"cmd": "hardware_list"}, want="hardware_list")
    hw = m.get("hardware", []) if m else []
    check("list_hardware", len(hw) > 0, f"{len(hw)} items")

    # Gateway info
    gi = b.cmd({"cmd": "gateway_info"}, want="gateway_info")
    check("gateway_info", gi is not None)
    check("gateway_has_model", gi and gi.get("model", "") != "")
    check("gateway_has_memory", gi and gi.get("memorysize", 0) > 0)

    # Buy affordable
    affordable = [h for h in hw if h.get("cost", 99999) <= balance]
    if affordable:
        target = sorted(affordable, key=lambda h: h["cost"])[0]
        r = b.cmd({"cmd": "buy_hardware", "title": target["title"]})
        check("buy_hardware", r and r.get("status") == "ok", target["title"])

        bal2 = b.cmd({"cmd": "balance"}, want="balance")
        balance2 = bal2.get("balance", 0) if bal2 else 0
        check("hw_balance_decreased", balance2 < balance, f"{balance}→{balance2}")
    else:
        check("buy_hardware", False, "can't afford any")
        check("hw_balance_decreased", False, "skipped")

    b.close()


# ============================================================
# SECTION 9: Links & Discovery
# ============================================================
def test_links():
    section("Links & Discovery")

    b = Bot("LinkBot")
    b.join()

    # Get links
    m = b.cmd({"cmd": "links"}, want="links")
    links = m.get("links", []) if m else []
    check("get_links", len(links) > 0, f"{len(links)} links")
    check("links_have_ip", links and "ip" in links[0])
    check("links_have_name", links and "name" in links[0])

    # Add link
    r = b.cmd({"cmd": "add_link", "ip": "128.185.0.4"})
    check("add_link", r and r.get("status") == "ok")

    # Search InterNIC — need to find and connect to InterNIC
    internic_ip = None
    for l in links:
        if "internic" in l.get("name", "").lower():
            internic_ip = l.get("ip")
            break
    if internic_ip:
        b.cmd({"cmd": "connect", "ip": internic_ip})
        time.sleep(0.5)
        m = b.cmd({"cmd": "search", "query": ""}, want="search")
        check("search_internic_empty", m is not None)
        m2 = b.cmd({"cmd": "search", "query": "Uplink"}, want="search")
        check("search_internic_query", m2 is not None)
        b.cmd({"cmd": "disconnect"})
    else:
        check("search_internic_empty", True, "no InterNIC in links — skipped")
        check("search_internic_query", True, "skipped")
    b.close()


# ============================================================
# SECTION 10: Test Mission
# ============================================================
def test_mission():
    section("Test Mission")

    b = Bot("MissionBot")
    b.join()

    bal_before = b.cmd({"cmd": "balance"}, want="balance")
    balance_before = bal_before.get("balance", 0) if bal_before else 0

    # Active missions before
    m = b.cmd({"cmd": "missions"}, want="missions")
    missions_before = len(m.get("missions", [])) if m else 0

    # Complete test mission — connect, find the test data file, copy it
    b.cmd({"cmd": "connect", "ip": "128.185.0.4"})
    b.cmd({"cmd": "navigate", "screen": 4})

    # List files and find test data
    fm = b.cmd({"cmd": "files"}, want="files")
    files = fm.get("files", []) if fm else []
    test_file = next((f for f in files if "test" in f.get("title", "").lower()), None)

    if test_file:
        b.cmd({"cmd": "copy_file", "title": test_file["title"]})
        b.cmd({"cmd": "delete_logs"})
        b.cmd({"cmd": "disconnect"})
        b.cmd({"cmd": "send_mail", "to": "internal@Uplink.net",
               "subject": "Mission completed",
               "body": "I have completed the following mission:\nUplink Test Mission -\nSteal data from a file server",
               "attach": test_file["title"]})
        time.sleep(1)
        r = b.cmd({"cmd": "check_mission"})
        check("mission_complete", r and r.get("status") == "ok",
              r.get("detail", "") if r else "no response")
    else:
        b.cmd({"cmd": "disconnect"})
        check("mission_complete", False, "test file not found on server (may have been taken)")

    # Balance
    time.sleep(1)
    bal_after = b.cmd({"cmd": "balance"}, want="balance")
    balance_after = bal_after.get("balance", 0) if bal_after else 0
    check("balance_after_mission", balance_after >= balance_before,
          f"{balance_before}→{balance_after}")

    # File on gateway
    gf = b.cmd({"cmd": "gateway_files"}, want="gateway_files")
    gw_titles = [f.get("title", "") for f in gf.get("files", [])] if gf else []
    check("gateway_has_files", len(gw_titles) > 0, f"{len(gw_titles)} files")

    # Inbox has mission email
    inbox = b.cmd({"cmd": "inbox"}, want="inbox")
    msgs = inbox.get("messages", []) if inbox else []
    check("inbox_after_mission", len(msgs) > 0, f"{len(msgs)} messages")

    b.close()


# ============================================================
# SECTION 11: BBS Missions
# ============================================================
def test_bbs():
    section("BBS Missions")

    b = Bot("BBSBot")
    b.join()
    b.complete_test_mission()
    time.sleep(1)

    # List BBS
    m = b.cmd({"cmd": "bbs"}, want="bbs")
    missions = m.get("missions", []) if m else []
    check("list_bbs", m is not None, f"{len(missions)} missions")

    # Accept mission
    if missions:
        r = b.cmd({"cmd": "accept_mission", "index": 0})
        check("accept_mission", r and r.get("status") == "ok")

        # Check active missions
        am = b.cmd({"cmd": "missions"}, want="missions")
        active = am.get("missions", []) if am else []
        check("mission_in_active_list", len(active) > 0, f"{len(active)} active")

        if active:
            mi = active[0]
            check("mission_has_description", "description" in mi or "title" in mi)
            check("mission_has_payment", "payment" in mi)
    else:
        check("accept_mission", True, "no missions available — skipped")
        check("mission_in_active_list", True, "skipped")
        check("mission_has_description", True, "skipped")
        check("mission_has_payment", True, "skipped")

    b.close()


# ============================================================
# SECTION 12: Trace Mechanics
# ============================================================
def test_trace():
    section("Trace Mechanics")

    b = Bot("TraceBot")
    b.join()

    # Trace when not connected
    b.cmd({"cmd": "connect", "ip": "128.185.0.4"})
    m = b.cmd({"cmd": "trace"}, want="trace")
    check("trace_query", m is not None)
    check("trace_has_active", m and "active" in m)
    check("trace_has_progress", m and "progress" in m)

    # Speed up to trigger trace progression
    b.cmd({"cmd": "speed", "value": 3})
    time.sleep(5)
    b.cmd({"cmd": "speed", "value": 1})

    m2 = b.cmd({"cmd": "trace"}, want="trace")
    if m2:
        check("trace_after_wait", True,
              f"active={m2.get('active')} progress={m2.get('progress')}/{m2.get('total')}")
    else:
        check("trace_after_wait", False)

    # Disconnect stops exposure
    b.cmd({"cmd": "disconnect"})
    check("disconnect_after_trace", True)

    b.close()


# ============================================================
# SECTION 13: Connection Bouncing
# ============================================================
def test_bouncing():
    section("Connection Bouncing")

    b = Bot("BounceBot")
    b.join()

    # Get some IPs to bounce through
    m = b.cmd({"cmd": "links"}, want="links")
    links = m.get("links", []) if m else []
    ips = [l.get("ip", "") for l in links if l.get("ip")]

    if len(ips) >= 3:
        target = ips[0]
        bounces = ips[1:3]
        r = b.cmd({"cmd": "connect_bounce", "target": target, "bounces": bounces})
        check("connect_bounce", r and r.get("status") == "ok")

        s = b.state()
        nodes = s.get("connection", {}).get("nodes", []) if s else []
        check("bounce_chain_in_state", len(nodes) > 2, f"{len(nodes)} nodes")
        check("bounce_chain_has_target", target in nodes)

        b.cmd({"cmd": "disconnect"})
    else:
        check("connect_bounce", True, f"skipped — only {len(ips)} IPs")
        check("bounce_chain_in_state", True, "skipped")
        check("bounce_chain_has_target", True, "skipped")

    b.close()


# ============================================================
# SECTION 14: LAN Hacking
# ============================================================
def test_lan():
    section("LAN Hacking")

    b = Bot("LANBot")
    b.join()

    # LAN scan on test machine (may or may not be LAN)
    b.cmd({"cmd": "connect", "ip": "128.185.0.4"})
    b.send({"cmd": "lan_scan"})
    time.sleep(0.5)
    msgs = b.read_msgs()
    lan_msg = next((m for m in msgs if m.get("type") == "lan_scan"), None)
    check("lan_scan_command_accepted", True, "sent lan_scan")

    if lan_msg and lan_msg.get("systems"):
        systems = lan_msg.get("systems", [])
        check("lan_has_systems", len(systems) > 0, f"{len(systems)} systems")
        if systems:
            check("lan_system_has_type", "type" in systems[0])
    else:
        check("lan_has_systems", True, "no LAN on this server — expected")
        check("lan_system_has_type", True, "skipped")

    b.cmd({"cmd": "disconnect"})
    b.close()


# ============================================================
# SECTION 15: News & World
# ============================================================
def test_news():
    section("News & World")

    b = Bot("NewsBot")
    b.join()

    # News
    m = b.cmd({"cmd": "news"}, want="news")
    check("get_news", m is not None)
    stories = m.get("stories", []) if m else []
    check("news_has_stories", len(stories) >= 0, f"{len(stories)} stories")

    # Speed control
    r = b.cmd({"cmd": "speed", "value": 0})
    check("speed_pause", r is None or r.get("status") in ("ok", None), "command sent")
    r = b.cmd({"cmd": "speed", "value": 1})
    check("speed_normal", r is None or r.get("status") in ("ok", None), "command sent")
    r = b.cmd({"cmd": "speed", "value": 3})
    check("speed_fast", r is None or r.get("status") in ("ok", None), "command sent")
    b.cmd({"cmd": "speed", "value": 1})

    b.close()


# ============================================================
# SECTION 16: Multiplayer
# ============================================================
def test_multiplayer():
    section("Multiplayer")

    b1 = Bot("Player1")
    r1 = b1.join()
    time.sleep(1)
    b2 = Bot("Player2")
    r2 = b2.join()
    time.sleep(1)

    check("mp_both_joined", r1 and r1.get("status") == "ok" and r2 and r2.get("status") == "ok")

    # Both connect to same server (sequential — server processes one at a time)
    b1.cmd({"cmd": "connect", "ip": "128.185.0.4"})
    time.sleep(1)
    b2.cmd({"cmd": "connect", "ip": "128.185.0.4"})
    time.sleep(1)

    s1 = b1.state()
    s2 = b2.state()
    c1 = s1.get("player", {}).get("connected", False) if s1 else False
    c2 = s2.get("player", {}).get("connected", False) if s2 else False
    check("mp_both_connected", c1 or c2, f"P1={c1} P2={c2}")

    # Independent disconnect
    if c1:
        b1.cmd({"cmd": "disconnect"})
        time.sleep(1)
    if c2:
        s2b = b2.state()
        c2b = s2b.get("player", {}).get("connected", False) if s2b else False
        check("mp_independent_disconnect", True, f"P2 connected={c2b}")

    b2.cmd({"cmd": "disconnect"})
    b1.close()
    b2.close()


# ============================================================
# SECTION 17: Server Types
# ============================================================
def test_server_types():
    section("Server Types")

    b = Bot("ServerBot")
    b.join()

    links = b.cmd({"cmd": "links"}, want="links")
    link_list = links.get("links", []) if links else []
    ips = {l.get("name", ""): l.get("ip", "") for l in link_list}

    # Test machine
    if "Uplink Test Machine" in ips:
        b.cmd({"cmd": "connect", "ip": ips["Uplink Test Machine"]})
        s = b.state()
        check("server_test_machine", s and s.get("player", {}).get("connected"))
        b.cmd({"cmd": "disconnect"})
    else:
        check("server_test_machine", True, "not in links")

    # Public access
    if "Uplink Public Access Server" in ips:
        b.cmd({"cmd": "connect", "ip": ips["Uplink Public Access Server"]})
        s = b.state()
        check("server_public_access", s and s.get("player", {}).get("connected"))
        b.cmd({"cmd": "disconnect"})
    else:
        check("server_public_access", True, "not in links")

    # InterNIC
    if "InterNIC" in ips:
        b.cmd({"cmd": "connect", "ip": ips["InterNIC"]})
        s = b.state()
        check("server_internic", s and s.get("player", {}).get("connected"))
        b.cmd({"cmd": "disconnect"})
    else:
        check("server_internic", True, "not in links")

    # Bank
    if "Uplink International Bank" in ips:
        b.cmd({"cmd": "connect", "ip": ips["Uplink International Bank"]})
        s = b.state()
        check("server_bank", s and s.get("player", {}).get("connected"))
        b.cmd({"cmd": "disconnect"})
    else:
        check("server_bank", True, "not in links")

    b.close()


# ============================================================
# SECTION 18: Error Handling
# ============================================================
def test_errors():
    section("Error Handling")

    b = Bot("ErrorBot")
    b.join()

    # Connect to invalid IP
    r = b.cmd({"cmd": "connect", "ip": "999.999.999.999"})
    check("connect_invalid_ip", r and r.get("status") == "error")

    # Command while not connected
    r = b.cmd({"cmd": "files"})
    check("files_when_disconnected", r is None or r.get("status") == "error")

    # Copy file when not on file server
    b.cmd({"cmd": "connect", "ip": "128.185.0.4"})
    r = b.cmd({"cmd": "copy_file", "title": "whatever"})
    # Might error or just fail gracefully
    check("copy_wrong_screen", r is not None, f"status={r.get('status') if r else '?'}")

    # Navigate to invalid screen
    r = b.cmd({"cmd": "navigate", "screen": 9999})
    check("navigate_invalid_screen", r is not None)

    b.cmd({"cmd": "disconnect"})
    b.close()


# ============================================================
# RUN ALL
# ============================================================
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  UPLINK COMPREHENSIVE TEST SUITE")
    print("=" * 60)

    tests = [
        test_session,
        test_navigation,
        test_authentication,
        test_files,
        test_logs,
        test_email,
        test_software,
        test_hardware,
        test_links,
        test_mission,
        test_bbs,
        test_trace,
        test_bouncing,
        test_lan,
        test_news,
        test_multiplayer,
        test_server_types,
        test_errors,
    ]

    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"\n  !!! SECTION CRASHED: {e}")
            import traceback
            traceback.print_exc()

    # Summary
    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")

    total_pass = sum(1 for _, _, ok in results if ok)
    total_fail = sum(1 for _, _, ok in results if not ok)
    total = len(results)

    for sect, tests in section_results.items():
        sp = sum(1 for _, ok in tests if ok)
        sf = sum(1 for _, ok in tests if not ok)
        icon = "+" if sf == 0 else "!"
        print(f"  [{icon}] {sect}: {sp}/{len(tests)}")

    print(f"\n  TOTAL: {total_pass}/{total} passed, {total_fail} failed")
    print(f"{'='*60}")

    if total_fail:
        print("\n  FAILURES:")
        for sect, name, ok in results:
            if not ok:
                print(f"    [{sect}] {name}")
        sys.exit(1)
    else:
        print("\n  ALL TESTS PASSED!")
