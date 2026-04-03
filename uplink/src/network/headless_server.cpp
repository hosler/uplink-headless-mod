#include "stdafx.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <string>
#include <math.h>
#include <vector>

#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <poll.h>
#include <fcntl.h>
#include <errno.h>

#include "eclipse.h"

#include "app/app.h"
#include "app/globals.h"
#include "app/serialise.h"

#include "game/game.h"

#include "interface/interface.h"
#include "interface/remoteinterface/remoteinterface.h"

#include "world/world.h"
#include "world/player.h"
#include "world/vlocation.h"
#include "world/date.h"
#include "world/computer/computer.h"
#include "world/computer/computerscreen/computerscreen.h"
#include "world/computer/computerscreen/menuscreen.h"
#include "world/computer/computerscreen/dialogscreen.h"
#include "world/computer/computerscreen/passwordscreen.h"
#include "world/computer/computerscreen/linksscreen.h"
#include "world/computer/computerscreen/genericscreen.h"
#include "world/computer/computerscreen/logscreen.h"
#include "world/computer/computerscreen/useridscreen.h"
#include "world/computer/computerscreen/highsecurityscreen.h"
#include "world/computer/computerscreen/menuscreen.h"
#include "world/computer/recordbank.h"
#include "world/computer/databank.h"
#include "world/computer/logbank.h"
#include "world/computer/gateway.h"
#include "world/computer/gatewaydef.h"
#include "world/computer/lancomputer.h"
#include "world/company/mission.h"
#include "world/company/sale.h"
#include "world/generator/missiongenerator.h"
#include "world/company/companyuplink.h"
#include "world/company/news.h"
#include "world/message.h"

#include "interface/localinterface/localinterface.h"
#include "interface/taskmanager/taskmanager.h"

#include "app/opengl.h"
#include "network/headless_server.h"
#include "network/player_session.h"

#include "mmgr.h"

// ============================================================================
// Globals
// ============================================================================

bool g_headless = false;
int  g_headless_port = 9090;
extern bool g_headless_player_update_allowed;  // defined in player.cpp

// ============================================================================
// Internal state
// ============================================================================

struct ClientConn {
    int fd;
    std::string readbuf;
    PlayerSession *session;  // NULL until "join" command
};

static int listen_fd = -1;
static std::vector<ClientConn> clients;
static bool active = false;

// ============================================================================
// Helpers
// ============================================================================

static void set_nonblocking ( int fd )
{
    int flags = fcntl ( fd, F_GETFL, 0 );
    fcntl ( fd, F_SETFL, flags | O_NONBLOCK );
}

static void send_line ( int fd, const std::string &line )
{
    std::string msg = line + "\n";
    // Best-effort send, ignore partial writes for now
    send ( fd, msg.c_str(), msg.size(), MSG_NOSIGNAL );
}

static void send_to_all ( const std::string &line )
{
    for ( auto &c : clients )
        send_line ( c.fd, line );
}

// Escape a string for JSON (handle quotes, backslashes, newlines)
static std::string json_escape ( const char *s )
{
    if ( !s ) return "";
    std::string out;
    for ( ; *s; s++ ) {
        switch ( *s ) {
            case '"':  out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\n': out += "\\n"; break;
            case '\r': out += "\\r"; break;
            case '\t': out += "\\t"; break;
            default:
                if ( (unsigned char)*s < 0x20 ) {
                    char buf[8];
                    snprintf ( buf, sizeof(buf), "\\u%04x", (unsigned char)*s );
                    out += buf;
                } else {
                    out += *s;
                }
        }
    }
    return out;
}

// Minimal JSON field extraction: find "key":"value" and copy value to buf
static bool extract_str ( const char *json, const char *key, char *buf, int bufsz )
{
    char pattern[128];
    snprintf ( pattern, sizeof(pattern), "\"%s\"", key );
    const char *p = strstr ( json, pattern );
    if ( !p ) return false;
    p += strlen(pattern);
    while ( *p == ' ' || *p == ':' ) p++;
    if ( *p != '"' ) return false;
    p++;
    int i = 0;
    while ( *p && *p != '"' && i < bufsz - 1 ) {
        if ( *p == '\\' && *(p+1) ) {
            p++;
            switch (*p) {
                case 'n': buf[i++] = '\n'; break;
                case 'r': buf[i++] = '\r'; break;
                case 't': buf[i++] = '\t'; break;
                case '"': buf[i++] = '"'; break;
                case '\\': buf[i++] = '\\'; break;
                default: buf[i++] = *p; break;
            }
            p++;
            continue;
        }
        buf[i++] = *p++;
    }
    buf[i] = '\0';
    return true;
}

static int extract_int ( const char *json, const char *key )
{
    char pattern[128];
    snprintf ( pattern, sizeof(pattern), "\"%s\"", key );
    const char *p = strstr ( json, pattern );
    if ( !p ) return -1;
    p += strlen(pattern);
    while ( *p == ' ' || *p == ':' ) p++;
    return atoi(p);
}

static double extract_double ( const char *json, const char *key )
{
    char pattern[128];
    snprintf ( pattern, sizeof(pattern), "\"%s\"", key );
    const char *p = strstr ( json, pattern );
    if ( !p ) return -1.0;
    p += strlen(pattern);
    while ( *p == ' ' || *p == ':' ) p++;
    return atof(p);
}

// ============================================================================
// Command dispatch
// ============================================================================

static std::string serialize_state ();  // forward decl

static void send_response ( int fd, const char *status, const char *detail )
{
    char buf[512];
    snprintf ( buf, sizeof(buf), "{\"type\":\"response\",\"status\":\"%s\",\"detail\":\"%s\"}",
        status, json_escape(detail).c_str() );
    send_line ( fd, buf );
}

static void handle_command ( const char *json, ClientConn *conn )
{
    int client_fd = conn->fd;
    char cmd[32];
    if ( !extract_str(json, "cmd", cmd, sizeof(cmd)) ) return;

    // ---- Session management ----

    if ( strcmp(cmd, "join") == 0 ) {
        char handle[128], pw[128];
        if ( !extract_str(json, "handle", handle, sizeof(handle)) ) {
            send_response(client_fd, "error", "missing handle");
            return;
        }
        if ( !extract_str(json, "password", pw, sizeof(pw)) )
            strcpy(pw, "default");

        if ( conn->session ) {
            send_response(client_fd, "error", "already joined");
            return;
        }

        // Try to load a saved session first
        conn->session = SessionLoad ( handle );
        if ( conn->session ) {
            char detail[128];
            snprintf(detail, sizeof(detail), "session %d (restored)", conn->session->session_id);
            send_response(client_fd, "ok", detail);
        } else {
            // No save — create new session
            conn->session = SessionCreate ( handle, pw );
            if ( conn->session ) {
                char detail[64];
                snprintf(detail, sizeof(detail), "session %d (new)", conn->session->session_id);
                send_response(client_fd, "ok", detail);
            } else {
                send_response(client_fd, "error", "session create failed");
            }
        }
        return;
    }

    // All other commands require an active session
    if ( !conn->session ) {
        send_response(client_fd, "error", "not joined - send {\"cmd\":\"join\",\"handle\":\"name\"}");
        return;
    }

    // Activate this client's session
    SessionActivate ( conn->session );

    // ---- Low-level commands (Eclipse) ----

    if ( strcmp(cmd, "click") == 0 ) {
        char bname[128];
        if ( extract_str(json, "button", bname, sizeof(bname)) ) {
            Button *b = EclGetButton(bname);
            if ( b ) {
                b->MouseDown();
                b->MouseUp();
                send_response ( client_fd, "ok", bname );
            } else {
                send_response ( client_fd, "error", "button not found" );
            }
        }
    }
    else if ( strcmp(cmd, "type") == 0 ) {
        char text[256];
        if ( extract_str(json, "text", text, sizeof(text)) ) {
            for ( int i = 0; text[i]; i++ )
                opengl_inject_keyboard ( (unsigned char)text[i], 0, 0 );
            send_response ( client_fd, "ok", "typed" );
        }
    }
    else if ( strcmp(cmd, "key") == 0 ) {
        int code = extract_int ( json, "code" );
        if ( code >= 0 && code < 256 ) {
            opengl_inject_keyboard ( (unsigned char)code, 0, 0 );
            send_response ( client_fd, "ok", "key sent" );
        }
    }

    // ---- Game control ----

    else if ( strcmp(cmd, "speed") == 0 ) {
        int val = extract_int ( json, "value" );
        if ( val >= 0 && val <= 4 && game && game->IsRunning() ) {
            game->SetGameSpeed ( val );
            send_response ( client_fd, "ok", "speed set" );
        }
    }

    // ---- Semantic: Navigation ----

    else if ( strcmp(cmd, "navigate") == 0 ) {
        // Navigate to a screen index on the current computer
        // {"cmd":"navigate","screen":5}
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        Player *p = game->GetWorld()->GetPlayer();
        if ( !p->IsConnected() ) { send_response(client_fd,"error","not connected"); return; }

        int screen = extract_int ( json, "screen" );
        if ( screen < 0 ) { send_response(client_fd,"error","invalid screen"); return; }

        // Validate screen index exists on this computer
        VLocation *vl = game->GetWorld()->GetVLocation( p->remotehost );
        if ( !vl ) { send_response(client_fd,"error","no location"); return; }
        Computer *comp = vl->GetComputer();
        if ( !comp ) { send_response(client_fd,"error","no computer"); return; }
        ComputerScreen *cs = comp->GetComputerScreen( screen );
        if ( !cs ) {
            send_response(client_fd,"error","screen not found");
            return;
        }

        game->GetInterface()->GetRemoteInterface()->RunScreen ( screen, comp );
        send_response ( client_fd, "ok", "navigated" );
    }

    else if ( strcmp(cmd, "back") == 0 ) {
        // Navigate to previous screen
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        Player *p = game->GetWorld()->GetPlayer();
        if ( !p->IsConnected() ) { send_response(client_fd,"error","not connected"); return; }

        int prev = game->GetInterface()->GetRemoteInterface()->previousscreenindex;
        VLocation *vl = game->GetWorld()->GetVLocation( p->remotehost );
        Computer *comp = vl ? vl->GetComputer() : NULL;
        if ( comp && comp->GetComputerScreen(prev) ) {
            game->GetInterface()->GetRemoteInterface()->RunScreen ( prev, comp );
            send_response ( client_fd, "ok", "back" );
        } else {
            send_response ( client_fd, "error", "no previous screen" );
        }
    }

    // ---- Semantic: Connection ----

    else if ( strcmp(cmd, "connect") == 0 ) {
        // Connect to a server by IP
        // {"cmd":"connect","ip":"192.168.1.1"}
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        char ip[64];
        if ( extract_str(json, "ip", ip, sizeof(ip)) ) {
            Player *p = game->GetWorld()->GetPlayer();
            VLocation *vl = game->GetWorld()->GetVLocation(ip);
            if ( !vl ) { send_response(client_fd,"error","unknown ip"); return; }

            // Disconnect from current, connect to new
            p->GetConnection()->Disconnect();
            p->GetConnection()->Reset();
            p->GetConnection()->AddVLocation( p->localhost );
            p->GetConnection()->AddVLocation( ip );
            p->GetConnection()->Connect();
            game->GetInterface()->GetRemoteInterface()->RunNewLocation();
            game->GetInterface()->GetRemoteInterface()->RunScreen ( 0, NULL );
            send_response ( client_fd, "ok", ip );
        }
    }
    else if ( strcmp(cmd, "disconnect") == 0 ) {
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        Player *p = game->GetWorld()->GetPlayer();
        p->GetConnection()->Disconnect();
        p->GetConnection()->Reset();
        // Return to gateway
        game->GetInterface()->GetRemoteInterface()->RunNewLocation();
        send_response ( client_fd, "ok", "disconnected" );
    }

    // ---- Semantic: Password ----

    else if ( strcmp(cmd, "password") == 0 ) {
        // Submit credentials on PasswordScreen or UserIDScreen
        // {"cmd":"password","value":"rosebud"} — password only
        // {"cmd":"password","user":"admin","value":"rosebud"} — user + password
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        char pw[128], user[128];
        if ( !extract_str(json, "value", pw, sizeof(pw)) ) {
            send_response(client_fd,"error","missing value"); return;
        }
        if ( !extract_str(json, "user", user, sizeof(user)) )
            strcpy(user, RECORDBANK_ADMIN);

        ComputerScreen *cs = game->GetInterface()->GetRemoteInterface()->GetComputerScreen();
        if ( !cs ) { send_response(client_fd,"error","no screen"); return; }

        int oid = cs->GetOBJECTID();

        if ( oid == OID_PASSWORDSCREEN ) {
            PasswordScreen *ps = (PasswordScreen*)cs;
            if ( strcmp(pw, ps->password) == 0 ) {
                game->GetInterface()->GetRemoteInterface()->SetSecurity (
                    (char*)user, 1 );
                game->GetInterface()->GetRemoteInterface()->RunScreen (
                    ps->nextpage, NULL );
                send_response ( client_fd, "ok", "authenticated" );
            } else {
                send_response ( client_fd, "error", "wrong password" );
            }
        }
        else if ( oid == OID_USERIDSCREEN ) {
            UserIDScreen *uid = (UserIDScreen*)cs;
            Computer *comp = uid->GetComputer();
            Record *rec = comp->recordbank.GetRecordFromNamePassword (
                (char*)user, (char*)pw );
            if ( rec ) {
                char *security = rec->GetField(RECORDBANK_SECURITY);
                int secLevel = security ? atoi(security) : 1;
                game->GetInterface()->GetRemoteInterface()->SetSecurity (
                    (char*)user, secLevel );
                game->GetInterface()->GetRemoteInterface()->RunScreen (
                    uid->nextpage, NULL );
                send_response ( client_fd, "ok", "authenticated" );
            } else {
                send_response ( client_fd, "error", "invalid credentials" );
            }
        }
        else {
            send_response(client_fd,"error","not on password/userid screen");
        }
    }

    // ---- Semantic: Menu selection ----

    else if ( strcmp(cmd, "menu") == 0 ) {
        // Select a menu option by index
        // {"cmd":"menu","option":0}
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        int opt = extract_int ( json, "option" );
        ComputerScreen *cs = game->GetInterface()->GetRemoteInterface()->GetComputerScreen();
        if ( !cs || cs->GetOBJECTID() != OID_MENUSCREEN ) {
            send_response(client_fd,"error","not on menu screen");
            return;
        }
        MenuScreen *ms = (MenuScreen*)cs;
        if ( opt < 0 || opt >= ms->NumOptions() ) {
            send_response(client_fd,"error","invalid option");
            return;
        }
        int nextPage = ms->GetNextPage(opt);
        int security = ms->GetSecurity(opt);
        int secLevel = game->GetInterface()->GetRemoteInterface()->security_level;
        if ( secLevel <= security ) {
            game->GetInterface()->GetRemoteInterface()->RunScreen (
                nextPage, ms->GetComputer() );
            send_response ( client_fd, "ok", ms->GetCaption(opt) );
        } else {
            send_response ( client_fd, "error", "access denied" );
        }
    }

    // ---- Semantic: Dialog OK ----

    else if ( strcmp(cmd, "dialog_ok") == 0 ) {
        // Click OK on a dialog screen (advance to next page)
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        ComputerScreen *cs = game->GetInterface()->GetRemoteInterface()->GetComputerScreen();
        if ( !cs || cs->GetOBJECTID() != OID_DIALOGSCREEN ) {
            send_response(client_fd,"error","not on dialog screen");
            return;
        }
        DialogScreen *ds = (DialogScreen*)cs;
        // Find a NEXTPAGE widget and navigate
        bool found = false;
        for ( int i = 0; i < ds->widgets.Size(); i++ ) {
            DialogScreenWidget *w = ds->widgets.GetData(i);
            if ( !w ) continue;
            if ( w->WIDGETTYPE == WIDGET_NEXTPAGE || w->WIDGETTYPE == WIDGET_SCRIPTBUTTON ) {
                Computer *comp = ds->GetComputer();
                char vname[200];
                snprintf ( vname, sizeof(vname), "%s %d %d %s",
                    w->GetName(), w->data1, w->data2, comp->ip );
                Button *vb = EclGetButton(vname);
                if ( !vb ) {
                    snprintf ( vname, sizeof(vname), "%s %d %d",
                        w->GetName(), w->data1, w->data2 );
                    vb = EclGetButton(vname);
                }
                if ( vb ) {
                    vb->MouseDown();
                    vb->MouseUp();
                    send_response(client_fd,"ok","dialog advanced");
                    found = true;
                    break;
                }
            }
        }
        if ( !found ) {
            // Fallback: try clicking any button with "ok" in its name
            int nb = EclGetNumButtons();
            for ( int i = 0; i < nb; i++ ) {
                Button *b = EclGetButtonByIndex(i);
                if ( b && strstr(b->name, "okbutton") ) {
                    b->MouseDown();
                    b->MouseUp();
                    send_response(client_fd,"ok","dialog ok (fallback)");
                    found = true;
                    break;
                }
            }
        }
        if ( !found )
            send_response ( client_fd, "error", "no ok button found" );
    }

    // ---- Semantic: Player info ----

    else if ( strcmp(cmd, "links") == 0 ) {
        // Get list of known server IPs
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        Player *p = game->GetWorld()->GetPlayer();
        std::string s = "{\"type\":\"links\",\"links\":[";
        for ( int i = 0; i < p->links.Size(); i++ ) {
            if ( i > 0 ) s += ",";
            char *ip = p->links.GetData(i);
            VLocation *vl = game->GetWorld()->GetVLocation(ip);
            Computer *comp = vl ? vl->GetComputer() : NULL;
            char buf[256];
            snprintf ( buf, sizeof(buf), "{\"ip\":\"%s\",\"name\":\"%s\"}",
                json_escape(ip).c_str(),
                comp ? json_escape(comp->name).c_str() : "" );
            s += buf;
        }
        s += "]}";
        send_line ( client_fd, s );
    }

    else if ( strcmp(cmd, "add_link") == 0 ) {
        // Add a server IP to the player's bookmarks
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        char ip[64];
        if ( !extract_str(json, "ip", ip, sizeof(ip)) ) {
            send_response(client_fd,"error","missing ip"); return;
        }
        Player *p = game->GetWorld()->GetPlayer();
        VLocation *vl = game->GetWorld()->GetVLocation(ip);
        if ( !vl ) { send_response(client_fd,"error","unknown ip"); return; }
        if ( p->HasLink(ip) ) {
            send_response(client_fd,"ok","already linked");
        } else {
            p->GiveLink(ip);
            Computer *comp = vl->GetComputer();
            char detail[256];
            snprintf(detail, sizeof(detail), "added %s", comp ? comp->name : ip);
            send_response(client_fd,"ok",detail);
        }
    }

    else if ( strcmp(cmd, "missions") == 0 ) {
        // Get list of active missions with full details
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        Player *p = game->GetWorld()->GetPlayer();
        std::string s = "{\"type\":\"missions\",\"missions\":[";
        for ( int i = 0; i < p->missions.Size(); i++ ) {
            Mission *m = p->missions.GetData(i);
            if ( !m ) continue;
            if ( i > 0 ) s += ",";
            char buf[1024];
            snprintf ( buf, sizeof(buf),
                "{\"index\":%d,\"type\":%d,\"employer\":\"%s\",\"contact\":\"%s\","
                "\"description\":\"%s\",\"payment\":%d,\"difficulty\":%d,"
                "\"completionA\":\"%s\",\"completionB\":\"%s\"",
                i, m->TYPE,
                json_escape(m->employer).c_str(),
                json_escape(m->contact).c_str(),
                json_escape(m->description).c_str(),
                m->payment, m->difficulty,
                m->completionA ? json_escape(m->completionA).c_str() : "",
                m->completionB ? json_escape(m->completionB).c_str() : "" );
            s += buf;

            // Links
            s += ",\"links\":[";
            for ( int j = 0; j < m->links.Size(); j++ ) {
                if ( j > 0 ) s += ",";
                s += "\"";
                s += json_escape(m->links.GetData(j));
                s += "\"";
            }
            s += "]";

            // Codes
            s += ",\"codes\":{";
            DArray<char*> *ips = m->codes.ConvertIndexToDArray();
            DArray<char*> *codes = m->codes.ConvertToDArray();
            bool first = true;
            for ( int j = 0; j < ips->Size(); j++ ) {
                if ( !ips->ValidIndex(j) ) continue;
                if ( !first ) s += ",";
                first = false;
                snprintf(buf, sizeof(buf), "\"%s\":\"%s\"",
                    json_escape(ips->GetData(j)).c_str(),
                    json_escape(codes->GetData(j)).c_str());
                s += buf;
            }
            delete ips;
            delete codes;
            s += "}";

            // Full details — only include for player's own missions
            // (BBS missions may not have details set, and GetDetails() asserts on NULL)
            // We can safely call GetDetails only when mission has been accepted
            // (the fulldetails field is set by SetFullDetails in mission creation)

            s += "}";
        }
        s += "]}";
        send_line ( client_fd, s );
    }

    else if ( strcmp(cmd, "set_field") == 0 ) {
        // Directly set an Eclipse button's caption (data write, no UI)
        // {"cmd":"set_field","button":"passwordscreen_password","value":"admin"}
        char bname[128], val[512];
        if ( extract_str(json, "button", bname, sizeof(bname)) &&
             extract_str(json, "value", val, sizeof(val)) ) {
            Button *b = EclGetButton(bname);
            if ( b ) {
                b->SetCaption ( val );
                send_response ( client_fd, "ok", bname );
            } else {
                send_response ( client_fd, "error", "button not found" );
            }
        }
    }

    // ---- Semantic: File operations ----

    else if ( strcmp(cmd, "files") == 0 ) {
        // List files on the currently connected computer
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        Player *p = game->GetWorld()->GetPlayer();
        VLocation *vl = game->GetWorld()->GetVLocation( p->remotehost );
        if ( !vl ) { send_response(client_fd,"error","not connected"); return; }
        Computer *comp = vl->GetComputer();
        if ( !comp ) { send_response(client_fd,"error","no computer"); return; }

        std::string s = "{\"type\":\"files\",\"computer\":\"";
        s += json_escape(comp->name);
        s += "\",\"files\":[";
        bool first = true;
        for ( int i = 0; i < comp->databank.GetSize(); i++ ) {
            Data *d = comp->databank.GetData(i);
            if ( !d ) continue;
            if ( !first ) s += ",";
            first = false;
            char buf[256];
            snprintf(buf, sizeof(buf),
                "{\"index\":%d,\"title\":\"%s\",\"size\":%d,\"encrypted\":%d,\"compressed\":%d}",
                i, json_escape(d->title).c_str(), d->size, d->encrypted, d->compressed);
            s += buf;
        }
        s += "]}";
        send_line ( client_fd, s );
    }
    else if ( strcmp(cmd, "copy_file") == 0 ) {
        // Copy a file from remote computer to player's gateway
        // {"cmd":"copy_file","title":"Uplink test data"}
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        char title[256];
        if ( !extract_str(json, "title", title, sizeof(title)) ) {
            send_response(client_fd,"error","missing title");
            return;
        }
        Player *p = game->GetWorld()->GetPlayer();
        VLocation *vl = game->GetWorld()->GetVLocation( p->remotehost );
        if ( !vl ) { send_response(client_fd,"error","not connected"); return; }
        Computer *comp = vl->GetComputer();
        Data *src = comp->databank.GetData(title);
        if ( !src ) { send_response(client_fd,"error","file not found"); return; }

        Data *copy = new Data();
        copy->SetTitle ( src->title );
        copy->SetDetails ( src->TYPE, src->size, src->encrypted, src->compressed );
        if ( p->gateway.databank.PutData(copy) ) {
            send_response ( client_fd, "ok", title );
        } else {
            delete copy;
            send_response ( client_fd, "error", "no space on gateway" );
        }
    }

    else if ( strcmp(cmd, "delete_file") == 0 ) {
        // Delete a file from the current remote computer
        // {"cmd":"delete_file","title":"Secret Data"}
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        char title[256];
        if ( !extract_str(json, "title", title, sizeof(title)) ) {
            send_response(client_fd,"error","missing title"); return;
        }
        Player *p = game->GetWorld()->GetPlayer();
        VLocation *vl = game->GetWorld()->GetVLocation( p->remotehost );
        if ( !vl ) { send_response(client_fd,"error","not connected"); return; }
        Computer *comp = vl->GetComputer();
        Data *d = comp->databank.GetData(title);
        if ( !d ) { send_response(client_fd,"error","file not found"); return; }
        // Find the memory index for this data
        for ( int i = 0; i < comp->databank.GetSize(); i++ ) {
            if ( comp->databank.GetData(i) == d ) {
                comp->databank.RemoveData(i);
                send_response(client_fd, "ok", title);
                return;
            }
        }
        send_response(client_fd,"error","could not remove file");
    }

    // ---- Semantic: Log operations ----

    else if ( strcmp(cmd, "logs") == 0 ) {
        // List access logs on current computer
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        Player *p = game->GetWorld()->GetPlayer();
        VLocation *vl = game->GetWorld()->GetVLocation( p->remotehost );
        if ( !vl ) { send_response(client_fd,"error","not connected"); return; }
        Computer *comp = vl->GetComputer();

        std::string s = "{\"type\":\"logs\",\"logs\":[";
        bool first = true;
        for ( int i = 0; i < comp->logbank.logs.Size(); i++ ) {
            if ( !comp->logbank.logs.ValidIndex(i) ) continue;
            AccessLog *log = comp->logbank.logs.GetData(i);
            if ( !log ) continue;
            if ( !first ) s += ",";
            first = false;
            char buf[512];
            snprintf(buf, sizeof(buf),
                "{\"index\":%d,\"date\":\"%s\",\"from_ip\":\"%s\",\"from_name\":\"%s\",\"suspicious\":%d,\"data1\":\"%s\"}",
                i,
                log->date.GetShortString(),
                json_escape(log->fromip).c_str(),
                json_escape(log->fromname).c_str(),
                log->SUSPICIOUS,
                log->data1 ? json_escape(log->data1).c_str() : "");
            s += buf;
        }
        s += "]}";
        send_line ( client_fd, s );
    }
    else if ( strcmp(cmd, "delete_logs") == 0 ) {
        // Delete all logs on current computer
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        Player *p = game->GetWorld()->GetPlayer();
        VLocation *vl = game->GetWorld()->GetVLocation( p->remotehost );
        if ( !vl ) { send_response(client_fd,"error","not connected"); return; }
        Computer *comp = vl->GetComputer();
        int count = comp->logbank.logs.Size();
        comp->logbank.Empty();
        char detail[64];
        snprintf(detail, sizeof(detail), "deleted %d logs", count);
        send_response ( client_fd, "ok", detail );
    }

    else if ( strcmp(cmd, "delete_log") == 0 ) {
        // Delete a single log entry by index
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        Player *p = game->GetWorld()->GetPlayer();
        VLocation *vl = game->GetWorld()->GetVLocation( p->remotehost );
        if ( !vl ) { send_response(client_fd,"error","not connected"); return; }
        Computer *comp = vl->GetComputer();
        int index = extract_int(json, "index");
        if ( index < 0 || index >= comp->logbank.logs.Size() ) {
            send_response(client_fd,"error","invalid log index");
            return;
        }
        comp->logbank.logs.RemoveData( index );
        char detail[64];
        snprintf(detail, sizeof(detail), "deleted log %d", index);
        send_response ( client_fd, "ok", detail );
    }

    // ---- Semantic: Email ----

    else if ( strcmp(cmd, "send_mail") == 0 ) {
        // Send email, optionally with a file attachment from gateway
        // {"cmd":"send_mail","to":"internal@Uplink.net","subject":"Done","body":"...","attach":"Uplink test data"}
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        char to[128], subject[256], body[1024], attach[256];
        if ( !extract_str(json, "to", to, sizeof(to)) ) {
            send_response(client_fd,"error","missing to");
            return;
        }
        extract_str(json, "subject", subject, sizeof(subject));
        extract_str(json, "body", body, sizeof(body));

        Message *msg = new Message();
        msg->SetTo ( to );
        msg->SetFrom ( "PLAYER" );
        msg->SetSubject ( subject );
        msg->SetBody ( body );

        // Attach file from gateway if specified
        if ( extract_str(json, "attach", attach, sizeof(attach)) && attach[0] ) {
            Player *p = game->GetWorld()->GetPlayer();
            Data *src = p->gateway.databank.GetData(attach);
            if ( src ) {
                Data *attachData = new Data();
                attachData->SetTitle ( src->title );
                attachData->SetDetails ( src->TYPE, src->size, src->encrypted, src->compressed );
                msg->AttachData ( attachData );
            }
        }

        msg->Send();
        send_response ( client_fd, "ok", "sent" );
    }

    // ---- Semantic: Mission completion ----

    else if ( strcmp(cmd, "check_mission") == 0 ) {
        // Force-process any pending mission completion emails for this player
        // This handles the NPC mail processing that normally happens in World::Update
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        Player *p = game->GetWorld()->GetPlayer();

        // Check each mission's contact person for mail from PLAYER
        bool completed = false;
        char debug[1024] = "";
        for ( int mi = p->missions.Size() - 1; mi >= 0; mi-- ) {
            Mission *mis = p->missions.GetData(mi);
            if ( !mis ) continue;

            Person *contact = game->GetWorld()->GetPerson( mis->contact );
            if ( !contact ) {
                snprintf(debug, sizeof(debug), "contact '%s' not found", mis->contact);
                break;
            }

            int nmsg = contact->messages.Size();
            snprintf(debug, sizeof(debug), "contact '%s' has %d msgs, desc='%.50s'",
                mis->contact, nmsg, mis->description);

            for ( int mi2 = 0; mi2 < contact->messages.Size(); mi2++ ) {
                Message *msg = contact->messages.GetData(mi2);
                if ( !msg ) continue;

                bool fromPlayer = (strcmp(msg->from, "PLAYER") == 0);
                bool hasDesc = (strstr(msg->GetBody(), mis->description) != NULL);
                bool hasData = (msg->GetData() != NULL);

                snprintf(debug, sizeof(debug),
                    "msg[%d] from='%s' fromPlayer=%d hasDesc=%d hasData=%d body='%.60s'",
                    mi2, msg->from, fromPlayer, hasDesc, hasData,
                    msg->GetBody() ? msg->GetBody() : "(null)");

                if ( !fromPlayer ) continue;
                if ( !hasDesc ) continue;

                if ( MissionGenerator::IsMissionComplete(mis, contact, msg) ) {
                    p->missions.RemoveData(mi);
                    send_response(client_fd, "ok", "mission completed");
                    completed = true;
                    contact->messages.RemoveData(mi2);
                    delete msg;
                    delete mis;
                    break;
                } else {
                    snprintf(debug, sizeof(debug), "IsMissionComplete returned false");
                }
            }
            if ( completed ) break;
        }
        if ( !completed )
            send_response(client_fd, "error", debug);
    }

    // ---- Semantic: Finances ----

    else if ( strcmp(cmd, "balance") == 0 ) {
        // Get player's bank balance
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        Player *p = game->GetWorld()->GetPlayer();
        int bal = p->GetBalance();
        char buf[128];
        snprintf(buf, sizeof(buf), "{\"type\":\"balance\",\"balance\":%d}", bal);
        send_line(client_fd, buf);
    }

    // ---- Semantic: Inbox (read messages) ----

    else if ( strcmp(cmd, "inbox") == 0 ) {
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        Player *p = game->GetWorld()->GetPlayer();
        std::string s = "{\"type\":\"inbox\",\"messages\":[";
        for ( int i = 0; i < p->messages.Size(); i++ ) {
            Message *msg = p->messages.GetData(i);
            if ( !msg ) continue;
            if ( i > 0 ) s += ",";
            char buf[1024];
            snprintf(buf, sizeof(buf),
                "{\"index\":%d,\"from\":\"%s\",\"to\":\"%s\",\"subject\":\"%s\","
                "\"body\":\"%s\",\"hasdata\":%s}",
                i,
                json_escape(msg->from).c_str(),
                json_escape(msg->to).c_str(),
                json_escape(msg->GetSubject() ? msg->GetSubject() : "").c_str(),
                json_escape(msg->GetBody() ? msg->GetBody() : "").c_str(),
                msg->GetData() ? "true" : "false");
            s += buf;
        }
        s += "]}";
        send_line(client_fd, s);
    }

    // ---- Semantic: News feed ----

    else if ( strcmp(cmd, "news") == 0 ) {
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        CompanyUplink *cu = (CompanyUplink*)game->GetWorld()->GetCompany("Uplink");
        if ( !cu ) { send_response(client_fd,"error","no company"); return; }

        std::string s = "{\"type\":\"news\",\"stories\":[";
        for ( int i = cu->news.Size() - 1; i >= 0; i-- ) {
            News *n = cu->news.GetData(i);
            if ( !n ) continue;
            if ( s.back() != '[' ) s += ",";
            char buf[2048];
            char *det = n->GetDetails();
            snprintf(buf, sizeof(buf),
                "{\"index\":%d,\"headline\":\"%s\",\"date\":\"%s\","
                "\"details\":\"%s\",\"type\":%d}",
                i,
                json_escape(n->headline).c_str(),
                json_escape(n->date.GetShortString()).c_str(),
                json_escape(det ? det : "").c_str(),
                n->NEWSTYPE);
            s += buf;
        }
        s += "]}";
        send_line(client_fd, s);
    }

    // ---- Semantic: Trace status ----

    else if ( strcmp(cmd, "trace") == 0 ) {
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        Player *p = game->GetWorld()->GetPlayer();
        Connection *conn = p->GetConnection();
        char buf[256];
        snprintf(buf, sizeof(buf),
            "{\"type\":\"trace\",\"active\":%s,\"progress\":%d,\"total\":%d}",
            conn->traceinprogress ? "true" : "false",
            conn->traceprogress,
            conn->GetSize() - 1);
        send_line(client_fd, buf);
    }
    else if ( strcmp(cmd, "begin_trace") == 0 ) {
        // Debug: force-start a trace on the current connection
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        Player *p = game->GetWorld()->GetPlayer();
        if ( !p->IsConnected() ) { send_response(client_fd,"error","not connected"); return; }
        p->GetConnection()->BeginTrace();
        send_response(client_fd, "ok",
            p->GetConnection()->TraceInProgress() ? "trace started" : "trace not started (no traceaction)");
    }

    // ---- Semantic: Software purchase ----

    else if ( strcmp(cmd, "buy_software") == 0 ) {
        // Buy software from Uplink's catalog
        // {"cmd":"buy_software","title":"Password_Breaker","version":1.0}
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        char title[128];
        if ( !extract_str(json, "title", title, sizeof(title)) ) {
            send_response(client_fd,"error","missing title"); return;
        }

        CompanyUplink *cu = (CompanyUplink*)game->GetWorld()->GetCompany("Uplink");
        if ( !cu ) { send_response(client_fd,"error","no company"); return; }

        Player *p = game->GetWorld()->GetPlayer();

        // Find the software sale
        for ( int i = 0; i < cu->sw_sales.Size(); i++ ) {
            Sale *sale = cu->sw_sales.GetData(i);
            if ( !sale || strcmp(sale->title, title) != 0 ) continue;

            // Find requested version, or default to first real version
            double req_ver = extract_double(json, "version");

            SaleVersion *sv = NULL;
            if ( req_ver > 0 ) {
                // Find specific version
                for ( int v = 1; v < sale->versions.Size(); v++ ) {
                    SaleVersion *candidate = sale->versions.GetData(v);
                    if ( candidate && candidate->cost >= 0 &&
                         fabs((float)candidate->data - req_ver) < 0.01 ) {
                        sv = candidate;
                        break;
                    }
                }
            }
            if ( !sv ) {
                // Fallback: first real version
                for ( int v = 1; v < sale->versions.Size(); v++ ) {
                    sv = sale->versions.GetData(v);
                    if ( sv && sv->cost >= 0 ) break;
                    sv = NULL;
                }
            }
            if ( !sv ) continue;

            int cost = sv->cost;
            int balance = p->GetBalance();
            if ( balance < cost ) {
                send_response(client_fd,"error","insufficient funds");
                return;
            }

            // Create data object
            Data *newsw = new Data();
            newsw->SetTitle ( sale->title );
            newsw->SetDetails ( DATATYPE_PROGRAM, sv->size, 0, 0,
                                (float)sv->data, sale->swhwTYPE );

            if ( p->gateway.databank.PutData(newsw) ) {
                p->ChangeBalance ( -cost, "Software purchase" );
                char detail[128];
                snprintf(detail, sizeof(detail), "%s ($%d)", title, cost);
                send_response(client_fd, "ok", detail);
            } else {
                delete newsw;
                send_response(client_fd, "error", "no space on gateway");
            }
            return;
        }
        send_response(client_fd, "error", "software not found");
    }
    else if ( strcmp(cmd, "software_list") == 0 ) {
        // List available software for purchase
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        CompanyUplink *cu = (CompanyUplink*)game->GetWorld()->GetCompany("Uplink");
        if ( !cu ) { send_response(client_fd,"error","no company"); return; }

        std::string s = "{\"type\":\"software_list\",\"software\":[";
        bool first = true;
        for ( int i = 0; i < cu->sw_sales.Size(); i++ ) {
            Sale *sale = cu->sw_sales.GetData(i);
            if ( !sale ) continue;
            // Version 0 is a dummy (-1,-1,-1), real versions start at index 1
            for ( int v = 1; v < sale->versions.Size(); v++ ) {
                SaleVersion *sv = sale->versions.GetData(v);
                if ( !sv || sv->cost < 0 ) continue;
                if ( !first ) s += ",";
                first = false;
                char buf[256];
                snprintf(buf, sizeof(buf),
                    "{\"title\":\"%s\",\"cost\":%d,\"size\":%d,\"version\":%.1f,\"type\":%d}",
                    json_escape(sale->title).c_str(), sv->cost, sv->size, (float)sv->data, sale->swhwTYPE);
                s += buf;
            }
        }
        s += "]}";
        send_line(client_fd, s);
    }

    // ---- Semantic: Gateway / Hardware ----

    else if ( strcmp(cmd, "gateway_info") == 0 ) {
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        Player *p = game->GetWorld()->GetPlayer();
        Gateway *gw = &p->gateway;
        GatewayDef *gd = gw->curgatewaydef;

        std::string s = "{\"type\":\"gateway_info\"";
        char buf[512];
        snprintf(buf, sizeof(buf),
            ",\"modemspeed\":%d,\"memorysize\":%d,\"nuked\":%s",
            gw->modemspeed, gw->memorysize, gw->nuked ? "true" : "false");
        s += buf;
        if ( gd ) {
            snprintf(buf, sizeof(buf),
                ",\"model\":\"%s\",\"cost\":%d,\"maxcpus\":%d,\"maxmemory\":%d,\"bandwidth\":%d",
                json_escape(gd->name).c_str(), gd->cost, gd->maxcpus, gd->maxmemory, gd->bandwidth);
            s += buf;
        }
        // List installed hardware
        s += ",\"hardware\":[";
        for ( int i = 0; i < gw->hardware.Size(); i++ ) {
            if ( i > 0 ) s += ",";
            s += "\"";
            s += json_escape(gw->hardware.GetData(i));
            s += "\"";
        }
        s += "]}";
        send_line(client_fd, s);
    }
    else if ( strcmp(cmd, "hardware_list") == 0 ) {
        // List hardware for sale
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        CompanyUplink *cu = (CompanyUplink*)game->GetWorld()->GetCompany("Uplink");
        if ( !cu ) { send_response(client_fd,"error","no company"); return; }

        std::string s = "{\"type\":\"hardware_list\",\"hardware\":[";
        bool first = true;
        for ( int i = 0; i < cu->hw_sales.Size(); i++ ) {
            Sale *sale = cu->hw_sales.GetData(i);
            if ( !sale ) continue;
            for ( int v = 1; v < sale->versions.Size(); v++ ) {
                SaleVersion *sv = sale->versions.GetData(v);
                if ( !sv || sv->cost < 0 ) continue;
                if ( !first ) s += ",";
                first = false;
                char buf[256];
                snprintf(buf, sizeof(buf),
                    "{\"title\":\"%s\",\"cost\":%d,\"size\":%d}",
                    json_escape(sale->title).c_str(), sv->cost, sv->size);
                s += buf;
            }
        }
        s += "]}";
        send_line(client_fd, s);
    }
    else if ( strcmp(cmd, "buy_hardware") == 0 ) {
        // Buy and install hardware upgrade
        // {"cmd":"buy_hardware","title":"CPU ( 60 Ghz )"}
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        char title[128];
        if ( !extract_str(json, "title", title, sizeof(title)) ) {
            send_response(client_fd,"error","missing title"); return;
        }
        CompanyUplink *cu = (CompanyUplink*)game->GetWorld()->GetCompany("Uplink");
        if ( !cu ) { send_response(client_fd,"error","no company"); return; }
        Player *p = game->GetWorld()->GetPlayer();

        for ( int i = 0; i < cu->hw_sales.Size(); i++ ) {
            Sale *sale = cu->hw_sales.GetData(i);
            if ( !sale || strcmp(sale->title, title) != 0 ) continue;
            SaleVersion *sv = NULL;
            for ( int v = 1; v < sale->versions.Size(); v++ ) {
                sv = sale->versions.GetData(v);
                if ( sv && sv->cost >= 0 ) break;
                sv = NULL;
            }
            if ( !sv ) continue;
            if ( p->GetBalance() < sv->cost ) {
                send_response(client_fd,"error","insufficient funds"); return;
            }
            p->gateway.GiveHardware ( (char*)title );
            p->ChangeBalance ( -sv->cost, "Hardware purchase" );
            char detail[128];
            snprintf(detail, sizeof(detail), "%s ($%d)", title, sv->cost);
            send_response(client_fd, "ok", detail);
            return;
        }
        send_response(client_fd, "error", "hardware not found");
    }

    // ---- Semantic: InterNIC Search ----

    else if ( strcmp(cmd, "search") == 0 ) {
        // Search for computers by name (like InterNIC)
        // {"cmd":"search","query":"LAN"} or {"cmd":"search"} for all listed
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        char query[128] = "";
        extract_str(json, "query", query, sizeof(query));

        DArray<VLocation*> *locs = game->GetWorld()->locations.ConvertToDArray();
        DArray<char*> *ips = game->GetWorld()->locations.ConvertIndexToDArray();

        std::string s = "{\"type\":\"search\",\"results\":[";
        bool first = true;
        int count = 0;
        for ( int i = 0; i < locs->Size() && count < 50; i++ ) {
            if ( !locs->ValidIndex(i) ) continue;
            VLocation *vl = locs->GetData(i);
            if ( !vl ) continue;

            Computer *comp = vl->GetComputer();
            if ( !comp ) continue;

            // Filter by query (search listed servers, or all if query matches)
            if ( query[0] ) {
                if ( !strstr(comp->name, query) && !strstr(ips->GetData(i), query) ) continue;
            } else {
                if ( !vl->listed ) continue;  // No query = only listed servers
            }

            if ( !first ) s += ",";
            first = false;
            char buf[256];
            snprintf(buf, sizeof(buf),
                "{\"ip\":\"%s\",\"name\":\"%s\",\"type\":%d}",
                json_escape(ips->GetData(i)).c_str(),
                json_escape(comp->name).c_str(),
                comp->GetOBJECTID());
            s += buf;
            count++;
        }
        s += "]}";
        delete locs;
        delete ips;
        send_line(client_fd, s);
    }

    // ---- Semantic: Multi-hop connect ----

    else if ( strcmp(cmd, "connect_bounce") == 0 ) {
        // Connect through bounce hops
        // {"cmd":"connect_bounce","target":"1.2.3.4","bounces":["5.6.7.8","9.10.11.12"]}
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        char target[64];
        if ( !extract_str(json, "target", target, sizeof(target)) ) {
            send_response(client_fd,"error","missing target"); return;
        }
        VLocation *targetVl = game->GetWorld()->GetVLocation(target);
        if ( !targetVl ) { send_response(client_fd,"error","unknown target"); return; }

        Player *p = game->GetWorld()->GetPlayer();
        p->GetConnection()->Disconnect();
        p->GetConnection()->Reset();
        p->GetConnection()->AddVLocation( p->localhost );

        // Parse bounces from the JSON manually
        // Look for "bounces":["ip1","ip2",...]
        const char *bp = strstr(json, "\"bounces\"");
        if ( bp ) {
            bp = strchr(bp, '[');
            if ( bp ) {
                bp++;
                char bounce_ip[64];
                while ( *bp ) {
                    while ( *bp == ' ' || *bp == ',' ) bp++;
                    if ( *bp == ']' ) break;
                    if ( *bp == '"' ) {
                        bp++;
                        int bi = 0;
                        while ( *bp && *bp != '"' && bi < 63 ) bounce_ip[bi++] = *bp++;
                        bounce_ip[bi] = '\0';
                        if ( *bp == '"' ) bp++;
                        if ( game->GetWorld()->GetVLocation(bounce_ip) )
                            p->GetConnection()->AddVLocation(bounce_ip);
                    } else break;
                }
            }
        }

        p->GetConnection()->AddVLocation(target);
        p->GetConnection()->Connect();
        p->SetRemoteHost(target);
        game->GetInterface()->GetRemoteInterface()->RunNewLocation();

        int hops = p->GetConnection()->GetSize();
        char detail[128];
        snprintf(detail, sizeof(detail), "%s (%d hops)", target, hops);
        send_response(client_fd, "ok", detail);
    }

    // ---- Semantic: Crack password (run password breaker) ----

    else if ( strcmp(cmd, "crack_password") == 0 ) {
        // Returns the admin credentials for the currently connected server.
        // In the real game, Password_Breaker software would animate this.
        // Here we just return the answer immediately (client can add animation).
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        Player *p = game->GetWorld()->GetPlayer();
        if ( !p->IsConnected() ) { send_response(client_fd,"error","not connected"); return; }

        VLocation *vl = game->GetWorld()->GetVLocation( p->remotehost );
        if ( !vl ) { send_response(client_fd,"error","no location"); return; }
        Computer *comp = vl->GetComputer();
        if ( !comp ) { send_response(client_fd,"error","no computer"); return; }

        // Look up all records with passwords
        std::string s = "{\"type\":\"credentials\",\"accounts\":[";
        bool first = true;

        for ( int i = 0; i < comp->recordbank.records.Size(); i++ ) {
            Record *rec = comp->recordbank.records.GetData(i);
            if ( !rec ) continue;

            char *name = rec->GetField ( RECORDBANK_NAME );
            char *pw = rec->GetField ( RECORDBANK_PASSWORD );
            char *sec = rec->GetField ( RECORDBANK_SECURITY );

            if ( name && pw ) {
                if ( !first ) s += ",";
                first = false;
                char buf[256];
                snprintf(buf, sizeof(buf),
                    "{\"name\":\"%s\",\"password\":\"%s\",\"security\":\"%s\"}",
                    json_escape(name).c_str(),
                    json_escape(pw).c_str(),
                    sec ? json_escape(sec).c_str() : "1" );
                s += buf;
            }
        }

        s += "]}";
        send_line(client_fd, s);
    }

    // ---- Semantic: Screen links (LinksScreen data) ----

    else if ( strcmp(cmd, "screen_links") == 0 ) {
        // Return links shown on the current LinksScreen
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        ComputerScreen *cs = game->GetInterface()->GetRemoteInterface()->GetComputerScreen();
        if ( !cs ) { send_response(client_fd,"error","no screen"); return; }

        std::string s = "{\"type\":\"screen_links\",\"links\":[";
        bool first = true;

        // Parse links from Eclipse buttons (linksscreen_link N)
        int nb = EclGetNumButtons();
        for ( int i = 0; i < nb; i++ ) {
            Button *b = EclGetButtonByIndex(i);
            if ( !b ) continue;
            if ( strncmp(b->name, "linksscreen_link ", 17) != 0 ) continue;
            if ( !b->caption || b->caption[0] == '\0' ) continue;

            // Caption format: "IP    SERVERNAME" or just text
            // Try to extract IP from the caption
            char cap[512];
            strncpy(cap, b->caption, sizeof(cap)-1);

            // The link button's tooltip often has the IP
            const char *ip = b->tooltip && b->tooltip[0] ? b->tooltip : "";
            const char *name = b->caption;

            if ( !first ) s += ",";
            first = false;
            char buf[512];
            snprintf(buf, sizeof(buf), "{\"ip\":\"%s\",\"name\":\"%s\"}",
                json_escape(ip).c_str(), json_escape(name).c_str());
            s += buf;
        }

        // Fallback: if LinksScreen is ALLLINKS type, also search world
        if ( first && cs->GetOBJECTID() == OID_LINKSSCREEN ) {
            // No buttons found — return all listed VLocations
            DArray<VLocation*> *locs = game->GetWorld()->locations.ConvertToDArray();
            DArray<char*> *ips = game->GetWorld()->locations.ConvertIndexToDArray();
            int count = 0;
            for ( int i = 0; i < locs->Size() && count < 100; i++ ) {
                if ( !locs->ValidIndex(i) ) continue;
                VLocation *vl = locs->GetData(i);
                if ( !vl || !vl->listed ) continue;
                Computer *comp = vl->GetComputer();
                if ( !comp ) continue;
                if ( !first ) s += ",";
                first = false;
                char buf[256];
                snprintf(buf, sizeof(buf), "{\"ip\":\"%s\",\"name\":\"%s\"}",
                    json_escape(ips->GetData(i)).c_str(),
                    json_escape(comp->name).c_str());
                s += buf;
                count++;
            }
            delete locs;
            delete ips;
        }

        s += "]}";
        send_line(client_fd, s);
    }

    // ---- Semantic: LAN ----

    else if ( strcmp(cmd, "lan_scan") == 0 ) {
        // List LAN systems on current computer
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        Player *p = game->GetWorld()->GetPlayer();
        VLocation *vl = game->GetWorld()->GetVLocation( p->remotehost );
        if ( !vl ) { send_response(client_fd,"error","not connected"); return; }
        Computer *comp = vl->GetComputer();
        if ( comp->GetOBJECTID() != OID_LANCOMPUTER ) {
            send_response(client_fd,"error","not a LAN computer"); return;
        }
        LanComputer *lan = (LanComputer*)comp;

        std::string s = "{\"type\":\"lan_scan\",\"systems\":[";
        for ( int i = 0; i < lan->systems.Size(); i++ ) {
            if ( !lan->systems.ValidIndex(i) ) continue;
            LanComputerSystem *sys = lan->systems.GetData(i);
            if ( !sys ) continue;
            if ( i > 0 ) s += ",";
            char buf[256];
            const char *typeName = "unknown";
            switch ( sys->TYPE ) {
                case 1: typeName = "Router"; break;
                case 2: typeName = "Hub"; break;
                case 4: typeName = "Terminal"; break;
                case 5: typeName = "MainServer"; break;
                case 6: typeName = "MailServer"; break;
                case 7: typeName = "FileServer"; break;
                case 8: typeName = "Authentication"; break;
                case 9: typeName = "Lock"; break;
                case 10: typeName = "IsolationBridge"; break;
                case 11: typeName = "Modem"; break;
                case 16: typeName = "LogServer"; break;
            }
            snprintf(buf, sizeof(buf),
                "{\"index\":%d,\"type\":%d,\"typeName\":\"%s\",\"x\":%d,\"y\":%d,"
                "\"security\":%d,\"visible\":%d,\"screenIndex\":%d}",
                i, sys->TYPE, typeName, sys->x, sys->y,
                sys->security, sys->visible, sys->screenIndex);
            s += buf;
        }
        s += "],\"links\":[";
        bool first = true;
        for ( int i = 0; i < lan->links.Size(); i++ ) {
            if ( !lan->links.ValidIndex(i) ) continue;
            LanComputerLink *link = lan->links.GetData(i);
            if ( !link ) continue;
            if ( !first ) s += ",";
            first = false;
            char buf[128];
            snprintf(buf, sizeof(buf),
                "{\"from\":%d,\"to\":%d,\"security\":%d}",
                link->from, link->to, link->security);
            s += buf;
        }
        s += "]}";
        send_line(client_fd, s);
    }

    // ---- Semantic: BBS (available missions) ----

    else if ( strcmp(cmd, "bbs") == 0 ) {
        // List available missions on the Uplink BBS
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        CompanyUplink *cu = (CompanyUplink*)game->GetWorld()->GetCompany("Uplink");
        if ( !cu ) { send_response(client_fd,"error","no Uplink company"); return; }

        Player *p = game->GetWorld()->GetPlayer();
        std::string s = "{\"type\":\"bbs\",\"missions\":[";
        bool first = true;
        for ( int i = 0; i < cu->missions.Size(); i++ ) {
            Mission *m = cu->missions.GetData(i);
            if ( !m ) continue;
            // Only show missions the player qualifies for
            if ( m->minuplinkrating > p->rating.uplinkrating ) continue;
            if ( !first ) s += ",";
            first = false;
            char buf[512];
            snprintf(buf, sizeof(buf),
                "{\"index\":%d,\"type\":%d,\"employer\":\"%s\",\"description\":\"%s\","
                "\"payment\":%d,\"difficulty\":%d,\"contact\":\"%s\"}",
                i, m->TYPE,
                json_escape(m->employer).c_str(),
                json_escape(m->description).c_str(),
                m->payment, m->difficulty,
                json_escape(m->contact).c_str());
            s += buf;
        }
        s += "]}";
        send_line ( client_fd, s );
    }
    else if ( strcmp(cmd, "accept_mission") == 0 ) {
        // Accept a BBS mission by index
        // {"cmd":"accept_mission","index":0}
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        int idx = extract_int(json, "index");
        CompanyUplink *cu = (CompanyUplink*)game->GetWorld()->GetCompany("Uplink");
        if ( !cu || idx < 0 || idx >= cu->missions.Size() ) {
            send_response(client_fd,"error","invalid index");
            return;
        }
        Mission *m = cu->missions.GetData(idx);
        if ( !m ) { send_response(client_fd,"error","mission not found"); return; }

        Player *p = game->GetWorld()->GetPlayer();
        p->GiveMission(m);
        // Give links from mission
        for ( int i = 0; i < m->links.Size(); i++ )
            p->GiveLink(m->links.GetData(i));
        // Give codes from mission
        DArray<char*> *ips = m->codes.ConvertIndexToDArray();
        DArray<char*> *codes = m->codes.ConvertToDArray();
        for ( int i = 0; i < ips->Size(); i++ ) {
            if ( ips->ValidIndex(i) )
                p->GiveCode(ips->GetData(i), codes->GetData(i));
        }
        delete ips;
        delete codes;

        cu->missions.RemoveData(idx);
        send_response(client_fd, "ok", m->description);
    }

    // ---- Semantic: Gateway files ----

    else if ( strcmp(cmd, "gateway_files") == 0 ) {
        // List files on player's gateway
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        Player *p = game->GetWorld()->GetPlayer();
        std::string s = "{\"type\":\"gateway_files\",\"files\":[";
        bool first = true;
        for ( int i = 0; i < p->gateway.databank.GetSize(); i++ ) {
            Data *d = p->gateway.databank.GetData(i);
            if ( !d ) continue;
            if ( !first ) s += ",";
            first = false;
            char buf[256];
            snprintf(buf, sizeof(buf),
                "{\"index\":%d,\"title\":\"%s\",\"size\":%d}",
                i, json_escape(d->title).c_str(), d->size);
            s += buf;
        }
        s += "]}";
        send_line ( client_fd, s );
    }

    else if ( strcmp(cmd, "delete_gateway_file") == 0 ) {
        // Delete a file from the player's gateway
        // {"cmd":"delete_gateway_file","title":"File_Copier"}
        if ( !game || !game->IsRunning() ) { send_response(client_fd,"error","no game"); return; }
        char title[256];
        if ( !extract_str(json, "title", title, sizeof(title)) ) {
            send_response(client_fd,"error","missing title"); return;
        }
        Player *p = game->GetWorld()->GetPlayer();
        for ( int i = 0; i < p->gateway.databank.GetSize(); i++ ) {
            Data *d = p->gateway.databank.GetData(i);
            if ( d && strcmp(d->title, title) == 0 ) {
                p->gateway.databank.RemoveData(i);
                send_response(client_fd, "ok", title);
                return;
            }
        }
        send_response(client_fd, "error", "file not found");
    }

    else if ( strcmp(cmd, "state") == 0 ) {
        // Immediate full state dump
        std::string state = serialize_state();
        send_line ( client_fd, state );
    }

    // Deactivate session after processing
    SessionDeactivate();
}

// ============================================================================
// State serializer
// ============================================================================

static std::string serialize_screen ()
{
    std::string s = "\"screen\":{";

    if ( !game || !game->IsRunning() ) {
        s += "\"type\":\"none\"}";
        return s;
    }

    RemoteInterface *ri = game->GetInterface()->GetRemoteInterface();
    ComputerScreen *cs = ri->GetComputerScreen();

    if ( !cs ) {
        s += "\"type\":\"none\"}";
        return s;
    }

    int oid = cs->GetOBJECTID();
    const char *typeName = "unknown";
    switch ( oid ) {
        case OID_MENUSCREEN:     typeName = "MenuScreen"; break;
        case OID_DIALOGSCREEN:   typeName = "DialogScreen"; break;
        case OID_PASSWORDSCREEN: typeName = "PasswordScreen"; break;
        case OID_LINKSSCREEN:    typeName = "LinksScreen"; break;
        case OID_GENERICSCREEN:  typeName = "GenericScreen"; break;
        case OID_MESSAGESCREEN:  typeName = "MessageScreen"; break;
        case OID_USERIDSCREEN:   typeName = "UserIDScreen"; break;
        case OID_LOGSCREEN:      typeName = "LogScreen"; break;
        case OID_BBSSCREEN:      typeName = "BBSScreen"; break;
        case OID_HIGHSECURITYSCREEN: typeName = "HighSecurityScreen"; break;
        case OID_DISCONNECTEDSCREEN: typeName = "DisconnectedScreen"; break;
        case 15: typeName = "LanScreen"; break;  // OID_LANCOMPUTER
    }

    char buf[256];
    snprintf ( buf, sizeof(buf),
        "\"type\":\"%s\",\"oid\":%d,\"maintitle\":\"%s\",\"subtitle\":\"%s\"",
        typeName, oid,
        json_escape(cs->maintitle).c_str(),
        json_escape(cs->subtitle).c_str() );
    s += buf;

    // Screen-specific data
    if ( oid == OID_MENUSCREEN ) {
        MenuScreen *ms = (MenuScreen*)cs;
        int n = ms->NumOptions();
        s += ",\"options\":[";
        for ( int i = 0; i < n; i++ ) {
            if ( i > 0 ) s += ",";
            snprintf ( buf, sizeof(buf),
                "{\"caption\":\"%s\",\"nextpage\":%d,\"security\":%d}",
                json_escape(ms->GetCaption(i)).c_str(),
                ms->GetNextPage(i),
                ms->GetSecurity(i) );
            s += buf;
        }
        s += "]";
    }
    else if ( oid == OID_HIGHSECURITYSCREEN ) {
        HighSecurityScreen *hs = (HighSecurityScreen*)cs;
        s += ",\"options\":[";
        for ( int i = 0; i < hs->systems.Size(); i++ ) {
            MenuScreenOption *opt = hs->systems.GetData(i);
            if ( !opt ) continue;
            if ( i > 0 ) s += ",";
            snprintf ( buf, sizeof(buf),
                "{\"caption\":\"%s\",\"nextpage\":%d,\"security\":0}",
                json_escape(opt->caption).c_str(),
                opt->nextpage );
            s += buf;
        }
        s += "]";
    }
    else if ( oid == OID_DIALOGSCREEN ) {
        DialogScreen *ds = (DialogScreen*)cs;
        s += ",\"widgets\":[";
        for ( int i = 0; i < ds->widgets.Size(); i++ ) {
            DialogScreenWidget *w = ds->widgets.GetData(i);
            if ( !w ) continue;
            if ( i > 0 ) s += ",";
            snprintf ( buf, sizeof(buf),
                "{\"name\":\"%s\",\"type\":%d,\"caption\":\"%s\",\"x\":%d,\"y\":%d,\"w\":%d,\"h\":%d}",
                json_escape(w->GetName()).c_str(),
                w->WIDGETTYPE,
                json_escape(w->GetCaption()).c_str(),
                w->x, w->y, w->width, w->height );
            s += buf;
        }
        s += "]";
    }

    s += "}";
    return s;
}

static std::string serialize_buttons ()
{
    std::string s = "\"buttons\":[";
    int n = EclGetNumButtons();
    bool first = true;
    for ( int i = 0; i < n; i++ ) {
        Button *b = EclGetButtonByIndex(i);
        if ( !b || b->x < 0 || b->y < 0 ) continue;
        if ( !first ) s += ",";
        first = false;

        char buf[512];
        snprintf ( buf, sizeof(buf),
            "{\"name\":\"%s\",\"caption\":\"%s\",\"x\":%d,\"y\":%d,\"w\":%d,\"h\":%d,\"tooltip\":\"%s\"}",
            json_escape(b->name).c_str(),
            json_escape(b->caption).c_str(),
            b->x, b->y, b->width, b->height,
            json_escape(b->tooltip).c_str() );
        s += buf;
    }
    s += "]";
    return s;
}

static std::string serialize_state ()
{
    std::string s = "{\"type\":\"state\"";

    // Date
    if ( game && game->IsRunning() ) {
        char *datestr = game->GetWorld()->date.GetLongString();
        char buf[256];
        snprintf ( buf, sizeof(buf), ",\"date\":\"%s\",\"speed\":%d",
            json_escape(datestr).c_str(), game->GameSpeed() );
        s += buf;
    }

    // Player
    if ( game && game->IsRunning() ) {
        Player *p = game->GetWorld()->GetPlayer();
        if ( p ) {
            char buf[512];
            // Note: 'local' is a macro for 'static' in this codebase
            snprintf ( buf, sizeof(buf),
                ",\"player\":{\"handle\":\"%s\",\"localhost\":\"%s\",\"remotehost\":\"%s\","
                "\"rating\":{\"uplink\":%d,\"neuromancer\":%d},"
                "\"connected\":%s}",
                json_escape(p->handle).c_str(),
                json_escape(p->localhost).c_str(),
                json_escape(p->remotehost).c_str(),
                p->rating.uplinkrating,
                p->rating.neuromancerrating,
                p->IsConnected() ? "true" : "false" );
            s += buf;

            // Connection nodes
            s += ",\"connection\":{\"nodes\":[";
            for ( int i = 0; i < p->connection.vlocations.Size(); i++ ) {
                if ( i > 0 ) s += ",";
                s += "\"";
                s += json_escape( p->connection.vlocations.GetData(i) );
                s += "\"";
            }
            snprintf ( buf, sizeof(buf),
                "],\"trace_active\":%s,\"trace_progress\":%d}",
                p->connection.traceinprogress ? "true" : "false",
                p->connection.traceprogress );
            s += buf;
        }
    }

    // Screen
    s += ",";
    s += serialize_screen();

    // Buttons
    s += ",";
    s += serialize_buttons();

    s += "}";
    return s;
}

// ============================================================================
// Public API
// ============================================================================

bool HeadlessServer::Initialise ( int port )
{
    listen_fd = socket ( AF_INET, SOCK_STREAM, 0 );
    if ( listen_fd < 0 ) {
        printf ( "HeadlessServer: socket() failed: %s\n", strerror(errno) );
        return false;
    }

    int opt = 1;
    setsockopt ( listen_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt) );

    struct sockaddr_in addr;
    memset ( &addr, 0, sizeof(addr) );
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(port);

    if ( bind(listen_fd, (struct sockaddr*)&addr, sizeof(addr)) < 0 ) {
        printf ( "HeadlessServer: bind() failed: %s\n", strerror(errno) );
        close ( listen_fd );
        listen_fd = -1;
        return false;
    }

    if ( listen(listen_fd, 8) < 0 ) {
        printf ( "HeadlessServer: listen() failed: %s\n", strerror(errno) );
        close ( listen_fd );
        listen_fd = -1;
        return false;
    }

    set_nonblocking ( listen_fd );
    active = true;
    printf ( "HeadlessServer: Listening on port %d\n", port );
    return true;
}

void HeadlessServer::Shutdown ()
{
    for ( auto &c : clients )
        close ( c.fd );
    clients.clear();
    if ( listen_fd >= 0 ) close ( listen_fd );
    listen_fd = -1;
    active = false;
}

bool HeadlessServer::IsActive ()
{
    return active;
}

void HeadlessServer::Tick ()
{
    if ( !active ) return;

    // Accept new connections
    while ( true ) {
        struct sockaddr_in caddr;
        socklen_t clen = sizeof(caddr);
        int cfd = accept ( listen_fd, (struct sockaddr*)&caddr, &clen );
        if ( cfd < 0 ) break;
        set_nonblocking ( cfd );
        clients.push_back ( { cfd, "", NULL } );
        printf ( "HeadlessServer: Client connected (fd %d), total %zu\n",
                 cfd, clients.size() );
    }

    // Read from each client
    char buf[4096];
    for ( int ci = clients.size() - 1; ci >= 0; ci-- ) {
        int n = recv ( clients[ci].fd, buf, sizeof(buf) - 1, 0 );
        if ( n == 0 ) {
            // Client disconnected — save session if active
            printf ( "HeadlessServer: Client disconnected (fd %d)\n", clients[ci].fd );
            if ( clients[ci].session ) {
                SessionSave ( clients[ci].session );
                SessionDestroy ( clients[ci].session );
            }
            close ( clients[ci].fd );
            clients.erase ( clients.begin() + ci );
            continue;
        }
        if ( n < 0 ) {
            if ( errno == EAGAIN || errno == EWOULDBLOCK ) continue;
            // Error
            close ( clients[ci].fd );
            clients.erase ( clients.begin() + ci );
            continue;
        }

        buf[n] = '\0';
        clients[ci].readbuf += buf;

        // Process complete lines
        size_t pos;
        while ( (pos = clients[ci].readbuf.find('\n')) != std::string::npos ) {
            std::string line = clients[ci].readbuf.substr ( 0, pos );
            clients[ci].readbuf.erase ( 0, pos + 1 );
            if ( !line.empty() ) {
                handle_command ( line.c_str(), &clients[ci] );
            }
        }
    }
}

void HeadlessServer::UpdateSessions ()
{
    if ( !active ) return;

    // Global world update first (date, scheduler, shared computers)
    // Run with FIRST session active so GetPlayer() works for NPC mail processing
    bool worldUpdated = false;

    for ( auto &c : clients ) {
        if ( !c.session ) continue;
        SessionActivate ( c.session );

        // Run world update once (with this session's player active)
        if ( !worldUpdated && game && game->IsRunning() ) {
            game->GetWorld()->Update();
            worldUpdated = true;
        }

        // Per-session player update (trace, security monitors)
        g_headless_player_update_allowed = true;
        game->GetWorld()->GetPlayer()->Update();
        g_headless_player_update_allowed = false;

        // Per-session interface updates
        game->GetInterface()->GetRemoteInterface()->Update();
        game->GetInterface()->GetTaskManager()->Update();

        SessionDeactivate();
    }

    // If no sessions, still update world
    if ( !worldUpdated && game && game->IsRunning() )
        game->GetWorld()->Update();
}

static int broadcast_counter = 0;

void HeadlessServer::BroadcastState ()
{
    if ( !active || clients.empty() ) return;

    // Only broadcast every 40 ticks (~2 seconds at 20 tps)
    broadcast_counter++;
    if ( broadcast_counter < 40 ) return;
    broadcast_counter = 0;

    // Per-session state broadcast
    for ( auto &c : clients ) {
        if ( !c.session ) continue;
        SessionActivate ( c.session );
        std::string state = serialize_state();
        send_line ( c.fd, state );
        SessionDeactivate();
    }
}
