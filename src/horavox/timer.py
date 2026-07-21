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
"""vox timer — count down for a duration, then beep and speak."""

import argparse
import datetime
import os
import time
import uuid

from daemonize import Daemonize

from horavox import core
from horavox.core import (
    PKG_DIR,
    SESSIONS_DIR,
    configure,
    create_session,
    detect_language,
    ensure_user_dirs,
    get_message,
    log,
    log_error,
    parse_duration,
    remove_session,
    resolve_voice,
    run_exec,
    speak,
)

# Beeps played when the timer ends — same as the clock on the hour.
END_BEEPS = 2


def setup_parser(parser):
    parser.add_argument(
        "duration",
        type=str,
        metavar="DURATION",
        help="Countdown length, e.g. 5m, 3h, 90s, 1h30m, '5 minutes'",
    )
    parser.add_argument(
        "--message",
        "-m",
        type=str,
        default=None,
        metavar="TEXT",
        help="Speak this text when the timer ends (default: a generic phrase)",
    )
    parser.add_argument(
        "--lang",
        type=str,
        default=None,
        metavar="LANG",
        help="Language code, e.g. pl, en (default: from system locale)",
    )
    parser.add_argument(
        "--voice",
        type=str,
        default=None,
        metavar="NAME",
        help="Voice name, e.g. en_US-lessac-medium (auto-downloads if missing)",
    )
    parser.add_argument(
        "--background",
        action="store_true",
        help="Run as a background daemon",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show log messages (silent by default)",
    )
    parser.add_argument(
        "--volume",
        type=int,
        default=100,
        metavar="PCT",
        help="Volume level 0-100 percent (default: 100, 0 = no sound)",
    )
    parser.add_argument(
        "--nosound",
        action="store_true",
        help="Same as --volume 0 — skip voice loading and audio playback",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Alias for --nosound --verbose",
    )
    parser.add_argument(
        "--exec",
        type=str,
        default=None,
        dest="exec_cmd",
        metavar="CMD",
        help="Run CMD when the timer ends ($TEXT, $TIME, $DATE, $MESSAGE)",
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Count down for a duration, then beep and speak",
        prog="vox timer",
    )
    setup_parser(parser)
    return parser.parse_args()


def _load_voice(args, lang):
    if core.NOSOUND:
        return None
    voice_path = resolve_voice(args.voice, lang)  # pragma: no cover
    voice_name = os.path.basename(voice_path).replace(".onnx", "")
    log(f"Loading voice: {voice_name}")
    from piper import PiperVoice

    return PiperVoice.load(voice_path)


def run_timer(args, lang, text, seconds):
    """Wait for the given number of seconds, then beep, speak, and run --exec."""
    voice = _load_voice(args, lang)
    log(f"Timer set for {seconds}s")
    time.sleep(seconds)
    speak(voice, text, beep_count=END_BEEPS)
    run_exec(args.exec_cmd, text, datetime.datetime.now(), args.message)


def main():  # pragma: no cover
    try:
        _main()
    except KeyboardInterrupt:
        pass
    except Exception:
        log_error()
        raise


def _main():
    args = parse_args()
    from horavox.config import apply_config

    apply_config(args)
    configure(
        verbose=args.verbose,
        nosound=args.nosound,
        volume=args.volume,
        debug=args.debug,
    )

    try:
        seconds = parse_duration(args.duration)
    except ValueError as e:
        raise SystemExit(f"Error: {e}")

    lang = args.lang or detect_language()
    text = args.message or get_message(lang, "timer_done", "time is up")

    # --background mode
    if args.background:  # pragma: no cover
        if not core.NOSOUND:
            voice_path = resolve_voice(args.voice, lang)
            if not os.path.exists(voice_path):
                return

        ensure_user_dirs()
        session_id = str(uuid.uuid4())
        pid_file = os.path.join(SESSIONS_DIR, f"{session_id}.pid")

        def daemon_action():
            create_session(os.getpid(), session_id, session_type="timer")
            try:
                run_timer(args, lang, text, seconds)
            except Exception:
                log_error()
                raise
            finally:
                remove_session(session_id)

        daemon = Daemonize(
            app="horavox",
            pid=pid_file,
            action=daemon_action,
            chdir=PKG_DIR,
        )
        log("Starting HoraVox in the background...")
        daemon.start()
        return

    # Foreground (with a session when supervised by the service manager)
    if os.environ.get("HORAVOX_SERVICE"):
        ensure_user_dirs()
        session_id = str(uuid.uuid4())
        create_session(os.getpid(), session_id, session_type="timer")
        try:
            run_timer(args, lang, text, seconds)
        finally:
            remove_session(session_id)
    else:
        run_timer(args, lang, text, seconds)


if __name__ == "__main__":
    main()
