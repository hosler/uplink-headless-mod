"""Music playlist (.uni tracker via mikmodplayer C extension) + SFX (.wav)."""
import os
import random
import pygame

MUSIC_DIR = "/tmp/uplinkos/music/"
SFX_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "game/uplinkHD/sounds/")

MUSIC_END_EVENT = pygame.USEREVENT + 1

_playlist: list[str] = []
_playlist_idx: int = 0
_sfx: dict[str, pygame.mixer.Sound] = {}
_music_enabled = True
_current_sound: pygame.mixer.Sound | None = None
_music_channel: pygame.mixer.Channel | None = None

try:
    import mikmodplayer
    _has_mikmod = True
except ImportError:
    _has_mikmod = False
    print("Audio: mikmodplayer not available — install with: cd client/mikmod_ext && pip install -e .")


def init():
    global _playlist, _music_enabled, _music_channel
    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
        # Reserve channel 0 for music
        pygame.mixer.set_num_channels(16)
        _music_channel = pygame.mixer.Channel(0)
    except Exception as e:
        print(f"Audio: mixer init failed: {e}")
        _music_enabled = False
        return

    # Build music playlist
    if os.path.isdir(MUSIC_DIR):
        tracks = [os.path.join(MUSIC_DIR, f) for f in os.listdir(MUSIC_DIR)
                  if f.endswith(".uni")]
        random.shuffle(tracks)
        _playlist = tracks
        if _has_mikmod:
            for t in tracks:
                title = mikmodplayer.get_title(t)
                name = os.path.basename(t)
                print(f"  {name}: {title}")
        print(f"Audio: {len(tracks)} music tracks")

    # Load SFX
    if os.path.isdir(SFX_DIR):
        for f in os.listdir(SFX_DIR):
            full = os.path.join(SFX_DIR, f)
            if f.endswith(".wav") and os.path.isfile(full):
                name = f[:-4]
                try:
                    _sfx[name] = pygame.mixer.Sound(full)
                    _sfx[name].set_volume(0.5)
                except Exception:
                    pass
        print(f"Audio: {len(_sfx)} sound effects")


def play_music():
    global _current_sound
    if not _music_enabled or not _playlist:
        print(f"Audio: play_music skipped (enabled={_music_enabled}, tracks={len(_playlist)})")
        return
    if not _has_mikmod:
        print("Audio: play_music skipped (no mikmodplayer)")
        return
    if not _music_channel:
        print("Audio: play_music skipped (no channel)")
        return
    try:
        path = _playlist[_playlist_idx]
        name = os.path.basename(path)
        print(f"Audio: Rendering {name}...")
        pcm = mikmodplayer.render(path, seconds=180)
        print(f"Audio: Rendered {len(pcm)} bytes")
        _current_sound = pygame.mixer.Sound(buffer=pcm)
        _current_sound.set_volume(0.4)
        _music_channel.play(_current_sound)
        _music_channel.set_endevent(MUSIC_END_EVENT)
        title = mikmodplayer.get_title(path) or name
        print(f"Audio: Playing '{title}'")
    except Exception as e:
        print(f"Audio: playback failed: {e}")


def next_track():
    global _playlist_idx
    if not _playlist:
        return
    _playlist_idx = (_playlist_idx + 1) % len(_playlist)
    play_music()


def play_sfx(name: str):
    if name in _sfx:
        _sfx[name].play()


def set_music_volume(vol: float):
    if _current_sound:
        _current_sound.set_volume(max(0.0, min(1.0, vol)))


def set_sfx_volume(vol: float):
    for s in _sfx.values():
        s.set_volume(max(0.0, min(1.0, vol)))
