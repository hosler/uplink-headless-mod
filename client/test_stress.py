#!/usr/bin/env python3
"""
Uplink Stress Test — Comprehensive bot that exercises all game actions.
"""

import socket
import json
import time
import sys
import traceback


class Bot:
    def __init__(self, name, host="127.0.0.1", port=9090):
        self.name = name
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
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

    def cmd_response(self, cmd, timeout=2.0):
        """Send command and wait for response."""
        self.send(cmd)
        time.sleep(0.5)
        for m in self.read_msgs(timeout):
            if m.get("type") == "response":
                return m
        return None

    def get_state(self):
        self.send({"cmd": "state"})
        time.sleep(0.5)
        for m in self.read_msgs():
            if m.get("type") == "state":
                return m
        return None

    def get_typed(self, msg_type):
        """Read messages and return first of given type."""
        time.sleep(0.5)
        for m in self.read_msgs():
            if m.get("type") == msg_type:
                return m
        return None

    def close(self):
        self.sock.close()


def log(bot, msg):
    print(f"[{bot.name}] {msg}")


def test_join(bot, password="test"):
    r = bot.cmd_response({"cmd": "join", "handle": bot.name, "password": password})
    assert r and r["status"] == "ok", f"Join failed: {r}"
    log(bot, f"Joined: {r['detail']}")
    return True


def test_state(bot, label=""):
    st = bot.get_state()
    assert st, "No state received"
    scr = st.get("screen", {})
    p = st.get("player", {})
    log(bot, f"{label} Screen={scr.get('type','?')}: {scr.get('maintitle','')} "
             f"Player={p.get('handle','?')} @ {p.get('remotehost','?')} "
             f"connected={p.get('connected')}")
    return st


def test_dialog_ok(bot):
    r = bot.cmd_response({"cmd": "dialog_ok"})
    if r:
        log(bot, f"dialog_ok: {r['status']}: {r.get('detail','')}")
    return r


def test_connect(bot, ip):
    r = bot.cmd_response({"cmd": "connect", "ip": ip})
    if r:
        log(bot, f"connect {ip}: {r['status']}: {r.get('detail','')}")
    return r


def test_disconnect(bot):
    r = bot.cmd_response({"cmd": "disconnect"})
    if r:
        log(bot, f"disconnect: {r['status']}")
    return r


def test_menu(bot, option):
    r = bot.cmd_response({"cmd": "menu", "option": option})
    if r:
        log(bot, f"menu[{option}]: {r['status']}: {r.get('detail','')}")
    return r


def test_password(bot, pw):
    r = bot.cmd_response({"cmd": "password", "value": pw})
    if r:
        log(bot, f"password: {r['status']}: {r.get('detail','')}")
    return r


def test_navigate(bot, screen):
    r = bot.cmd_response({"cmd": "navigate", "screen": screen})
    if r:
        log(bot, f"navigate[{screen}]: {r['status']}")
    return r


def test_speed(bot, speed):
    r = bot.cmd_response({"cmd": "speed", "value": speed})
    if r:
        log(bot, f"speed={speed}: {r['status']}")
    return r


def test_links(bot):
    bot.send({"cmd": "links"})
    m = bot.get_typed("links")
    if m:
        links = m.get("links", [])
        log(bot, f"links ({len(links)}):")
        for lk in links[:10]:
            log(bot, f"  {lk['ip']} - {lk['name']}")
        return links
    return []


def test_missions(bot):
    bot.send({"cmd": "missions"})
    m = bot.get_typed("missions")
    if m:
        missions = m.get("missions", [])
        log(bot, f"missions ({len(missions)}):")
        for mi in missions[:5]:
            log(bot, f"  {mi['description']} (${mi['payment']})")
        return missions
    return []


def test_set_field(bot, button, value):
    r = bot.cmd_response({"cmd": "set_field", "button": button, "value": value})
    if r:
        log(bot, f"set_field [{button}]={value}: {r['status']}")
    return r


def run_all_tests():
    print("=" * 60)
    print("  UPLINK HEADLESS API — STRESS TEST")
    print("=" * 60)

    passed = 0
    failed = 0
    errors = []

    def check(name, func):
        nonlocal passed, failed
        try:
            func()
            print(f"  PASS: {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {name} — {e}")
            errors.append((name, str(e)))
            failed += 1

    # Create bots
    alice = Bot("Alice")
    bob = Bot("Bob")

    # === TEST SUITE ===

    check("Alice joins", lambda: test_join(alice, "alice123"))
    check("Bob joins", lambda: test_join(bob, "bob456"))

    check("Alice initial state", lambda: test_state(alice, "initial"))
    check("Bob initial state", lambda: test_state(bob, "initial"))

    # Click through gateway dialogs
    check("Alice dialog_ok", lambda: test_dialog_ok(alice))
    check("Bob dialog_ok", lambda: test_dialog_ok(bob))

    # Check links
    check("Alice links", lambda: test_links(alice))
    check("Bob links", lambda: test_links(bob))

    # Check missions
    check("Alice missions", lambda: test_missions(alice))
    check("Bob missions", lambda: test_missions(bob))

    # Alice connects to InterNIC
    check("Alice connect InterNIC", lambda: test_connect(alice, "458.615.48.651"))
    def check_alice_internic():
        st = test_state(alice, "at InterNIC")
        assert st["player"]["remotehost"] == "458.615.48.651", f"Expected InterNIC, got {st['player']['remotehost']}"
    check("Alice at InterNIC", check_alice_internic)

    check("Bob still at gateway", lambda: test_state(bob, "at gateway"))

    # Alice disconnects
    check("Alice disconnect", lambda: test_disconnect(alice))
    check("Alice after disconnect", lambda: test_state(alice, "after disconnect"))

    # Speed control
    check("Alice speed=2", lambda: test_speed(alice, 2))
    check("Alice speed=1", lambda: test_speed(alice, 1))

    # Navigate by screen index
    check("Alice navigate screen 0", lambda: test_navigate(alice, 0))
    check("Alice state after navigate", lambda: test_state(alice, "after navigate"))

    # Connect to Uplink Public Access Server
    check("Bob connect Uplink PAS", lambda: test_connect(bob, "234.773.0.666"))
    check("Bob at Uplink PAS", lambda: test_state(bob, "at Uplink PAS"))

    # Bob disconnects
    check("Bob disconnect", lambda: test_disconnect(bob))

    # Both reconnect to same server — shared world
    check("Alice connect Uplink PAS", lambda: test_connect(alice, "234.773.0.666"))
    check("Bob connect Uplink PAS", lambda: test_connect(bob, "234.773.0.666"))
    check("Alice at Uplink PAS", lambda: test_state(alice, "shared server"))
    check("Bob at Uplink PAS", lambda: test_state(bob, "shared server"))

    # Final states
    check("Alice final state", lambda: test_state(alice, "FINAL"))
    check("Bob final state", lambda: test_state(bob, "FINAL"))

    alice.close()
    bob.close()

    # Summary
    print("\n" + "=" * 60)
    print(f"  RESULTS: {passed} passed, {failed} failed")
    if errors:
        print(f"\n  FAILURES:")
        for name, err in errors:
            print(f"    {name}: {err}")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
