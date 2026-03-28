#!/usr/bin/env python3
"""
Uplink Multiplayer Test — Two bots playing the same world.
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
        self.sock.settimeout(3)
        self.buf = ""
        print(f"[{name}] Connected")

    def send(self, cmd):
        self.sock.sendall((json.dumps(cmd) + "\n").encode())

    def read_msgs(self):
        msgs = []
        try:
            data = self.sock.recv(65536).decode("utf-8", errors="replace")
            self.buf += data
        except socket.timeout:
            pass
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

    def get_state(self):
        self.send({"cmd": "state"})
        time.sleep(0.5)
        for m in self.read_msgs():
            if m.get("type") == "state":
                return m
        return None

    def get_response(self):
        time.sleep(0.3)
        for m in self.read_msgs():
            if m.get("type") == "response":
                return m
        return None

    def join(self, password="test"):
        self.send({"cmd": "join", "handle": self.name, "password": password})
        r = self.get_response()
        if r:
            print(f"[{self.name}] Join: {r['status']}: {r.get('detail', '')}")
        return r

    def show_state(self, label=""):
        st = self.get_state()
        if not st:
            print(f"[{self.name}] {label} (no state)")
            return None
        scr = st.get("screen", {})
        p = st.get("player", {})
        print(f"[{self.name}] {label}")
        print(f"  Screen: {scr.get('type', '?')}: {scr.get('maintitle', '')}")
        print(f"  Player: {p.get('handle', '?')} @ {p.get('remotehost', '?')} connected={p.get('connected')}")
        print(f"  Date: {st.get('date', '?')}")
        return st

    def close(self):
        self.sock.close()


def main():
    print("=== Uplink Multiplayer Test ===\n")

    # Create two bots
    alice = Bot("Alice")
    bob = Bot("Bob")

    # Both join
    print("\n--- Step 1: Both bots join ---")
    alice.join("alice123")
    time.sleep(1)
    bob.join("bob456")
    time.sleep(1)

    # Both check their state
    print("\n--- Step 2: Check initial state ---")
    alice.show_state("Alice's state")
    bob.show_state("Bob's state")

    # Alice clicks through her gateway dialog
    print("\n--- Step 3: Alice clicks dialog OK ---")
    alice.send({"cmd": "dialog_ok"})
    r = alice.get_response()
    if r:
        print(f"[Alice] dialog_ok: {r['status']}: {r.get('detail', '')}")

    # Bob clicks through his gateway dialog
    print("\n--- Step 4: Bob clicks dialog OK ---")
    bob.send({"cmd": "dialog_ok"})
    r = bob.get_response()
    if r:
        print(f"[Bob] dialog_ok: {r['status']}: {r.get('detail', '')}")

    # Check states again — should be independent
    print("\n--- Step 5: Check states after dialog ---")
    alice.show_state("Alice after dialog")
    bob.show_state("Bob after dialog")

    # Alice connects to InterNIC
    print("\n--- Step 6: Alice connects to InterNIC ---")
    alice.send({"cmd": "connect", "ip": "458.615.48.651"})
    r = alice.get_response()
    if r:
        print(f"[Alice] connect: {r['status']}: {r.get('detail', '')}")

    # Bob stays at gateway — check both
    print("\n--- Step 7: Verify independence ---")
    alice.show_state("Alice (should be at InterNIC)")
    bob.show_state("Bob (should still be at gateway)")

    # Both check links
    print("\n--- Step 8: Check links ---")
    alice.send({"cmd": "links"})
    time.sleep(0.5)
    for m in alice.read_msgs():
        if m.get("type") == "links":
            print(f"[Alice] {len(m['links'])} links:")
            for lk in m["links"][:5]:
                print(f"  {lk['ip']} - {lk['name']}")

    bob.send({"cmd": "links"})
    time.sleep(0.5)
    for m in bob.read_msgs():
        if m.get("type") == "links":
            print(f"[Bob] {len(m['links'])} links:")
            for lk in m["links"][:5]:
                print(f"  {lk['ip']} - {lk['name']}")

    print("\n--- Done! ---")
    alice.close()
    bob.close()


if __name__ == "__main__":
    main()
