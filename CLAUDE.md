# Uplink RE — Headless Multiplayer Server + Pygame Client

## Current Goal

Build out the content tabs (Email, Gateway, Missions, BBS, Software, Hardware) in the pygame client. The browser tab and all server screen types are complete.

## Quick Start

### Server
```bash
export PATH="$HOME/uplink-re/src/bin:$PATH"
cd ~/uplink-re/src/uplink/src && rm -f uplink.full && make
cp uplink.full ~/uplink-re/game/uplink.bin.x86_64
rm -rf ~/.uplink/
export LD_LIBRARY_PATH="$HOME/uplink-re/src/contrib/FTGL-2.1.2/unix/src/.libs"
~/uplink-re/game/uplink.bin.x86_64 --headless --port 9090
```
~50s startup. Wait for port 9090.

### Client
```bash
source ~/uplink-re/client/.venv/bin/activate
python3 ~/uplink-re/client/uplink_client.py
```
Optional flags: `--no-music`, `--debug-log /tmp/debug.json`, `--light-theme`

### Auto-testing (skip login UI)
```bash
python3 ~/uplink-re/client/uplink_client.py --auto-join AgentName --auto-connect 128.185.0.4 --auto-crack
```
Finds ISM IP: use scout script or `--auto-connect IP_FROM_INTERNIC`

### Xvfb visual testing
```bash
source ~/uplink-re/client/.venv/bin/activate
python3 ~/uplink-re/client/test_ui.py       # 16/16 basic
python3 ~/uplink-re/client/test_ui_deep.py  # 7/7 server flows
```

### Build after changes
```bash
export PATH="$HOME/uplink-re/src/bin:$PATH"
cd ~/uplink-re/src/uplink/src && rm -f uplink.full && make
# If eclipse lib changed: cd src/lib/eclipse && make clean && make
```

## Architecture

### Server (`--headless --port 9090`)
- TCP line-delimited JSON, 39 commands
- Multiplayer: sequential context switching per session
- Session persistence: save on disconnect, restore on rejoin
- `src/uplink/src/network/headless_server.cpp` — all commands + state serializer
- `src/uplink/src/network/player_session.cpp` — session lifecycle

### Client
- `client/uplink_client.py` — main loop, TopBar, StatusBar, TabBar
- `client/ui/browser.py` — browser tab (bookmarks, connecting, all screen renderers)
- `client/ui/map_view.py` — interactive map with server dots
- `client/network.py` — TCP recv thread, GameState cache, 39 command methods
- `client/audio.py` — music (.uni via mikmodplayer) + SFX (.wav)
- `client/mikmod_ext/` — C extension wrapping libmikmod
- `client/.venv/` — Python venv (pygame, mikmodplayer, pytesseract, numpy, Pillow)

### Screen Renderers (all in browser.py)
Every server screen type has a dedicated renderer:
- `_draw_menu` — MenuScreen + HighSecurityScreen (options with arrows)
- `_draw_dialog` — DialogScreen (typed widgets: text, inputs, buttons)
- `_draw_password` — PasswordScreen/UserIDScreen (centered form)
- `_draw_message` — MessageScreen (text + conditional Continue)
- `_draw_links` — LinksScreen (filterable server list)
- `_draw_file_server` — GenericScreen (file columns with scroll)
- `_draw_log_viewer` — LogScreen (4-column access logs)
- `_draw_records` — GenericScreen Records (key-value table)
- `_draw_security` — GenericScreen Security (system levels)
- `_draw_console` — GenericScreen Console (terminal window)
- `_draw_company_info` — GenericScreen CompanyInfo (employee cards)
- `_draw_bookmarks` — disconnected view (saved servers)
- `_draw_connecting` — connection animation (progress bar)

### GenericScreen dispatch
Detects subtype by Eclipse button name prefixes:
- `recordscreen_title` → Records renderer
- `securityscreen_system` → Security renderer
- `console_typehere` → Console renderer
- `companyscreen_` → CompanyInfo renderer
- subtitle contains "file"/"server" + has files → FileServer renderer

**Critical**: Clear `remote_files`, `remote_logs`, `screen_links` on screen change to prevent stale data leak.

## API Commands (39)
```
join, state, connect, connect_bounce, disconnect, navigate, back, menu,
dialog_ok, password, crack_password, files, copy_file, delete_file, logs,
delete_logs, send_mail, check_mission, links, missions, bbs, accept_mission,
balance, gateway_files, gateway_info, hardware_list, buy_hardware, inbox,
trace, begin_trace, search, lan_scan, screen_links, software_list,
buy_software, set_field, speed, click, type, key
```

## Completed Features

### Content Tabs (all 6 done)
- **Email**: two-panel — message list + body reader. Compose email with To/Subject/Body/Attach. Attachment indicator.
- **Gateway**: model stats, memory bar, hardware list, file table. Right-click to delete gateway files.
- **Missions**: two-panel — list + details with clickable links (connect to target). "SEND COMPLETION" button.
- **BBS**: mission board with ACCEPT buttons. Refreshes bookmarks on accept.
- **Software**: catalog with BUY buttons, affordability coloring (teal/red).
- **Hardware**: catalog with BUY buttons, affordability coloring.

### Gameplay Mechanics (all done)
- **Password Cracking**: "Run Password Breaker" button → character-cycling animation → auto-fill + submit
- **Speed Control**: Clickable speed indicators in TopBar (||, >, >>, >>>)
- **Trace Polling**: Auto-polls every 2s, progress bar in StatusBar, audio warning at 80%
- **Bounce Routing**: Right-click map nodes to build route, dashed teal path, numbered markers
- **File Operations**: Timed progress bars for copy (~1s/GQ) and delete (~0.2s/GQ)
- **Log Operations**: Timed progress for delete all (~0.3s/log)
- **Console Typing**: Interactive text input, Enter to execute commands
- **Mission Completion**: Send email to contact + check_mission validation
- **Mission Links**: Clickable in detail panel to connect to target servers

### Visual Polish (8-round Gemini review)
- Letter-spaced titles on all screens ("U P L I N K   T E S T   M A C H I N E")
- Menu pointer `>` on left (signature Uplink style)
- Unified button style, zebra stripes, TopBar centering, column header brightness
- Links screen: IP right-aligned on same line as server name
- Log/file data entries brightened for readability

## Client TODO (next session)

### Remaining
- **Software running system**: Run tools (Log_Deleter, Decrypter) on targets — needs app sidebar UI
- **LAN view renderer**: LanComputer screen type
- **World persistence**: Save/restore across server restarts
- **Web client**: WebSocket bridge for browser-based play
- **HighSecurityScreen**: Interactive 3-factor challenge UI (works mechanically as menu)

## Server Screen Types (verified)
| OID | Type | Screens/Notes |
|-----|------|---------------|
| 31 | MessageScreen | Welcome text + conditional Continue |
| 33 | MenuScreen | Clickable options with nextpage |
| 34 | DialogScreen | Typed widgets (caption, textbox, button) |
| 37 | UserIDScreen | Username + password from RecordBank |
| 36 | PasswordScreen | Single password field |
| 30 | GenericScreen | FileServer, Records, Security, Console, CompanyInfo, News, Rankings |
| 38 | LogScreen | Access logs with 4 columns |
| 40 | LinksScreen | Player/All/Local links with filter |
| 42 | HighSecurityScreen | Multi-factor auth (3 challenges) |
| 35 | BBSScreen | Mission bulletin board |
| 15 | LanComputer | LAN topology (needs renderer) |

## Real Server Layouts (verified via admin login)
### Internal Services Machine (8 screens)
s0: UserIDScreen → s1: MenuScreen [File Server, View records, View links, Admin]
→ s2: FileServer, s3: LogScreen, s4: Records, s6: LinksScreen
→ s7: Admin Menu [View logs, Security, Console, Exit] → s3/s5/s8

### Bank (11+ screens)
s0: MenuScreen [About Us, Create Account, Manage Account, Administration]
→ s1: CompanyInfo, s4: DialogScreen (create), s2: UserIDScreen (manage)
→ s3: Account Menu [View Account, Statement, Transfer, Loans, Done]
→ s6: HighSecurityScreen [Password, Voice, Cypher]

### InterNIC (6 screens)
s0: MessageScreen → s1: MenuScreen [Browse/Search, Admin]
→ s2: LinksScreen (all servers, filterable) → s3: PasswordScreen → s4: Admin Menu

## Build Gotchas
- `export PATH="$HOME/uplink-re/src/bin:$PATH"` (apgcc/apg++ wrappers)
- Delete `~/.uplink/` when switching builds
- Client venv: `source client/.venv/bin/activate`
- mikmodplayer: `cd client/mikmod_ext && pip install -e .` (needs libmikmod-dev)
- Xvfb testing: `emerge x11-misc/xvfb-run x11-misc/xdotool media-gfx/scrot`
- Navigate to invalid screen was crashing — now returns error response
- Mission::GetDetails crashes on NULL — removed from serialization
- Session activate must preserve previousscreenindex for back button
