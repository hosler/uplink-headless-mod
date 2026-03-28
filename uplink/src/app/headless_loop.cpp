#include "stdafx.h"

#include <sys/time.h>
#include <unistd.h>

#include "eclipse.h"

#include "app/app.h"
#include "app/globals.h"
#include "app/serialise.h"
#include "app/headless_loop.h"
#include "network/headless_server.h"

#include "options/options.h"

#include "game/game.h"
#include "game/data/data.h"

#include "interface/interface.h"
#include "interface/localinterface/localinterface.h"
#include "interface/remoteinterface/remoteinterface.h"

#include "world/world.h"
#include "world/player.h"
#include "world/computer/computer.h"
#include "world/computer/recordbank.h"
#include "world/generator/namegenerator.h"
#include "world/generator/worldgenerator.h"
#include "world/generator/recordgenerator.h"
#include "world/scheduler/notificationevent.h"

#include "mmgr.h"

static unsigned long headless_get_time_ms ()
{
    struct timeval tv;
    gettimeofday ( &tv, NULL );
    static struct timeval start = tv;
    long diff_sec  = tv.tv_sec  - start.tv_sec;
    long diff_usec = tv.tv_usec - start.tv_usec;
    if ( diff_usec < 0 ) { diff_usec += 1000000; diff_sec--; }
    return (unsigned long)(1000 * diff_sec + diff_usec / 1000);
}

void headless_initialise ()
{
    // Set virtual screen dimensions so code that divides by screen size doesn't SIGFPE
    app->GetOptions()->SetOptionValue ( "graphics_screenwidth", 1024 );
    app->GetOptions()->SetOptionValue ( "graphics_screenheight", 768 );
    app->GetOptions()->SetOptionValue ( "graphics_screendepth", 32 );
    app->GetOptions()->SetOptionValue ( "graphics_screenrefresh", 60 );

    // Initialize Eclipse with matching virtual screen size
    EclReset ( 1024, 768 );
    printf ( "Headless: Eclipse initialised (virtual 1024x768)\n" );
}

// Create a new game directly, skipping the intro wizard entirely.
// Replicates the logic from FirstTimeLoadingInterface::HD_LoadingComplete()
void headless_newgame ( const char *username, const char *password )
{
    printf ( "Headless: Creating new game for '%s'\n", username );

    game->NewGame();

    // Generate access code
    char accesscode[256];
    Computer::GenerateAccessCode ( (char*)username, (char*)password,
                                   accesscode, sizeof(accesscode) );

    // Set player handle
    game->GetWorld()->GetPlayer()->SetHandle ( (char*)username );

    // Open bank account
    Computer *bank = game->GetWorld()->GetComputer (
        NameGenerator::GenerateInternationalBankName("Uplink") );
    if ( bank ) {
        int accno = game->GetWorld()->GetPlayer()->CreateNewAccount (
            bank->ip, (char*)username, (char*)password, 0, PLAYER_START_BALANCE );
        game->GetWorld()->GetPlayer()->GiveLink ( bank->ip );

        // Store player record
        Record *record = new Record();
        char accnoStr[16];
        snprintf ( accnoStr, sizeof(accnoStr), "%d", accno );
        record->AddField ( RECORDBANK_NAME, (char*)username );
        record->AddField ( RECORDBANK_ACCNO, accnoStr );
        record->AddField ( RECORDBANK_PASSWORD, (char*)password );
        record->AddField ( RECORDBANK_SECURITY, "5" );
        record->AddField ( "Created", game->GetWorld()->date.GetLongString() );
        Computer *uplinkComp = game->GetWorld()->GetComputer ( NAME_UPLINKINTERNALSERVICES );
        if ( uplinkComp )
            uplinkComp->recordbank.AddRecord ( record );
    }

    // Generate records
    RecordGenerator::GenerateRecords_Player ( (char*)username );

    // Set beginner rating
    game->GetWorld()->GetPlayer()->rating.SetUplinkRating ( 1 );

    // Skip HUD creation in headless mode — it requires OpenGL for font metrics.
    // The local interface (HUD) is purely visual; game logic works without it.

    // Mark first time done
    app->GetOptions()->SetOptionValue ( "game_firsttime", 0 );

    // Connect to gateway
    game->GetWorld()->GetPlayer()->GetConnection()->Disconnect();
    game->GetWorld()->GetPlayer()->GetConnection()->Reset();
    game->GetInterface()->GetRemoteInterface()->RunNewLocation();
    game->GetInterface()->GetRemoteInterface()->RunScreen ( 6 );

    printf ( "Headless: Game created. Player '%s' connected to gateway.\n", username );
}

void headless_run ()
{
    printf ( "Headless: Creating world...\n" );

    // Create the game world with a default player
    // Sessions will create additional players via "join" command
    game->NewGame();
    game->SetGameSpeed ( GAMESPEED_NORMAL );
    printf ( "Headless: World created. Waiting for clients to join.\n" );

    printf ( "Headless: Entering main loop\n" );

    unsigned long tick_period_ms = 1000 / 20;  // 20 ticks per second

    while ( !app->Closed() ) {
        unsigned long tick_start = headless_get_time_ms();

        // Process network commands per-session (with context switching)
        HeadlessServer::Tick();

        // Per-session game logic + global world update
        HeadlessServer::UpdateSessions();

        // Per-session state broadcast
        HeadlessServer::BroadcastState();

        // Rate limit
        unsigned long elapsed = headless_get_time_ms() - tick_start;
        if ( elapsed < tick_period_ms ) {
            usleep ( (tick_period_ms - elapsed) * 1000 );
        }
    }

    printf ( "Headless: Exiting main loop\n" );
}

void headless_close ()
{
    HeadlessServer::Shutdown();
}
