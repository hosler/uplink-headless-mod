#!/usr/bin/env python3
"""
Uplink Mission Test — Two bots independently complete the test mission.

Mission: Steal "Uplink test data" from Test Machine (128.185.0.4)
Steps: connect → enter password "rosebud" → navigate to file server →
       copy file → delete logs → disconnect → email file to contact
"""

import socket
import json
import time
import sys


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

    def cmd(self, command, timeout=2.0):
        """Send command, return response."""
        self.send(command)
        time.sleep(0.5)
        for m in self.read_msgs(timeout):
            if m.get("type") == "response":
                return m
        return None

    def query(self, command, msg_type, timeout=2.0):
        """Send command, return first message of given type."""
        self.send(command)
        time.sleep(0.5)
        for m in self.read_msgs(timeout):
            if m.get("type") == msg_type:
                return m
        return None

    def state(self):
        return self.query({"cmd": "state"}, "state")

    def close(self):
        self.sock.close()


def log(bot, msg):
    print(f"[{bot.name}] {msg}")


def run_mission(bot):
    """Have a bot complete the full test mission."""
    log(bot, "=== Starting Test Mission ===")

    # 1. Check missions
    m = bot.query({"cmd": "missions"}, "missions")
    if m:
        missions = m.get("missions", [])
        log(bot, f"Active missions: {len(missions)}")
        for mi in missions:
            log(bot, f"  {mi['description']} (${mi['payment']})")
    else:
        log(bot, "WARNING: Could not get missions")

    # 2. Click through gateway dialog first
    st = bot.state()
    if st and st.get("screen", {}).get("type") == "DialogScreen":
        log(bot, "Clicking through gateway dialog...")
        bot.cmd({"cmd": "dialog_ok"})
        time.sleep(0.5)

    # 3. Connect to Uplink Test Machine
    log(bot, "Connecting to Test Machine (128.185.0.4)...")
    r = bot.cmd({"cmd": "connect", "ip": "128.185.0.4"})
    if r:
        log(bot, f"  Connect: {r['status']}: {r.get('detail','')}")
        if r["status"] != "ok":
            log(bot, "FAILED to connect!")
            return False

    # 4. Check current screen
    st = bot.state()
    if st:
        scr = st.get("screen", {})
        log(bot, f"  Screen: {scr.get('type')}: {scr.get('maintitle','')}")

    # 5. Submit password "rosebud"
    log(bot, "Submitting password 'rosebud'...")
    r = bot.cmd({"cmd": "password", "value": "rosebud"})
    if r:
        log(bot, f"  Password: {r['status']}: {r.get('detail','')}")

    # 6. Check screen — should be on menu now
    time.sleep(1)
    st = bot.state()
    if st:
        scr = st.get("screen", {})
        log(bot, f"  Screen: {scr.get('type')}: {scr.get('maintitle','')}")
        if scr.get("options"):
            for i, opt in enumerate(scr["options"]):
                log(bot, f"    [{i}] {opt['caption']}")

    # 7. Navigate to file server (option index for "Access fileserver")
    log(bot, "Selecting file server from menu...")
    # Try menu option 0 first (usually "Access fileserver")
    st = bot.state()
    scr = st.get("screen", {}) if st else {}
    if scr.get("type") == "MenuScreen":
        # Find the file server option
        for i, opt in enumerate(scr.get("options", [])):
            if "file" in opt["caption"].lower():
                log(bot, f"  Found file server at option {i}: {opt['caption']}")
                r = bot.cmd({"cmd": "menu", "option": i})
                if r:
                    log(bot, f"  Menu: {r['status']}: {r.get('detail','')}")
                break
    else:
        # Try navigating directly to screen 4 (file server)
        log(bot, "  Not on menu, navigating to screen 4...")
        bot.cmd({"cmd": "navigate", "screen": 4})

    # 8. List files on remote server
    time.sleep(0.5)
    m = bot.query({"cmd": "files"}, "files")
    if m:
        log(bot, f"Files on {m.get('computer','')}:")
        for f in m.get("files", []):
            log(bot, f"  [{f['index']}] {f['title']} (size={f['size']}, enc={f['encrypted']})")
    else:
        log(bot, "WARNING: Could not list files")

    # 9. Copy "Uplink test data" to gateway
    log(bot, "Copying 'Uplink test data' to gateway...")
    r = bot.cmd({"cmd": "copy_file", "title": "Uplink test data"})
    if r:
        log(bot, f"  Copy: {r['status']}: {r.get('detail','')}")

    # 10. Verify file on gateway
    m = bot.query({"cmd": "gateway_files"}, "gateway_files")
    if m:
        log(bot, f"Gateway files:")
        for f in m.get("files", []):
            log(bot, f"  [{f['index']}] {f['title']} (size={f['size']})")
    else:
        log(bot, "WARNING: Could not list gateway files")

    # 11. Check and delete logs
    m = bot.query({"cmd": "logs"}, "logs")
    if m:
        logs = m.get("logs", [])
        log(bot, f"Access logs: {len(logs)}")
        for l in logs[:5]:
            log(bot, f"  {l['date']} - {l['from_name']}: {l.get('data1','')}")

    log(bot, "Deleting all logs...")
    r = bot.cmd({"cmd": "delete_logs"})
    if r:
        log(bot, f"  Delete: {r['status']}: {r.get('detail','')}")

    # 12. Disconnect from test machine
    log(bot, "Disconnecting...")
    bot.cmd({"cmd": "disconnect"})

    # 13. Send mission completion email with file attachment
    log(bot, "Sending mission completion email...")
    r = bot.cmd({"cmd": "send_mail",
                  "to": "internal@Uplink.net",
                  "subject": "Mission completed",
                  "body": "I have completed the following mission:\nUplink Test Mission -\nSteal data from a file server",
                  "attach": "Uplink test data"})
    if r:
        log(bot, f"  Email: {r['status']}: {r.get('detail','')}")

    # 14. Force mission completion check
    log(bot, "Checking mission completion...")
    time.sleep(1)
    r = bot.cmd({"cmd": "check_mission"})
    if r:
        log(bot, f"  Check: {r['status']}: {r.get('detail','')}")

    # 15. Verify missions
    m = bot.query({"cmd": "missions"}, "missions")
    if m:
        missions = m.get("missions", [])
        log(bot, f"Missions remaining: {len(missions)}")
        if len(missions) == 0:
            log(bot, "*** MISSION COMPLETE! ***")
            return True
        else:
            for mi in missions:
                log(bot, f"  Still active: {mi['description']}")
            return False

    log(bot, "Could not verify mission status")
    return False


def main():
    print("=" * 60)
    print("  UPLINK TEST MISSION — MULTIPLAYER BOT TEST")
    print("=" * 60)

    alice = Bot("Alice")
    bob = Bot("Bob")

    # Join
    print("\n--- Joining ---")
    r = alice.cmd({"cmd": "join", "handle": "Alice", "password": "a"})
    log(alice, f"Joined: {r['status'] if r else 'no response'}: {r.get('detail','') if r else ''}")

    r = bob.cmd({"cmd": "join", "handle": "Bob", "password": "b"})
    log(bob, f"Joined: {r['status'] if r else 'no response'}: {r.get('detail','') if r else ''}")

    # Alice runs the mission
    print("\n" + "=" * 40)
    print("  ALICE'S MISSION RUN")
    print("=" * 40)
    alice_success = run_mission(alice)

    # Bob runs the same mission independently
    print("\n" + "=" * 40)
    print("  BOB'S MISSION RUN")
    print("=" * 40)
    bob_success = run_mission(bob)

    # Final check
    print("\n" + "=" * 60)
    print(f"  RESULTS:")
    print(f"    Alice: {'COMPLETED' if alice_success else 'FAILED'}")
    print(f"    Bob:   {'COMPLETED' if bob_success else 'FAILED'}")
    print("=" * 60)

    alice.close()
    bob.close()


if __name__ == "__main__":
    main()
