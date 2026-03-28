#ifndef _included_player_session_h
#define _included_player_session_h

class Player;
class RemoteInterface;
class TaskManager;

struct PlayerSession {
    int  session_id;
    char handle[128];
    Player          *player;
    RemoteInterface *ri;
    TaskManager     *tm;
};

// Create a new session: new Player + RemoteInterface + TaskManager
// The World must already exist (game->NewGame() called).
PlayerSession *SessionCreate ( const char *handle, const char *password );

// Swap this session into the global singletons (game, Interface, World)
void SessionActivate ( PlayerSession *session );

// Swap out the active session, clean up Eclipse buttons
void SessionDeactivate ();

// Destroy session and free all owned objects
void SessionDestroy ( PlayerSession *session );

// Save session to disk (call on disconnect)
bool SessionSave ( PlayerSession *session );

// Load a previously saved session (returns NULL if no save exists)
PlayerSession *SessionLoad ( const char *handle );

// Currently active session (NULL if none)
PlayerSession *GetActiveSession ();

#endif
