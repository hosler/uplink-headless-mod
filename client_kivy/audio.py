"""Audio module — SFX via Kivy SoundLoader + music via mikmod PCM -> temp wav."""
import os
import random
import wave
import tempfile
import threading

SFX_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "game", "uplinkHD", "sounds")
MUSIC_DIR = "/tmp/uplinkos/music/"

_sfx = {}
_playlist = []
_playlist_idx = 0
_current_music = None
_music_enabled = True

try:
    import mikmodplayer
    _has_mikmod = True
except ImportError:
    _has_mikmod = False
    print("Audio: mikmodplayer not available — install with: cd client/mikmod_ext && pip install -e .")


def init():
    """Load SFX files."""
    global _playlist
    from kivy.core.audio import SoundLoader

    # Load SFX
    if os.path.isdir(SFX_DIR):
        count = 0
        for f in os.listdir(SFX_DIR):
            if f.endswith(".wav"):
                full = os.path.join(SFX_DIR, f)
                sound = SoundLoader.load(full)
                if sound:
                    sound.volume = 0.5
                    _sfx[f[:-4]] = sound
                    count += 1
        print(f"Audio: {count} sound effects loaded")

    # Build music playlist
    if os.path.isdir(MUSIC_DIR):
        tracks = [os.path.join(MUSIC_DIR, f) for f in os.listdir(MUSIC_DIR)
                  if f.endswith(".uni")]
        random.shuffle(tracks)
        _playlist = tracks
        print(f"Audio: {len(tracks)} music tracks")


def play_sfx(name):
    """Play a sound effect by name."""
    if name in _sfx:
        _sfx[name].play()


def play_music():
    """Start playing music from the playlist."""
    global _current_music
    if not _music_enabled or not _playlist or not _has_mikmod:
        return
    _render_and_play(_playlist[_playlist_idx])


def next_track():
    """Advance to the next track."""
    global _playlist_idx
    if not _playlist:
        return
    _playlist_idx = (_playlist_idx + 1) % len(_playlist)
    play_music()


def _render_and_play(path):
    """Render .uni to PCM in background thread, then play as .wav."""
    def _worker():
        global _current_music
        try:
            from kivy.core.audio import SoundLoader
            from kivy.clock import Clock

            name = os.path.basename(path)
            print(f"Audio: Rendering {name}...")
            pcm = mikmodplayer.render(path, seconds=180)
            print(f"Audio: Rendered {len(pcm)} bytes")

            # Write to temp wav
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            with wave.open(tmp.name, 'wb') as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(44100)
                wf.writeframes(pcm)

            def _play(dt):
                global _current_music
                if _current_music:
                    _current_music.stop()
                sound = SoundLoader.load(tmp.name)
                if sound:
                    sound.volume = 0.4
                    sound.bind(on_stop=lambda *_: _on_track_end())
                    sound.play()
                    _current_music = sound
                    title = mikmodplayer.get_title(path) or name
                    print(f"Audio: Playing '{title}'")

            Clock.schedule_once(_play, 0)
        except Exception as e:
            print(f"Audio: playback failed: {e}")

    threading.Thread(target=_worker, daemon=True).start()


def _on_track_end():
    """Called when a track finishes."""
    from kivy.clock import Clock
    Clock.schedule_once(lambda dt: next_track(), 0.5)


def set_music_volume(vol):
    if _current_music:
        _current_music.volume = max(0.0, min(1.0, vol))


def set_sfx_volume(vol):
    for s in _sfx.values():
        s.volume = max(0.0, min(1.0, vol))
