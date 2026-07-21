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
"""vox timer — count down to a time (or for a duration), then beep and speak.

Two ways to give the target:
  vox timer 30m           duration from now
  vox timer 10:30         absolute clock time (next occurrence)

Optional reminders announce the remaining time before the target:
  vox timer 10:30 --reminders 30m,1h,1h30m --name 'the train'
"""

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
    load_durations,
    log,
    log_error,
    parse_duration,
    parse_time_arg,
    play_beep,
    play_speech,
    prepare_speech,
    remove_session,
    resolve_voice,
    run_exec,
    speak,
    spoken_duration,
)

# Beeps played on each announcement — same as the clock on the hour.
END_BEEPS = 2


def setup_parser(parser):
    parser.add_argument(
        "duration",
        type=str,
        metavar="TIME",
        help="Duration (5m, 1h30m, 90s) or clock time (10:30) to count down to",
    )
    parser.add_argument(
        "--reminders",
        type=str,
        default=None,
        metavar="LIST",
        help="Comma-separated reminder offsets before the target, e.g. 30m,1h,1h30m",
    )
    parser.add_argument(
        "--name",
        type=str,
        default=None,
        metavar="TEXT",
        help="Event name spoken in reminders and at the target (e.g. 'the train')",
    )
    parser.add_argument(
        "--message",
        "-m",
        type=str,
        default=None,
        metavar="TEXT",
        help="Speak this text at the target instead of the default phrase",
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
        help="Run CMD on each announcement ($TEXT, $TIME, $DATE, $MESSAGE)",
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Count down to a time (or for a duration), then beep and speak",
        prog="vox timer",
    )
    setup_parser(parser)
    return parser.parse_args()


def _clean(text):
    """Collapse whitespace and trim (handles empty {name} in templates)."""
    return " ".join(text.split())


def _target_datetime(arg, now):
    """Interpret the positional as an absolute clock time (HH:MM) or a duration."""
    if ":" in arg:
        h, m = parse_time_arg(arg)
        target = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if target <= now:
            target += datetime.timedelta(days=1)
        return target
    return now + datetime.timedelta(seconds=parse_duration(arg))


def _parse_reminders(value):
    """Parse a comma-separated list of reminder offsets into sorted seconds."""
    if not value:
        return []
    offsets = set()
    for part in value.split(","):
        part = part.strip()
        if part:
            offsets.add(parse_duration(part))
    return sorted(offsets)


def _final_text(args, lang, durations):
    """Text spoken when the target time is reached."""
    if args.message:
        return args.message
    if args.name:
        return _clean(durations.get("now", "now {name}").format(name=args.name))
    return get_message(lang, "timer_done", "time is up")


def _reminder_text(args, lang, durations, offset_seconds):
    """Text spoken at a reminder: 'in <duration> <name>'."""
    phrase = spoken_duration(durations, lang, offset_seconds)
    template = durations.get("template", "in {duration} {name}")
    return _clean(template.format(duration=phrase, name=args.name or ""))


def _build_events(args, lang, durations, now, target, offsets, final_text):
    """Build a sorted list of (fire_time, text): reminders before target + final."""
    events = []
    for off in offsets:
        fire = target - datetime.timedelta(seconds=off)
        if fire > now - datetime.timedelta(seconds=5):
            events.append((fire, _reminder_text(args, lang, durations, off)))
    events.append((target, final_text))
    events.sort(key=lambda event: event[0])
    return events


def _load_voice(args, lang):
    if core.NOSOUND:
        return None
    voice_path = resolve_voice(args.voice, lang)  # pragma: no cover
    voice_name = os.path.basename(voice_path).replace(".onnx", "")
    log(f"Loading voice: {voice_name}")
    from piper import PiperVoice

    return PiperVoice.load(voice_path)


def run_timer(args, lang, text, seconds):
    """Simple mode: wait `seconds`, then beep, speak, and run --exec."""
    voice = _load_voice(args, lang)
    log(f"Timer set for {int(seconds)}s")
    time.sleep(seconds)
    speak(voice, text, beep_count=END_BEEPS)
    run_exec(args.exec_cmd, text, datetime.datetime.now(), args.message)


def run_reminders(args, lang, events):
    """Reminder mode: announce each (fire_time, text) event in order."""
    voice = _load_voice(args, lang)
    announce_offset = 3
    tick = 1.0
    idx = 0
    while idx < len(events):
        now = datetime.datetime.now()
        fire_time, text = events[idx]
        secs = (fire_time - now).total_seconds()
        if secs <= announce_offset + 0.5:
            if secs < -5:
                log(f"  {fire_time:%H:%M} missed, skipping.")
                idx += 1
                continue
            prepare_speech(voice, text)
            remaining = (fire_time - datetime.datetime.now()).total_seconds()
            if remaining > 0:
                time.sleep(remaining)
            for _ in range(END_BEEPS):
                play_beep()
            play_speech()
            run_exec(args.exec_cmd, text, fire_time, args.message)
            idx += 1
            continue
        time.sleep(tick)


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

    lang = args.lang or detect_language()
    durations = load_durations(lang) or load_durations("en")

    now = datetime.datetime.now()
    try:
        target = _target_datetime(args.duration, now)
        offsets = _parse_reminders(args.reminders)
    except ValueError as e:
        raise SystemExit(f"Error: {e}")

    final_text = _final_text(args, lang, durations)

    if offsets:
        events = _build_events(args, lang, durations, now, target, offsets, final_text)

        def runner():
            run_reminders(args, lang, events)
    else:
        seconds = max(0.0, (target - now).total_seconds())

        def runner():
            run_timer(args, lang, final_text, seconds)

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
                runner()
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
            runner()
        finally:
            remove_session(session_id)
    else:
        runner()


if __name__ == "__main__":
    main()
