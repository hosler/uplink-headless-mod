# Uplink RE — Headless Multiplayer Server + Pygame Client

## Current Goal

Polish and extend the pygame client. All content tabs, server screen types, and core gameplay mechanics are complete. Focus areas: remaining server screen subtypes (Rankings), software running system, LAN interactivity, and web client.

## Quick Start

### Server
```bash
export PATH="$PWD/bin:$PATH"
cd uplink/src && rm -f uplink.full && make
cp uplink.full ../../game/uplink.bin.x86_64
rm -rf ~/.uplink/
export LD_LIBRARY_PATH="$PWD/../../contrib/FTGL-2.1.2/unix/src/.libs"
../../game/uplink.bin.x86_64 --headless --port 9090
```
~1s startup on warm cache. Wait for port 9090.

### Client
```bash
source client/.venv/bin/activate
python3 client/uplink_client.py
```
Optional flags: `--no-music`, `--debug-log /tmp/debug.json`, `--light-theme`

### Auto-testing (skip login UI)
```bash
python3 client/uplink_client.py --auto-join AgentName --auto-connect 128.185.0.4 --auto-crack
```

### Tests (all use keyboard shortcuts — no coordinate dependencies)
```bash
source client/.venv/bin/activate
cd client
python3 test_ui.py           # 16/16 basic UI
DARK_THEME=1 python3 test_ui_deep.py  # 7/7 server flows
python3 test_multiplayer.py  # 2 bots concurrent
python3 test_stress.py       # 28/28 API commands
python3 test_advanced.py     # 10/10 missions+shopping
python3 test_mechanics.py    # 9/9 trace+LAN+hardware
python3 test_mission.py      # 2 bots complete missions
python3 test_paid_mission.py # full paid mission flow
```

### Build after C++ changes
```bash
export PATH="$PWD/bin:$PATH"
cd uplink/src && rm -f uplink.full && make
cp uplink.full ../../game/uplink.bin.x86_64
# If eclipse lib changed: cd src/lib/eclipse && make clean && make
```

## Architecture

### Server (`--headless --port 9090`)
- TCP line-delimited JSON, 42 commands
- Multiplayer: sequential context switching per session
- Session persistence: save on disconnect, restore on rejoin
- `uplink/src/network/headless_server.cpp` — all commands + state serializer

### Client
- `client/uplink_client.py` — main loop, TopBar, StatusBar, TabBar (F1-F8 shortcuts)
- `client/ui/browser.py` — browser tab (bookmarks, connecting, all 14 screen renderers)
- `client/ui/content_tabs.py` — Email, Gateway, Missions, BBS, Software Market, Hardware
- `client/ui/map_view.py` — interactive map with server nodes, bounce routing
- `client/ui/app_sidebar.py` — software tools sidebar when connected
- `client/ui/login_screen.py` — login with HackerPanel
- `client/ui/widgets.py` — TextInput, Button, Label, HackerPanel, ScrollableList, ProgressBar
- `client/ui/theme.py` — colors, fonts, Scale, gradient, scanlines, WARNING color
- `client/network.py` — TCP recv thread, GameState cache, 42 command methods
- `client/audio.py` — music (.uni via mikmodplayer) + SFX (.wav)

### Keyboard Shortcuts
- **F1-F8**: Switch tabs (Browser, Map, Email, Gateway, Missions, BBS, Software, Hardware)
- **1-9**: Select bookmark or menu option
- **Enter**: Continue/OK/Submit
- **Backspace**: Go back
- **Escape**: Disconnect
- **P**: Run Password Breaker (on UserID/Password screens)

### Screen Renderers (all in browser.py)
- `_draw_menu` — MenuScreen + HighSecurityScreen (filled triangle pointers)
- `_draw_dialog` — DialogScreen (form with TextInput widgets, bank branding)
- `_draw_password` — PasswordScreen/UserIDScreen (AUTHENTICATION REQUIRED, sequential crack animation)
- `_draw_message` — MessageScreen (panel with dedup, CONTINUE button)
- `_draw_links` — LinksScreen (filterable server list, auto-bookmark on click)
- `_draw_file_server` — GenericScreen FileServer (FILENAME/SIZE/ENCRYPTION/COMPRESSION)
- `_draw_log_viewer` — LogScreen (4-column access logs with right-click delete)
- `_draw_records` — GenericScreen Records (DATABASE RECORD VIEW, key-value pairs)
- `_draw_security` — GenericScreen Security (system levels)
- `_draw_console` — GenericScreen Console (REMOTE TERMINAL SESSION, command prompt)
- `_draw_company_info` — GenericScreen CompanyInfo (2-column cards with avatars)
- `_draw_news` — GenericScreen News (two-panel: story list + detail body)
- `_draw_bookmarks` — disconnected view (BOOKMARKS title)
- `_draw_connecting` — ESTABLISHING LINK animation (progress bar, data noise)

### GenericScreen dispatch
Detects subtype by Eclipse button name prefixes:
- `recordscreen_title` → Records
- `securityscreen_system` → Security
- `console_typehere` → Console
- `companyscreen_` → CompanyInfo
- subtitle contains "news" → News renderer (requests news API data)
- subtitle contains "file"/"server" (not "news") + has files → FileServer

**Critical**: Clear `remote_files`, `remote_logs`, `screen_links`, `news` on screen change.

## API Commands (42)
```
join, state, connect, connect_bounce, disconnect, navigate, back, menu,
dialog_ok, password, crack_password, files, copy_file, delete_file, logs,
delete_logs, send_mail, check_mission, links, add_link, missions, bbs,
accept_mission, balance, gateway_files, gateway_info, hardware_list,
buy_hardware, inbox, news, trace, begin_trace, search, lan_scan,
screen_links, software_list, buy_software, set_field, speed, click, type, key
```

## Completed Features

### Content Tabs (all 6 done)
- **Email**: two-panel — message list + body reader with word wrap. Compose email.
- **Gateway**: model stats, memory bar (blue), hardware list, file table with encryption/compression.
- **Missions**: two-panel — list + details with clickable links. "SEND COMPLETION" button.
- **BBS**: mission board with ACCEPT buttons, employer column, full descriptions.
- **Software**: card-style marketplace (3x4 grid), version selector dots, paginated (27 tools).
- **Hardware**: catalog with BUY buttons, affordability coloring.

### All Server Screen Types (14 renderers)
MessageScreen, MenuScreen, DialogScreen, PasswordScreen, UserIDScreen, HighSecurityScreen, GenericScreen (FileServer, Records, Security, Console, CompanyInfo, News), LogScreen, LinksScreen, LanComputer.

### Gameplay Mechanics
- Password cracking with sequential character-cycling DECRYPTION animation
- Speed control (||, >, >>, >>>) with glow indicators
- Trace polling with progress bar and audio warnings
- Bounce routing via right-click map nodes
- File/log operations with timed progress bars
- Console typing with command execution
- Mission completion flow (email + check_mission)
- News feed (server API + two-panel reader)
- Auto-bookmark on connect (add_link API)

### Visual Polish (25+ Gemini review rounds)
- CRT scanlines + vignette overlay
- HackerPanel with corner accents throughout
- TopBar: AGENT:/HOST:/CREDITS:/PAUSE labels
- Tab bar: ALL CAPS with full highlight
- Map: full-width grid, pulsing target, data packets
- Themed buttons with corner tech accents
- Light theme support with adjusted colors
- WARNING theme color for gold/yellow elements

## Remaining TODO

### High Priority
- **Rankings renderer**: GenericScreen subtype on Uplink ISS (currently shows subtitle only)
- **Software running system**: Run tools (Log_Deleter, Decrypter) on targets via sidebar
- **HighSecurityScreen interactivity**: 3-factor challenge UI (voice, cypher bypass)
- **Populated BBS/Email screenshots**: Need game time to pass for mission generation

### Medium Priority
- **LAN interactivity**: Navigate LAN nodes, hack systems
- **World persistence**: Save/restore across server restarts
- **Email compose**: Functional compose form with attachments

### Low Priority
- **Web client**: WebSocket bridge for browser-based play
- **Stock Market**: Requires dedicated renderer for trading UI

## Build Gotchas
- `export PATH="$PWD/bin:$PATH"` (apgcc/apg++ wrappers needed)
- Delete `~/.uplink/` when switching builds
- Client venv: `source client/.venv/bin/activate`
- mikmodplayer: `cd client/mikmod_ext && pip install -e .` (needs libmikmod-dev)
- Xvfb testing: `emerge x11-misc/xvfb-run x11-misc/xdotool media-gfx/scrot`
- All UI tests use keyboard shortcuts (F-keys, Enter, Backspace, Escape, 1-9, P)
- Screenshot scripts: `take_screenshots.py`, `take_all_screenshots.py`, `take_server_screenshots.py`, `take_database_screenshots.py`
- Gemini CLI: `gemini -p "" --yolo` for aesthetic reviews (rate limits apply)
- **IMPORTANT**: Only let Gemini modify Python files in client/ — never C++ server code
