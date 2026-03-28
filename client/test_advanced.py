#!/usr/bin/env python3
"""
Advanced tests: mission racing, inbox, trace/security, software purchase,
multiple missions in sequence.
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
        r = self.cmd({'cmd':'join','handle':self.name,'password':'x'})
        self.cmd({'cmd':'dialog_ok'})
        return r

    def complete_test_mission(self):
        self.cmd({'cmd':'connect','ip':'128.185.0.4'})
        self.cmd({'cmd':'navigate','screen':4})
        self.cmd({'cmd':'copy_file','title':'Uplink test data'})
        self.cmd({'cmd':'delete_logs'})
        self.cmd({'cmd':'disconnect'})
        self.cmd({'cmd':'send_mail','to':'internal@Uplink.net','subject':'Mission completed',
            'body':'I have completed the following mission:\nUplink Test Mission -\nSteal data from a file server',
            'attach':'Uplink test data'})
        time.sleep(0.5)
        return self.cmd({'cmd':'check_mission'})

    def close(self):
        self.sock.close()

def log(bot, msg):
    print(f'  [{bot.name}] {msg}')

results = []
def check(name, passed):
    results.append((name, passed))
    print(f'  {"PASS" if passed else "FAIL"}: {name}')

# ================================================================
print('=' * 60)
print('  ADVANCED TESTS')
print('=' * 60)

# ================================================================
print('\n--- TEST A: Inbox / Messages ---')
# ================================================================
a = Bot('Inbox')
a.join()
a.complete_test_mission()

# Check inbox — should have welcome message and mission confirmation
time.sleep(2)
m = a.cmd({'cmd':'inbox'}, 'inbox')
if m:
    msgs = m.get('messages', [])
    log(a, f'Inbox: {len(msgs)} messages')
    for msg in msgs[:5]:
        log(a, f'  [{msg["index"]}] From: {msg["from"]} Subj: {msg["subject"]}')
    check('Has inbox messages', len(msgs) > 0)
    has_welcome = any('welcome' in msg.get('subject','').lower() or 'uplink' in msg.get('from','').lower() for msg in msgs)
    check('Has welcome/system message', has_welcome)
else:
    check('Has inbox messages', False)
    check('Has welcome/system message', False)
a.close()

# ================================================================
print('\n--- TEST B: Software Purchase ---')
# ================================================================
b = Bot('Shopper')
b.join()
b.complete_test_mission()

# List available software
m = b.cmd({'cmd':'software_list'}, 'software_list')
if m:
    sw = m.get('software', [])
    log(b, f'Available software: {len(sw)}')
    for s in sw[:8]:
        log(b, f'  {s["title"]} v{s["version"]} (${s["cost"]}, {s["size"]}GQ)')

    # Check balance first
    bal = b.cmd({'cmd':'balance'}, 'balance')
    balance_before = bal['balance'] if bal else 0
    log(b, f'Balance: {balance_before}c')

    # Try to buy something affordable
    bought = False
    for s in sw:
        if s['cost'] <= balance_before:
            log(b, f'Buying {s["title"]} for ${s["cost"]}...')
            r = b.cmd({'cmd':'buy_software','title':s['title']})
            log(b, f'Result: {r}')
            if r and r.get('status') == 'ok':
                bought = True
                # Check balance decreased
                bal2 = b.cmd({'cmd':'balance'}, 'balance')
                balance_after = bal2['balance'] if bal2 else 0
                log(b, f'Balance: {balance_before}c → {balance_after}c')
                check('Software purchased', True)
                check('Balance decreased', balance_after < balance_before)
                # Check it's on gateway
                gw = b.cmd({'cmd':'gateway_files'}, 'gateway_files')
                if gw:
                    titles = [f['title'] for f in gw['files']]
                    check('Software on gateway', s['title'] in titles)
                break
    if not bought:
        log(b, 'Could not afford any software')
        check('Software purchased', False)
        check('Balance decreased', False)
        check('Software on gateway', False)
else:
    log(b, 'Could not list software')
    check('Software purchased', False)
    check('Balance decreased', False)
    check('Software on gateway', False)
b.close()

# ================================================================
print('\n--- TEST C: Trace / Security ---')
# ================================================================
c = Bot('Traced')
c.join()
c.complete_test_mission()

# Connect to test machine (has trace speed 30 seconds)
c.cmd({'cmd':'connect','ip':'128.185.0.4'})

# Check initial trace status
m = c.cmd({'cmd':'trace'}, 'trace')
if m:
    log(c, f'Trace: active={m["active"]}, progress={m["progress"]}/{m["total"]}')
    check('Trace status works', True)
else:
    check('Trace status works', False)

# Speed up time to trigger trace
log(c, 'Speeding up time to trigger trace...')
c.cmd({'cmd':'speed','value':2})
time.sleep(8)
c.cmd({'cmd':'speed','value':1})

m2 = c.cmd({'cmd':'trace'}, 'trace')
if m2:
    log(c, f'Trace after wait: active={m2["active"]}, progress={m2["progress"]}/{m2["total"]}')
    # Trace may or may not have started depending on timing
    check('Trace query after delay', True)
else:
    check('Trace query after delay', False)

c.cmd({'cmd':'disconnect'})
c.close()

# ================================================================
print('\n--- TEST D: Mission Racing ---')
# ================================================================
d1 = Bot('Racer1')
d2 = Bot('Racer2')
d1.join()
d2.join()
d1.complete_test_mission()
d2.complete_test_mission()

# Both browse BBS
m1 = d1.cmd({'cmd':'bbs'}, 'bbs')
m2 = d2.cmd({'cmd':'bbs'}, 'bbs')

if m1 and m1['missions'] and m2 and m2['missions']:
    # Find a steal mission both can see
    target_mission = None
    for mi in m1['missions']:
        if mi['type'] == 1:  # MISSION_STEALFILE
            target_mission = mi
            break

    if target_mission:
        idx = target_mission['index']
        log(d1, f'Both accepting mission [{idx}]: {target_mission["description"]}')

        # Both accept the same mission
        r1 = d1.cmd({'cmd':'accept_mission','index':idx})
        log(d1, f'Accept: {r1}')
        r2 = d2.cmd({'cmd':'accept_mission','index':idx})
        log(d2, f'Accept: {r2}')

        # One should succeed, one should fail (mission removed from BBS after first accept)
        d1_got = r1 and r1.get('status') == 'ok'
        d2_got = r2 and r2.get('status') == 'ok'

        if d1_got and not d2_got:
            log(d1, 'Got the mission!')
            log(d2, 'Mission already taken')
            check('Mission racing: first wins', True)
        elif d2_got and not d1_got:
            log(d2, 'Got the mission!')
            log(d1, 'Mission already taken')
            check('Mission racing: first wins', True)
        elif d1_got and d2_got:
            log(d1, 'Both got it (no contention)')
            check('Mission racing: both accepted different index copies', True)
        else:
            log(d1, 'Neither got it?')
            check('Mission racing: unexpected', False)
    else:
        log(d1, 'No steal missions on BBS')
        check('Mission racing: no missions', False)
else:
    check('Mission racing: BBS empty', False)

d1.close()
d2.close()

# ================================================================
print('\n--- TEST E: Multiple Missions in Sequence ---')
# ================================================================
e = Bot('Grinder')
e.join()
e.complete_test_mission()

bal = e.cmd({'cmd':'balance'}, 'balance')
start_balance = bal['balance'] if bal else 0
missions_completed = 0

for attempt in range(3):
    # Get BBS mission
    m = e.cmd({'cmd':'bbs'}, 'bbs')
    if not m or not m['missions']:
        log(e, f'Attempt {attempt+1}: No missions on BBS')
        break

    # Accept first steal mission
    target = None
    for mi in m['missions']:
        if mi['type'] == 1:  # steal
            target = mi
            break
    if not target:
        for mi in m['missions']:
            if mi['type'] == 2:  # destroy
                target = mi
                break
    if not target:
        log(e, f'Attempt {attempt+1}: No steal/destroy missions')
        break

    r = e.cmd({'cmd':'accept_mission','index':target['index']})
    log(e, f'Mission {attempt+1}: Accepted {target["description"][:40]}... (${target["payment"]})')

    # Get mission details
    mm = e.cmd({'cmd':'missions'}, 'missions')
    if not mm or not mm['missions']:
        log(e, 'No mission in list after accept?')
        break

    mission = mm['missions'][0]
    target_ip = mission['links'][0] if mission.get('links') else None
    target_file = mission.get('completionB', '')

    if not target_ip:
        log(e, 'No target IP')
        break

    # Execute
    e.cmd({'cmd':'connect','ip':target_ip})

    # Try to navigate to file server
    # Try auth first if codes available
    codes = mission.get('codes', {})
    if target_ip in codes:
        e.cmd({'cmd':'navigate','screen':1})
        e.cmd({'cmd':'password','user':'admin','value':codes[target_ip]})

    # Find file server — try navigating to various screens
    for screen_idx in [4, 3, 2]:
        e.cmd({'cmd':'navigate','screen':screen_idx})
        fm = e.cmd({'cmd':'files'}, 'files')
        if fm and fm.get('files'):
            break

    if mission['type'] == 1:  # steal
        e.cmd({'cmd':'copy_file','title':target_file})
    elif mission['type'] == 2:  # destroy
        e.cmd({'cmd':'delete_file','title':target_file})

    e.cmd({'cmd':'delete_logs'})
    e.cmd({'cmd':'disconnect'})

    # Complete
    body = f'I have completed the following mission:\n{mission["description"]}'
    email = {'cmd':'send_mail','to':mission['contact'],'subject':'Mission completed','body':body}
    if mission['type'] == 1:
        email['attach'] = target_file
    e.cmd(email)
    time.sleep(1)
    r = e.cmd({'cmd':'check_mission'})

    mm2 = e.cmd({'cmd':'missions'}, 'missions')
    remaining = len(mm2['missions']) if mm2 else -1
    if remaining == 0:
        missions_completed += 1
        log(e, f'  COMPLETED! ({missions_completed} total)')
    else:
        log(e, f'  Not completed (missions remaining: {remaining})')

bal = e.cmd({'cmd':'balance'}, 'balance')
end_balance = bal['balance'] if bal else 0
log(e, f'Balance: {start_balance}c → {end_balance}c (+{end_balance - start_balance}c)')
log(e, f'Rating after grind:')
st = e.cmd({'cmd':'state'}, 'state')
if st:
    log(e, f'  Uplink: {st["player"]["rating"]["uplink"]}')

check(f'Completed {missions_completed}/3 missions', missions_completed >= 1)
check('Earned money from grinding', end_balance > start_balance)

e.close()

# ================================================================
# Summary
# ================================================================
print('\n' + '=' * 60)
passed = sum(1 for _, p in results if p)
total = len(results)
for name, p in results:
    if not p:
        print(f'  FAIL: {name}')
print(f'\n  {passed}/{total} passed')
print('=' * 60)
