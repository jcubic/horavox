# Copyright (C) 2026 Jakub T. Jankiewicz <https://jakub.jankiewicz.org/>
#
# This file is part of HoraVox.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
"""HoraVox shared library — paths, logging, language, TTS, voice, session management."""

import contextlib
import datetime
import json
import locale
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import traceback

from voxkit import VoiceManager
from voxkit.tts import play_mp3, play_wav, scale_volume, synthesize, synthesize_multi

__version__ = "0.6.1"

# ================== PATHS ==================
# Package data (ships with the package, read-only)
PKG_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PKG_DIR, "data")
LANG_DIR = os.path.join(DATA_DIR, "lang")
BLANK_MP3 = os.path.join(DATA_DIR, "blank.mp3")
BEEP_MP3 = os.path.join(DATA_DIR, "beep.mp3")

# User data (writable, created at runtime)
USER_DIR = os.path.expanduser("~/.horavox")
CACHE_DIR = os.path.join(USER_DIR, "cache")
SESSIONS_DIR = os.path.join(USER_DIR, "sessions")
SLEEP_FILE = os.path.join(USER_DIR, "sleep.json")
WAKEUP_FILE = os.path.join(USER_DIR, "wakeup.json")
LEGACY_VOICES_DIR = os.path.join(USER_DIR, "voices")

TEMP_WAV = f"/tmp/horavox-{os.getpid()}.wav"
LOG_FILE = os.path.join(USER_DIR, "horavox.log")

_vm = None


def _migrate_legacy_voices(models_dir):
    """Move voice files from legacy voices/ to models/ directory."""
    if not os.path.isdir(LEGACY_VOICES_DIR):
        return
    for name in os.listdir(LEGACY_VOICES_DIR):
        src = os.path.join(LEGACY_VOICES_DIR, name)
        dst = os.path.join(models_dir, name)
        if os.path.isfile(src) and not os.path.exists(dst):
            try:
                shutil.move(src, dst)
            except OSError:  # pragma: no cover
                log_to_file(f"Failed to migrate voice file: {name}")
    try:
        if not os.listdir(LEGACY_VOICES_DIR):
            os.rmdir(LEGACY_VOICES_DIR)
    except OSError:  # pragma: no cover
        pass


def get_voice_manager():
    """Return the shared VoiceManager instance (lazy init)."""
    global _vm
    if _vm is None:
        _vm = VoiceManager(
            data_dir=USER_DIR,
            catalog_url=os.environ.get("HORAVOX_VOICES_JSON_URL"),
            base_url=os.environ.get("HORAVOX_VOICES_BASE_URL"),
        )
        _migrate_legacy_voices(_vm.voices_dir)
    return _vm


# ============================================

VERBOSE = False
NOSOUND = False
VOLUME = 100


def configure(verbose=False, nosound=False, volume=100, debug=False):
    """Set global audio/logging flags. Call from each subcommand's main()."""
    global VERBOSE, NOSOUND, VOLUME
    if debug:
        verbose = True
        nosound = True
    VERBOSE = verbose
    if not 0 <= volume <= 100:
        print(f"Error: --volume must be 0-100, got {volume}")
        sys.exit(1)
    VOLUME = volume
    if nosound:
        VOLUME = 0
    NOSOUND = nosound or VOLUME == 0


# ==================== LOGGING ====================


def log(msg):
    """Print a message only when --verbose is enabled."""
    if VERBOSE:
        print(msg)


def log_to_file(message):
    """Append a timestamped message to ~/.horavox.log."""
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except OSError:
        pass


def log_spoken(text):
    """Append a spoken-words entry to ~/.horavox.log."""
    log_to_file(text)


def log_error():
    """Append the current exception traceback to ~/.horavox.log."""
    log_to_file(traceback.format_exc().rstrip())


# ==================== LANGUAGE ====================


def detect_language():
    """Detect language from system locale, return 2-letter code."""
    try:
        loc = locale.getlocale()[0]  # e.g. "pl_PL", "en_US"
        if loc and len(loc) >= 2:
            return loc.split("_")[0]
    except Exception:
        pass
    return "en"


def load_language_data(lang, mode="classic"):
    """Load language JSON data. Falls back to English if not found."""
    lang_file = os.path.join(LANG_DIR, f"{lang}.json")
    if not os.path.exists(lang_file):
        if lang != "en":
            log(f"Warning: data/lang/{lang}.json not found, falling back to English.")
            lang_file = os.path.join(LANG_DIR, "en.json")
            lang = "en"
        else:
            print("Error: data/lang/en.json not found.")
            sys.exit(1)

    with open(lang_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extract mode-specific data if present
    if "classic" in data:
        if mode not in data:
            print(f"Error: mode '{mode}' not found in data/lang/{lang}.json.")
            sys.exit(1)
        data = data[mode]

    # Validate
    if len(data.get("hours", [])) != 24:
        print(f"Error: data/lang/{lang}.json 'hours' must have 24 entries.")
        sys.exit(1)

    # hours_alt defaults to hours if not provided
    if "hours_alt" not in data:
        data["hours_alt"] = data["hours"]
    elif len(data["hours_alt"]) != 24:
        print(f"Error: data/lang/{lang}.json 'hours_alt' must have 24 entries.")
        sys.exit(1)

    # Validate required patterns based on mode
    if "time" in data.get("patterns", {}):
        required_patterns = ["full_hour", "time"]
    else:
        required_patterns = [
            "full_hour",
            "quarter_past",
            "half_past",
            "quarter_to",
            "minutes_past",
            "minutes_to",
        ]
    for p in required_patterns:
        if p not in data.get("patterns", {}):
            print(f"Error: data/lang/{lang}.json missing pattern '{p}'.")
            sys.exit(1)

    return data, lang


def _load_lang_json(lang):
    """Load a whole language JSON file (English fallback, {} on error)."""
    lang_file = os.path.join(LANG_DIR, f"{lang}.json")
    if not os.path.exists(lang_file):
        lang_file = os.path.join(LANG_DIR, "en.json")
    try:
        with open(lang_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def load_messages(lang):
    """Load the top-level 'messages' dict for a language (English fallback)."""
    return _load_lang_json(lang).get("messages", {})


def load_durations(lang):
    """Load the top-level 'durations' dict for a language (English fallback)."""
    return _load_lang_json(lang).get("durations", {})


def get_message(lang, key, default=""):
    """Return a localized message string, falling back to English then default."""
    value = load_messages(lang).get(key)
    if value is None and lang != "en":
        value = load_messages("en").get(key)
    return value if value is not None else default


def plural_category(lang, n):
    """Return the plural category used for spoken durations (CLDR-style).

    'one' is handled by callers; this returns 'few'/'many' for Polish
    (2-4 excluding teens is 'few', otherwise 'many') and 'other' elsewhere.
    """
    if lang == "pl":
        if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
            return "few"
        return "many"
    return "other"


def _unit_phrase(durations, lang, unit, n):
    """Render a single '{number} {noun}' duration part with correct plural form."""
    forms = durations[unit]
    if n == 1:
        return forms["one"]
    noun = forms.get(plural_category(lang, n)) or forms.get("other") or forms.get("many", "")
    number = durations.get("numbers", {}).get(str(n), str(n))
    return f"{number} {noun}"


def spoken_duration(durations, lang, total_seconds):
    """Render a duration (seconds) as a spoken phrase using a durations dict.

    Decomposes into hours/minutes/seconds, drops zero parts, and joins the
    remaining parts with the language's 'join' connector.
    """
    hours, rem = divmod(int(total_seconds), 3600)
    minutes, seconds = divmod(rem, 60)
    parts = [
        _unit_phrase(durations, lang, unit, n)
        for unit, n in (("hour", hours), ("minute", minutes), ("second", seconds))
        if n
    ]
    return durations.get("join", " ").join(parts)


def get_spoken_time(lang_data, hour, minute):
    """Return spoken time string using language data patterns."""
    hours = lang_data["hours"]
    hours_alt = lang_data["hours_alt"]
    minutes_map = lang_data["minutes"]
    patterns = lang_data["patterns"]

    next_hour = (hour + 1) % 24

    next_hour_name = hours[next_hour]
    next_hour_alt_name = hours_alt[next_hour]
    if next_hour == 0:
        next_hour_name = lang_data.get("next_hour_midnight", next_hour_name)
        next_hour_alt_name = lang_data.get("next_hour_midnight_alt", next_hour_alt_name)

    def fill(pattern, minute_val=None):
        result = pattern
        result = result.replace("{hour}", hours[hour])
        result = result.replace("{hour_alt}", hours_alt[hour])
        result = result.replace("{next_hour}", next_hour_name)
        result = result.replace("{next_hour_alt}", next_hour_alt_name)
        if minute_val is not None and ("{minutes}" in result or "{remaining}" in result):
            minute_key = str(minute_val)
            word = minutes_map.get(minute_key, minute_key)
            result = result.replace("{minutes}", word)
            result = result.replace("{remaining}", word)
        return result

    if minute == 0:
        return fill(patterns["full_hour"])

    if "time" in patterns:
        return fill(patterns["time"], minute)

    if minute == 15:
        return fill(patterns["quarter_past"])
    elif minute == 30:
        return fill(patterns["half_past"])
    elif minute == 45:
        return fill(patterns["quarter_to"])
    elif minute < 30:
        return fill(patterns["minutes_past"], minute)
    else:
        return fill(patterns["minutes_to"], 60 - minute)


# ==================== VOICE MANAGEMENT ====================


def ensure_user_dirs():
    """Create ~/.horavox/ subdirectories for cache and sessions."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(SESSIONS_DIR, exist_ok=True)


def resolve_voice(voice_name, lang):
    """Resolve which voice to use. Downloads if needed. Returns .onnx path."""
    vm = get_voice_manager()
    try:
        return vm.resolve(voice=voice_name, lang=lang)
    except FileNotFoundError:
        print(f"No voice installed for language '{lang}'.")
        print(f"Run: vox voice --lang {lang} (then press 'i' to install)")
        print(f"Or list available voices: vox voice --list --lang {lang}")
        sys.exit(1)


@contextlib.contextmanager
def _suppressed_native_stderr():
    """Redirect the process stderr file descriptor (2) to /dev/null.

    Native libraries (e.g. onnxruntime) write directly to file descriptor 2,
    bypassing Python's ``sys.stderr`` and its log-severity settings, so we
    redirect the fd itself. Best-effort: if fd 2 can't be duplicated, do
    nothing.
    """
    stderr_fd = 2
    try:
        saved_fd = os.dup(stderr_fd)
    except OSError:
        yield
        return
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    try:
        sys.stderr.flush()
        os.dup2(devnull_fd, stderr_fd)
        yield
    finally:
        sys.stderr.flush()
        os.dup2(saved_fd, stderr_fd)
        os.close(saved_fd)
        os.close(devnull_fd)


def load_piper_voice(voice_path):
    """Load a Piper voice model.

    Onnxruntime writes device-discovery warnings (harmless noise about virtual
    DRM devices, e.g. from evdi/DisplayLink) straight to the stderr file
    descriptor when it builds the inference session. Silence them unless
    --verbose by redirecting the fd during the load.
    """
    if VERBOSE:
        from piper import PiperVoice

        return PiperVoice.load(voice_path)
    with _suppressed_native_stderr():
        from piper import PiperVoice

        return PiperVoice.load(voice_path)


# ==================== TTS ====================


def play_blank():
    """Play blank MP3 to wake up Bluetooth audio (avoids clipping the start)."""
    if NOSOUND:
        return
    if os.path.exists(BLANK_MP3):
        play_mp3(BLANK_MP3)


def play_beep():
    """Play the beep MP3 once, respecting VOLUME."""
    if NOSOUND:
        return
    if os.path.exists(BEEP_MP3):
        play_mp3(BEEP_MP3, volume=VOLUME)


def beep_count_for_minute(minute):
    """Return number of beeps to play: 2 on the hour, 1 on the half hour."""
    if minute == 0:
        return 2
    if minute == 30:
        return 1
    return 0


def prepare_speech(voice, text):
    """Synthesize WAV and play blank MP3 to warm up Bluetooth audio."""
    log(f"Preparing: {text}")
    if NOSOUND:
        return
    log_spoken(text)  # pragma: no cover
    synthesize(voice, text, TEMP_WAV)
    scale_volume(TEMP_WAV, VOLUME)
    play_blank()


def prepare_combined_speech(voice, texts, pause_ms=700):
    """Synthesize multiple texts into one WAV with pauses between them."""
    log(f"Preparing combined: {texts}")
    if NOSOUND:
        return
    for t in texts:
        log_spoken(t)
    synthesize_multi(voice, texts, TEMP_WAV, pause_ms)
    scale_volume(TEMP_WAV, VOLUME)
    play_blank()


def play_speech():
    """Play the previously prepared speech WAV."""
    log("Playing speech")
    if NOSOUND:
        return
    play_wav(TEMP_WAV)
    if os.path.exists(TEMP_WAV):
        os.remove(TEMP_WAV)


def speak(voice, text, beep_count=0):
    """Synthesize and play speech (no timing control)."""
    prepare_speech(voice, text)
    for _ in range(beep_count):
        play_beep()
    play_speech()


def run_exec(command, text, target, message=None):
    """Run --exec command with TEXT, TIME, DATE, MESSAGE as env vars."""
    if not isinstance(command, str) or not command:
        return
    env = os.environ.copy()
    env["TEXT"] = text
    env["TIME"] = target.strftime("%H:%M")
    env["DATE"] = target.strftime("%Y-%m-%d")
    env["MESSAGE"] = message or ""
    try:
        subprocess.Popen(
            command,
            shell=True,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as e:
        log(f"  --exec error: {e}")


# ==================== SESSION MANAGEMENT ====================


def get_running_sessions():
    """Return list of active sessions as (filepath, data) tuples."""
    if not os.path.exists(SESSIONS_DIR):
        return []
    sessions = []
    for name in os.listdir(SESSIONS_DIR):
        path = os.path.join(SESSIONS_DIR, name)
        if not name.endswith(".json"):
            if name.endswith(".pid"):
                os.remove(path)
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            pid = data["pid"]
            os.kill(pid, 0)
            sessions.append((path, data))
        except (json.JSONDecodeError, KeyError, ValueError):
            os.remove(path)
        except OSError:
            os.remove(path)
    return sessions


def create_session(pid, session_id, session_type=None, start=None, end=None):
    """Create a session file for a new daemon instance."""
    session_file = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    data = {
        "pid": pid,
        "command": " ".join(sys.argv),
    }
    if session_type:
        data["type"] = session_type
    if start is not None:
        data["start"] = start
    if end is not None:
        data["end"] = end
    with open(session_file, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return session_file


def remove_session(session_id):
    """Remove session files for a given session ID."""
    for ext in (".json", ".pid"):
        path = os.path.join(SESSIONS_DIR, f"{session_id}{ext}")
        if os.path.exists(path):
            os.remove(path)


def kill_session(path, data):
    """Kill a daemon process and remove its session file."""
    pid = data["pid"]
    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(50):
            try:
                os.kill(pid, 0)
            except OSError:
                break
            time.sleep(0.1)
        else:
            os.kill(pid, signal.SIGKILL)
        print(f"Stopped (PID {pid}).")
    except OSError as e:
        print(f"Error stopping process {pid}: {e}")
    if os.path.exists(path):
        os.remove(path)
    pid_path = path.replace(".json", ".pid")
    if os.path.exists(pid_path):
        os.remove(pid_path)


# ==================== SLEEP ====================


def read_sleep():
    """Read sleep file. Returns dict or None."""
    if not os.path.exists(SLEEP_FILE):
        return None
    try:
        with open(SLEEP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "timestamp" not in data:
            return None
        return data
    except (json.JSONDecodeError, OSError):
        log("Warning: corrupt sleep file, ignoring.")
        return None


def write_sleep(until=None):
    """Write sleep file atomically."""
    data = {"timestamp": time.time()}
    if until is not None:
        data["until"] = until
    tmp = SLEEP_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.rename(tmp, SLEEP_FILE)


def clear_sleep():
    """Remove sleep file."""
    try:
        os.remove(SLEEP_FILE)
    except OSError:
        pass


def read_wakeup():
    """Read wakeup file. Returns dict or None."""
    if not os.path.exists(WAKEUP_FILE):
        return None
    try:
        with open(WAKEUP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "timestamp" not in data:
            return None
        return data
    except (json.JSONDecodeError, OSError):
        return None


def write_wakeup():
    """Write early-wake marker file."""
    tmp = WAKEUP_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"timestamp": time.time()}, f)
    os.rename(tmp, WAKEUP_FILE)


def clear_wakeup():
    """Remove wakeup file."""
    try:
        os.remove(WAKEUP_FILE)
    except OSError:
        pass


def is_early_wake(start_minutes, end_minutes):
    """Check if early wake is active (between ranges only)."""
    full_day = start_minutes == 0 and end_minutes == time_to_minutes(23, 59)
    if full_day:
        return False
    if read_wakeup() is None:
        return False
    now = datetime.datetime.now()
    current = time_to_minutes(now.hour, now.minute)
    if start_minutes <= end_minutes:
        in_range = start_minutes <= current <= end_minutes
    else:
        in_range = current >= start_minutes or current <= end_minutes
    return not in_range


def _next_range_start_after(sleep_timestamp, start_minutes):
    """Find the first range start datetime after the sleep timestamp."""
    sleep_dt = datetime.datetime.fromtimestamp(sleep_timestamp)
    start_h = start_minutes // 60
    start_m = start_minutes % 60
    candidate = sleep_dt.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
    if candidate <= sleep_dt:
        candidate += datetime.timedelta(days=1)
    return candidate


def is_sleep_active(start_minutes=None, end_minutes=None, check_time=None):
    """Check if sleep is active for a daemon with the given range.

    Pass start_minutes/end_minutes for daemons with a time range (auto-wake).
    Pass None for daemons without a range (no auto-wake).
    Full-day range (0:00-23:59) is treated as no range.
    check_time overrides now() for the auto-wake comparison (use the
    announcement target so the warm-up window doesn't skip the first slot).
    """
    sleep_data = read_sleep()
    if sleep_data is None:
        return False
    if sleep_data.get("until") is not None and time.time() >= sleep_data["until"]:
        clear_sleep()
        return False
    if start_minutes is not None and end_minutes is not None:
        full_day = start_minutes == 0 and end_minutes == time_to_minutes(23, 59)
        if not full_day:
            next_start = _next_range_start_after(sleep_data["timestamp"], start_minutes)
            now = check_time if check_time is not None else datetime.datetime.now()
            if now >= next_start:
                # Range restarted: the indefinite sleep is over for this daemon.
                # Remove the stale file so it doesn't linger past its purpose.
                clear_sleep()
                return False
    return True


# ==================== TIME UTILITIES ====================


def parse_time_range(value, name):
    """Parse a --start/--end value into (hour, minute)."""
    try:
        if ":" in value:
            h, m = map(int, value.split(":"))
        else:
            h = int(value)
            m = 0
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
        return h, m
    except ValueError:
        print(f"Error: {name} must be H, HH, H:MM, or HH:MM (e.g., 7, 07:30), got '{value}'")
        sys.exit(1)


def parse_time_arg(value):
    """Parse a --time HH:MM value into (hour, minute)."""
    try:
        h, m = map(int, value.split(":"))
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
        return h, m
    except ValueError:
        print(f"Error: --time must be HH:MM (e.g., 16:00), got '{value}'")
        sys.exit(1)


_DURATION_UNITS = {
    "s": 1,
    "sec": 1,
    "secs": 1,
    "second": 1,
    "seconds": 1,
    "m": 60,
    "min": 60,
    "mins": 60,
    "minute": 60,
    "minutes": 60,
    "h": 3600,
    "hr": 3600,
    "hrs": 3600,
    "hour": 3600,
    "hours": 3600,
}


def parse_duration(text):
    """Parse a human duration into total seconds.

    Accepts compact forms (``5s``, ``5m``, ``3h``, ``1h30m``), full unit
    names (``5 minutes``, ``2 hours``, ``30 sec``), and a bare number
    (interpreted as seconds). Raises ValueError on anything unrecognized
    or non-positive.
    """
    s = text.strip().lower()
    if not s:
        raise ValueError(f"invalid duration '{text}'")
    if s.isdigit():
        total = int(s)
    else:
        tokens = re.findall(r"(\d+)\s*([a-z]+)", s)
        rebuilt = "".join(num + unit for num, unit in tokens)
        if not tokens or rebuilt != re.sub(r"\s+", "", s):
            raise ValueError(f"invalid duration '{text}'")
        total = 0
        for num, unit in tokens:
            if unit not in _DURATION_UNITS:
                raise ValueError(f"invalid duration '{text}': unknown unit '{unit}'")
            total += int(num) * _DURATION_UNITS[unit]
    if total <= 0:
        raise ValueError(f"invalid duration '{text}': must be greater than zero")
    return total


def time_to_minutes(hour, minute):
    """Convert hour:minute to total minutes since midnight (0-1439)."""
    return hour * 60 + minute


def is_in_range(hour, minute, start_minutes, end_minutes):
    """Check if hour:minute is within range (handles midnight wrap)."""
    t = time_to_minutes(hour, minute)
    if start_minutes <= end_minutes:
        return start_minutes <= t <= end_minutes
    else:
        return t >= start_minutes or t <= end_minutes
