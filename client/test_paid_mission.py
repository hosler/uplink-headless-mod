#!/usr/bin/env python3
"""
Test: Complete a real paid mission end-to-end.
Accept from BBS → find target → hack → complete → get paid
"""
import socket, json, time, sys

def bot(name):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('127.0.0.1', 9090))
    s.settimeout(5)
    return s

def cmd(s, c, want=None):
    s.sendall((json.dumps(c) + '\n').encode())
    time.sleep(0.5)
    try:
        data = s.recv(65536).decode()
        for l in data.strip().split('\n'):
            try:
                j = json.loads(l.strip())
                if want and j.get('type') == want: return j
                if not want and j.get('type') == 'response': return j
            except: pass
    except: pass
    return None

def log(msg):
    print(f'  {msg}')

print('=' * 60)
print('  REAL PAID MISSION — END TO END')
print('=' * 60)

s = bot('Hacker')
r = cmd(s, {'cmd':'join','handle':'Hacker','password':'h'})
log(f'Join: {r.get("detail")}')
cmd(s, {'cmd':'dialog_ok'})

# Complete test mission first to unlock better missions
log('Completing test mission...')
cmd(s, {'cmd':'connect','ip':'128.185.0.4'})
cmd(s, {'cmd':'navigate','screen':4})
cmd(s, {'cmd':'copy_file','title':'Uplink test data'})
cmd(s, {'cmd':'delete_logs'})
cmd(s, {'cmd':'disconnect'})
cmd(s, {'cmd':'send_mail','to':'internal@Uplink.net','subject':'Mission completed',
    'body':'I have completed the following mission:\nUplink Test Mission -\nSteal data from a file server',
    'attach':'Uplink test data'})
time.sleep(1)
cmd(s, {'cmd':'check_mission'})

# Check balance
m = cmd(s, {'cmd':'balance'}, 'balance')
balance_start = m['balance'] if m else 0
log(f'Balance after test mission: {balance_start}c')

# Browse BBS
print('\n--- BBS Missions ---')
m = cmd(s, {'cmd':'bbs'}, 'bbs')
if not m or not m.get('missions'):
    log('No missions available!')
    s.close()
    sys.exit(1)

for mi in m['missions'][:5]:
    log(f'[{mi["index"]}] {mi["description"]} (${mi["payment"]}) diff={mi["difficulty"]}')

# Accept first mission
mission_bbs = m['missions'][0]
log(f'\nAccepting: {mission_bbs["description"]} (${mission_bbs["payment"]})')
r = cmd(s, {'cmd':'accept_mission','index':mission_bbs['index']})
log(f'Accept: {r}')

# Get full mission details
print('\n--- Mission Details ---')
m = cmd(s, {'cmd':'missions'}, 'missions')
if not m or not m['missions']:
    log('No active mission!')
    s.close()
    sys.exit(1)

mission = m['missions'][0]
log(f'Type: {mission["type"]}')
log(f'Description: {mission["description"]}')
log(f'Contact: {mission["contact"]}')
log(f'Payment: ${mission["payment"]}')
log(f'CompletionA: {mission.get("completionA","")}')
log(f'CompletionB: {mission.get("completionB","")}')
log(f'Links: {mission.get("links",[])}')
log(f'Codes: {mission.get("codes",{})}')
if mission.get('fulldetails'):
    log(f'Details: {mission["fulldetails"][:200]}')

# Figure out what to do based on mission type
target_ip = mission['links'][0] if mission.get('links') else None
target_file = mission.get('completionB', '')
mission_type = mission['type']
contact = mission['contact']

if not target_ip:
    log('No target IP in mission links!')
    s.close()
    sys.exit(1)

log(f'\nTarget IP: {target_ip}')

# Connect to target
print('\n--- Executing Mission ---')
log(f'Connecting to {target_ip}...')
r = cmd(s, {'cmd':'connect','ip':target_ip})
log(f'Connect: {r}')

# Check what screen we're on
st = cmd(s, {'cmd':'state'}, 'state')
screen = st['screen']['type'] if st else '?'
log(f'Screen: {screen}')

# Try to authenticate — use codes from mission if available
codes = mission.get('codes', {})
if target_ip in codes:
    code = codes[target_ip]
    log(f'Have access code: {code}')
    # Navigate to password/userid screen
    if screen == 'MessageScreen':
        cmd(s, {'cmd':'navigate','screen':1})
        st = cmd(s, {'cmd':'state'}, 'state')
        screen = st['screen']['type'] if st else '?'
        log(f'Screen after navigate: {screen}')

    if screen in ('PasswordScreen', 'UserIDScreen'):
        r = cmd(s, {'cmd':'password','user':'admin','value':code})
        log(f'Auth: {r}')
        st = cmd(s, {'cmd':'state'}, 'state')
        screen = st['screen']['type'] if st else '?'
        log(f'Screen after auth: {screen}')
else:
    log('No access code provided, trying to navigate directly')

# Navigate to file server — try screens 2-10 looking for files
if screen == 'MenuScreen':
    opts = st['screen'].get('options', []) if st else []
    log(f'Menu options:')
    for i, o in enumerate(opts):
        log(f'  [{i}] {o["caption"]}')
    # Look for file server option
    for i, o in enumerate(opts):
        if 'file' in o['caption'].lower():
            log(f'Selecting file server option {i}')
            cmd(s, {'cmd':'menu','option':i})
            break
    else:
        # Just try first option
        if opts:
            log(f'Selecting first option')
            cmd(s, {'cmd':'menu','option':0})

# List files
print()
m = cmd(s, {'cmd':'files'}, 'files')
if m:
    log(f'Files on target ({m.get("computer","?")}):')
    for f in m.get('files', [])[:10]:
        log(f'  [{f["index"]}] {f["title"]} (size={f["size"]}, enc={f["encrypted"]})')

# Execute based on mission type
# Type 1 = MISSION_STEALFILE, Type 2 = MISSION_DESTROYFILE
if mission_type == 1:  # Steal
    log(f'\nSTEALING: {target_file}')
    r = cmd(s, {'cmd':'copy_file','title':target_file})
    log(f'Copy: {r}')
elif mission_type == 2:  # Destroy
    log(f'\nDESTROYING: {target_file}')
    r = cmd(s, {'cmd':'delete_file','title':target_file})
    log(f'Delete: {r}')
else:
    log(f'\nUnknown mission type {mission_type}, trying steal anyway')
    r = cmd(s, {'cmd':'copy_file','title':target_file})
    log(f'Copy: {r}')

# Delete logs
log('Deleting logs...')
r = cmd(s, {'cmd':'delete_logs'})
log(f'Logs: {r}')

# Disconnect
cmd(s, {'cmd':'disconnect'})

# Send completion email
print('\n--- Completing Mission ---')
body = f'I have completed the following mission:\n{mission["description"]}'
email_cmd = {
    'cmd': 'send_mail',
    'to': contact,
    'subject': 'Mission completed',
    'body': body
}
# Attach file if steal mission
if mission_type == 1 and target_file:
    email_cmd['attach'] = target_file
r = cmd(s, email_cmd)
log(f'Email: {r}')

# Check mission completion
time.sleep(1)
r = cmd(s, {'cmd':'check_mission'})
log(f'Check: {r}')

# Verify
m = cmd(s, {'cmd':'missions'}, 'missions')
remaining = len(m['missions']) if m else -1
log(f'Missions remaining: {remaining}')

m = cmd(s, {'cmd':'balance'}, 'balance')
balance_end = m['balance'] if m else 0
log(f'Balance: {balance_start}c → {balance_end}c ({"+" if balance_end > balance_start else ""}{balance_end - balance_start}c)')

st = cmd(s, {'cmd':'state'}, 'state')
if st:
    rating = st['player']['rating']['uplink']
    log(f'Uplink rating: {rating}')

s.close()

print('\n' + '=' * 60)
if remaining == 0 and balance_end > balance_start:
    print('  MISSION COMPLETE — GOT PAID!')
elif remaining == 0:
    print('  MISSION COMPLETE (no payment change detected)')
else:
    print('  MISSION NOT COMPLETED')
print('=' * 60)
