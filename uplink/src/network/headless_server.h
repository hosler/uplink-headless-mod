#ifndef _included_headless_server_h
#define _included_headless_server_h

extern bool g_headless;
extern int  g_headless_port;

namespace HeadlessServer {
    bool Initialise ( int port );
    void Shutdown ();
    void Tick ();               // Accept connections, read commands
    void UpdateSessions ();     // Per-session game updates + global world update
    void BroadcastState ();     // Per-session state broadcast
    bool IsActive ();
}

#endif
