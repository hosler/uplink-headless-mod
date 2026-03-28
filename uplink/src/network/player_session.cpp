#include "stdafx.h"

#include <stdio.h>
#include <string.h>

#include "eclipse.h"

#include "app/app.h"
#include "app/globals.h"
#include "app/serialise.h"

#include "options/options.h"

#include "game/game.h"
#include "game/data/data.h"
#include "app/miscutils.h"

#include "interface/interface.h"
#include "interface/remoteinterface/remoteinterface.h"
#include "interface/taskmanager/taskmanager.h"

#include "world/world.h"
#include "world/player.h"
#include "world/computer/computer.h"
#include "world/computer/recordbank.h"
#include "world/computer/gateway.h"
#include "world/generator/namegenerator.h"
#include "world/generator/worldgenerator.h"
#include "world/generator/recordgenerator.h"

#include "world/company/mission.h"
#include "world/generator/missiongenerator.h"
#include "world/message.h"

#include "network/player_session.h"

#include "mmgr.h"

// ============================================================================
// Static state
// ============================================================================

static PlayerSession *s_active = NULL;
static RemoteInterface *s_saved_ri = NULL;
static TaskManager *s_saved_tm = NULL;
static int s_next_id = 1;

// ============================================================================

PlayerSession *SessionCreate ( const char *handle, const char *password )
{
    printf ( "SessionCreate: Creating session for '%s'\n", handle );

    PlayerSession *session = new PlayerSession();
    session->session_id = s_next_id++;
    strncpy ( session->handle, handle, sizeof(session->handle) - 1 );
    session->handle[sizeof(session->handle) - 1] = '\0';

    // Create player object (replicates headless_newgame / WorldGenerator::GeneratePlayer)
    Player *player = new Player();
    player->SetName ( "PLAYER" );  // Must be "PLAYER" for BTree key compatibility
    player->SetHandle ( (char*)handle );
    player->SetAge ( 21 + (rand() % 20) );
    player->SetPhotoIndex ( 0 );
    player->SetLocalHost ( "127.0.0.1" );  // Gateway IP
    player->SetRemoteHost ( "127.0.0.1" );

    // Initialize gateway
    player->gateway.GiveStartingHardware ();
    player->gateway.GiveStartingSoftware ();

    session->player = player;

    // Create per-session Interface components
    session->ri = new RemoteInterface();
    session->tm = new TaskManager();

    // Now activate this session temporarily to run player initialization
    // that depends on GetPlayer() returning the right player
    SessionActivate ( session );

    // Generate access code
    char accesscode[256];
    Computer::GenerateAccessCode ( (char*)handle, (char*)password,
                                   accesscode, sizeof(accesscode) );

    // Open bank account
    Computer *bank = game->GetWorld()->GetComputer (
        NameGenerator::GenerateInternationalBankName("Uplink") );
    if ( bank ) {
        int accno = player->CreateNewAccount (
            bank->ip, (char*)handle, (char*)password, 0, PLAYER_START_BALANCE );
        player->GiveLink ( bank->ip );

        // Store player record on Uplink's computer
        Record *record = new Record();
        char accnoStr[16];
        snprintf ( accnoStr, sizeof(accnoStr), "%d", accno );
        record->AddField ( RECORDBANK_NAME, (char*)handle );
        record->AddField ( RECORDBANK_ACCNO, accnoStr );
        record->AddField ( RECORDBANK_PASSWORD, (char*)password );
        record->AddField ( RECORDBANK_SECURITY, "5" );
        record->AddField ( "Created", game->GetWorld()->date.GetLongString() );
        Computer *uplinkComp = game->GetWorld()->GetComputer ( NAME_UPLINKINTERNALSERVICES );
        if ( uplinkComp )
            uplinkComp->recordbank.AddRecord ( record );
    }

    // Generate records
    RecordGenerator::GenerateRecords_Player ( (char*)handle );

    // Set beginner rating and give standard links
    player->rating.SetUplinkRating ( 1 );
    player->GiveLink ( "458.615.48.651" );   // InterNIC
    player->GiveLink ( "234.773.0.666" );    // Uplink Public Access Server

    // Give test mission
    Mission *mission = new Mission();
    mission->SetTYPE ( MISSION_STEALFILE );
    mission->SetCompletion ( IP_UPLINKINTERNALSERVICES, "Uplink test data", NULL, NULL, NULL );
    mission->SetEmployer ( "Uplink" );
    mission->SetContact ( "internal@Uplink.net" );
    mission->SetPayment ( 500 );
    mission->SetDifficulty ( 1 );
    mission->SetDescription ( "Uplink Test Mission -\nSteal data from a file server" );
    mission->SetFullDetails (
        "Gain access to the Uplink Test Machine by breaking the outer security layer.\n"
        "Access the fileserver and download the target file 'Uplink Test Data'.\n"
        "Remove any traces of your hack.\n"
        "Return the data to us at address internal@Uplink.net" );
    mission->GiveLink ( IP_UPLINKTESTMACHINE );
    player->GiveMission ( mission );
    player->GiveLink ( IP_UPLINKTESTMACHINE );

    // Mark first time done
    app->GetOptions()->SetOptionValue ( "game_firsttime", 0 );

    // Set up player connection to gateway
    player->GetConnection()->Reset();
    player->GetConnection()->AddVLocation ( player->localhost );
    player->GetConnection()->Connect();
    player->SetRemoteHost ( player->localhost );

    // Show gateway's first screen (screen 6 = welcome dialog)
    game->GetInterface()->GetRemoteInterface()->RunNewLocation();
    game->GetInterface()->GetRemoteInterface()->RunScreen ( 6 );

    SessionDeactivate();

    printf ( "SessionCreate: Session %d created for '%s'\n",
             session->session_id, handle );
    return session;
}

void SessionActivate ( PlayerSession *session )
{
    if ( !session ) return;
    if ( s_active == session ) return;
    if ( s_active ) SessionDeactivate();

    // Swap player into World's "PLAYER" BTree slot
    game->GetWorld()->SwapPlayer ( session->player );

    // Swap RemoteInterface and TaskManager into the global Interface
    game->GetInterface()->SwapRemoteInterface ( session->ri, &s_saved_ri );
    game->GetInterface()->SwapTaskManager ( session->tm, &s_saved_tm );

    s_active = session;

    // Rebuild Eclipse buttons for this session's current screen
    // Save previousscreenindex because RunScreen overwrites it
    RemoteInterface *ri = game->GetInterface()->GetRemoteInterface();
    if ( ri && !ri->HasScreen() && ri->currentscreenindex >= 0 ) {
        int saved_prev = ri->previousscreenindex;
        ri->RunScreen ( ri->currentscreenindex, NULL );
        ri->previousscreenindex = saved_prev;
    }
}

void SessionDeactivate ()
{
    if ( !s_active ) return;

    // Clean up Eclipse buttons from this session's screen
    RemoteInterface *ri = game->GetInterface()->GetRemoteInterface();
    if ( ri ) ri->ClearScreen();

    // Restore saved ri/tm
    RemoteInterface *dummy_ri = NULL;
    TaskManager *dummy_tm = NULL;
    game->GetInterface()->SwapRemoteInterface ( s_saved_ri, &dummy_ri );
    game->GetInterface()->SwapTaskManager ( s_saved_tm, &dummy_tm );
    s_saved_ri = NULL;
    s_saved_tm = NULL;

    s_active = NULL;
}

PlayerSession *GetActiveSession ()
{
    return s_active;
}

void SessionDestroy ( PlayerSession *session )
{
    if ( !session ) return;
    if ( s_active == session ) SessionDeactivate();

    printf ( "SessionDestroy: Destroying session %d ('%s')\n",
             session->session_id, session->handle );

    if ( session->ri ) delete session->ri;
    if ( session->tm ) delete session->tm;
    session->ri = NULL;
    session->tm = NULL;
    session->player = NULL;

    delete session;
}

static void get_save_path ( const char *handle, char *path, int pathsize )
{
    snprintf ( path, pathsize, "%ssessions/%s.sav", app->userpath, handle );
}

bool SessionSave ( PlayerSession *session )
{
    if ( !session || !session->player ) return false;

    // Ensure sessions directory exists
    char dirpath[512];
    snprintf ( dirpath, sizeof(dirpath), "%ssessions/", app->userpath );
    MakeDirectory ( dirpath );

    char path[512];
    get_save_path ( session->handle, path, sizeof(path) );

    FILE *file = fopen ( path, "wb" );
    if ( !file ) {
        printf ( "SessionSave: Failed to open %s\n", path );
        return false;
    }

    // Save player state
    session->player->Save ( file );

    // Save remote interface state (screen index, security)
    if ( session->ri ) {
        session->ri->Save ( file );
    }

    fclose ( file );
    printf ( "SessionSave: Saved '%s' to %s\n", session->handle, path );
    return true;
}

PlayerSession *SessionLoad ( const char *handle )
{
    char path[512];
    get_save_path ( handle, path, sizeof(path) );

    FILE *file = fopen ( path, "rb" );
    if ( !file ) return NULL;  // No save exists

    printf ( "SessionLoad: Loading '%s' from %s\n", handle, path );

    // Create session shell
    PlayerSession *session = new PlayerSession();
    session->session_id = s_next_id++;
    strncpy ( session->handle, handle, sizeof(session->handle) - 1 );

    // Load player
    Player *player = new Player();
    if ( !player->Load(file) ) {
        printf ( "SessionLoad: Failed to load player data\n" );
        delete player;
        delete session;
        fclose(file);
        return NULL;
    }
    session->player = player;

    // Load remote interface state
    session->ri = new RemoteInterface();
    session->ri->Load(file);

    session->tm = new TaskManager();

    fclose(file);

    printf ( "SessionLoad: Loaded '%s' (rating=%d, screen=%d)\n",
             handle, player->rating.uplinkrating, session->ri->currentscreenindex );
    return session;
}
