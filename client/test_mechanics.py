#!/usr/bin/env python3
"""
Test: LAN hacking, getting caught (trace), gateway/hardware upgrades
"""
import socket, json, time, sys

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
                    if want and j.get('type') == want: return j
                    if not want and j.get('type') == 'response': return j
                except: pass
        except: pass
        return None

    def join(self):
        self.cmd({'cmd':'join','handle':self.name,'password':'x'})
        self.cmd({'cmd':'dialog_ok'})
        # Complete test mission for money
        self.cmd({'cmd':'connect','ip':'128.185.0.4'})
        self.cmd({'cmd':'navigate','screen':4})
        self.cmd({'cmd':'copy_file','title':'Uplink test data'})
        self.cmd({'cmd':'delete_logs'})
        self.cmd({'cmd':'disconnect'})
        self.cmd({'cmd':'send_mail','to':'internal@Uplink.net','subject':'Mission completed',
            'body':'I have completed the following mission:\nUplink Test Mission -\nSteal data from a file server',
            'attach':'Uplink test data'})
        time.sleep(0.5)
        self.cmd({'cmd':'check_mission'})

    def close(self):
        self.sock.close()

def log(bot, msg):
    print(f'  [{bot.name}] {msg}')

results = []
def check(name, passed):
    results.append((name, passed))
    print(f'  {"PASS" if passed else "FAIL"}: {name}')

print('=' * 60)
print('  MECHANICS TESTS')
print('=' * 60)

# ================================================================
print('\n--- TEST A: Gateway Info ---')
# ================================================================
a = Bot('GatewayBot')
a.join()

m = a.cmd({'cmd':'gateway_info'}, 'gateway_info')
if m:
    log(a, f'Model: {m.get("model","?")}')
    log(a, f'Modem speed: {m.get("modemspeed")}')
    log(a, f'Memory: {m.get("memorysize")}')
    log(a, f'Bandwidth: {m.get("bandwidth")}')
    log(a, f'Hardware: {m.get("hardware",[])}')
    check('Gateway info works', m.get('modemspeed', 0) > 0)
else:
    check('Gateway info works', False)

# ================================================================
print('\n--- TEST B: Hardware List & Purchase ---')
# ================================================================
m = a.cmd({'cmd':'hardware_list'}, 'hardware_list')
if m:
    hw = m.get('hardware', [])
    log(a, f'Available hardware: {len(hw)} items')
    for h in hw[:8]:
        log(a, f'  {h["title"]} (${h["cost"]})')
    check('Hardware list works', len(hw) > 0)

    # Check balance
    bal = a.cmd({'cmd':'balance'}, 'balance')
    balance_before = bal['balance'] if bal else 0
    log(a, f'Balance: {balance_before}c')

    # Buy cheapest affordable hardware
    bought = False
    for h in sorted(hw, key=lambda x: x['cost']):
        if h['cost'] <= balance_before and h['cost'] > 0:
            log(a, f'Buying {h["title"]} for ${h["cost"]}...')
            r = a.cmd({'cmd':'buy_hardware','title':h['title']})
            log(a, f'Result: {r}')
            if r and r.get('status') == 'ok':
                bought = True
                bal2 = a.cmd({'cmd':'balance'}, 'balance')
                log(a, f'Balance: {balance_before}c → {bal2["balance"]}c')
                # Verify it shows in gateway
                gw = a.cmd({'cmd':'gateway_info'}, 'gateway_info')
                if gw:
                    log(a, f'Hardware now: {gw.get("hardware",[])}')
                    check('Hardware purchased', True)
                    check('Hardware in gateway', h['title'] in gw.get('hardware',[]))
                break
    if not bought:
        log(a, 'Could not afford any hardware')
        check('Hardware purchased', False)
        check('Hardware in gateway', False)
else:
    check('Hardware list works', False)
    check('Hardware purchased', False)
    check('Hardware in gateway', False)

a.close()

# ================================================================
print('\n--- TEST C: Trace / Getting Caught ---')
# ================================================================
c = Bot('TraceBot')
c.join()

# Search for a corporate server (has tracing enabled)
log(c, 'Searching for corporate servers...')
m = c.cmd({'cmd':'search','query':'Internal Services'}, 'search')
corp_ip = None
if m:
    for r in m.get('results', []):
        if 'Internal Services' in r['name'] and 'Uplink' not in r['name']:
            corp_ip = r['ip']
            log(c, f'Found: {r["ip"]} - {r["name"]}')
            break

if corp_ip:
    # Find a bounce server
    bounces = []
    m2 = c.cmd({'cmd':'search','query':'Public Access'}, 'search')
    if m2:
        for r in m2.get('results', [])[:3]:
            if r['ip'] != corp_ip:
                bounces.append(r['ip'])

    if bounces:
        log(c, f'Connecting via {len(bounces)} bounces to {corp_ip}...')
        r = c.cmd({'cmd':'connect_bounce','target':corp_ip,'bounces':bounces})
        log(c, f'Connect: {r}')

        # Force begin trace (normally triggered by disabling security)
        r = c.cmd({'cmd':'begin_trace'})
        log(c, f'Begin trace: {r}')

        m = c.cmd({'cmd':'trace'}, 'trace')
        if m:
            log(c, f'Trace: active={m["active"]}, progress={m["progress"]}/{m["total"]}')

        # Speed up to let trace progress
        log(c, 'Speeding up time...')
        c.cmd({'cmd':'speed','value':2})
        time.sleep(10)
        c.cmd({'cmd':'speed','value':1})

        m2 = c.cmd({'cmd':'trace'}, 'trace')
        if m2:
            log(c, f'Trace after wait: active={m2["active"]}, progress={m2["progress"]}/{m2["total"]}')
            check('Trace progresses on corporate server', m2['progress'] > 0 or m2['active'])
        else:
            check('Trace progresses on corporate server', False)
    else:
        log(c, 'No bounce servers found')
        check('Trace progresses on corporate server', False)
else:
    log(c, 'No corporate server found')
    check('Trace progresses on corporate server', False)

c.cmd({'cmd':'disconnect'})
c.close()

# ================================================================
print('\n--- TEST D: InterNIC Search ---')
# ================================================================
d = Bot('LANBot')
d.join()

# Test search
# Search for any server with "Government" (they have LANs)
m = d.cmd({'cmd':'search','query':'Government'}, 'search')
if m:
    results = m.get('results', [])
    log(d, f'Search "Government": {len(results)} results')
    for res in results[:5]:
        log(d, f'  {res["ip"]} - {res["name"]} (type={res["type"]})')
    check('InterNIC search works', len(results) > 0)
else:
    check('InterNIC search works', False)
    results = []

# Find LAN from the Government search results (OID_LANCOMPUTER = 15)
lan_ip = None
for res in results:
    if res['type'] == 15:  # OID_LANCOMPUTER
        lan_ip = res['ip']
        log(d, f'Found LAN: {res["ip"]} - {res["name"]}')
        break
if not lan_ip:
    # Try broader search
    m2 = d.cmd({'cmd':'search','query':'Network'}, 'search')
    if m2:
        for res in m2.get('results', []):
            if res['type'] == 15:
                lan_ip = res['ip']
                log(d, f'Found LAN: {res["ip"]} - {res["name"]}')
                break

# ================================================================
print('\n--- TEST E: LAN Scanning ---')
# ================================================================

if lan_ip:
    log(d, f'Connecting to LAN at {lan_ip}...')
    d.cmd({'cmd':'connect','ip':lan_ip})

    m = d.cmd({'cmd':'lan_scan'}, 'lan_scan')
    if m:
        systems = m.get('systems', [])
        links = m.get('links', [])
        log(d, f'LAN: {len(systems)} systems, {len(links)} links')
        for sys in systems[:10]:
            log(d, f'  [{sys["index"]}] {sys["typeName"]} sec={sys["security"]} vis={sys["visible"]}')
        for lnk in links[:5]:
            log(d, f'  Link: {lnk["from"]} → {lnk["to"]} sec={lnk["security"]}')
        check('LAN scan works', len(systems) > 0)
        check('LAN has multiple systems', len(systems) >= 3)
        check('LAN has links between systems', len(links) >= 2)
    else:
        r = d.cmd({'cmd':'lan_scan'})
        log(d, f'LAN scan response: {r}')
        check('LAN scan works', False)
        check('LAN has multiple systems', False)
        check('LAN has links between systems', False)
    d.cmd({'cmd':'disconnect'})
else:
    # Test rejection on non-LAN
    log(d, 'No LAN found, testing rejection...')
    d.cmd({'cmd':'connect','ip':'128.185.0.4'})
    r = d.cmd({'cmd':'lan_scan'})
    check('LAN scan rejects non-LAN', r and r.get('status') == 'error')
    check('LAN scan works', False)
    check('LAN has multiple systems', False)
    check('LAN has links between systems', False)
    d.cmd({'cmd':'disconnect'})

d.close()

# ================================================================
# Summary
# ================================================================
print('\n' + '=' * 60)
passed = sum(1 for n, p in results if p)
total = len(results)
for n, p in results:
    if not p:
        print(f'  FAIL: {n}')
print(f'\n  {passed}/{total} passed')
print('=' * 60)
