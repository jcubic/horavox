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
"""vox sleep — mute/unmute running daemons."""

import argparse
import datetime
import os
import re
import sys
import time

from horavox import core
from horavox.core import (
    clear_sleep,
    get_running_sessions,
    is_in_range,
    log_error,
    parse_time_arg,
    parse_time_range,
    time_to_minutes,
    write_sleep,
    write_wakeup,
)


def parse_duration(value):
    """Parse duration string like '2h', '30m', '1h30m' into seconds."""
    match = re.match(r"^(?:(\d+)h)?(?:(\d+)m)?$", value)
    if not match or not any(match.groups()):
        print(f"Error: invalid duration '{value}'. Use format like 2h, 30m, 1h30m.")
        sys.exit(1)
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    if hours == 0 and minutes == 0:
        print("Error: duration must be greater than zero.")
        sys.exit(1)
    return hours * 3600 + minutes * 60


def _compute_until(time_str):
    """Convert HH:MM to the next occurrence as a unix timestamp."""
    h, m = parse_time_arg(time_str)
    now = datetime.datetime.now()
    target = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if target <= now:
        target += datetime.timedelta(days=1)
    return target.timestamp()


def _session_type(data):
    """Detect session type from session data."""
    if "type" in data:
        return data["type"]
    parts = data.get("command", "").split()
    if len(parts) >= 2 and parts[1] in ("clock", "at", "now"):
        return parts[1]
    return None


def _has_range(data):
    """Check if a clock session has an explicit time range."""
    return "start" in data and "end" in data


def _has_between_range_sessions():
    """Check if any running clock session is currently outside its range."""
    now = datetime.datetime.now()
    for _, data in get_running_sessions():
        if data.get("type") != "clock":
            continue
        if "start" not in data or "end" not in data:
            continue
        sh, sm = parse_time_range(data["start"], "start")
        eh, em = parse_time_range(data["end"], "end")
        start_min = time_to_minutes(sh, sm)
        end_min = time_to_minutes(eh, em)
        if not is_in_range(now.hour, now.minute, start_min, end_min):
            return True
    return False


def setup_parser(parser):
    parser.add_argument(
        "action",
        nargs="?",
        default="on",
        choices=["on", "off"],
        help="on = mute (default), off = resume",
    )
    parser.add_argument(
        "--until",
        type=str,
        default=None,
        metavar="HH:MM",
        help="Auto-wake at the given time (only with 'on')",
    )
    parser.add_argument(
        "--for",
        type=str,
        default=None,
        dest="duration",
        metavar="DURATION",
        help="Auto-wake after duration, e.g. 2h, 30m, 1h30m (only with 'on')",
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Mute or resume running daemons",
        prog="vox sleep",
    )
    setup_parser(parser)
    return parser.parse_args()


def main():  # pragma: no cover
    try:
        _main()
    except KeyboardInterrupt:
        pass
    except Exception:
        log_error()
        raise


def _sleep_on(args):
    """Enable sleep (mute daemons)."""
    if args.until and args.duration:
        print("Error: --until and --for cannot be used together.")
        sys.exit(1)

    sessions = get_running_sessions()
    if not sessions:
        print("No running sessions found; nothing to mute.")
        return

    has_expiry = args.until is not None or args.duration is not None

    for _, data in sessions:
        stype = _session_type(data)
        if stype == "clock" and not _has_range(data) and not has_expiry:
            print(
                "Error: running clock has no time range (--start/--end).\n"
                "Without a range, sleep cannot auto-wake.\n"
                "Add --start/--end to the clock, or use: vox sleep --until HH:MM"
            )
            sys.exit(1)

    at_sessions = [d for _, d in sessions if _session_type(d) == "at"]
    if at_sessions and not has_expiry:
        print(
            "Warning: running 'vox at' instances will stay muted until 'vox sleep off'.\n"
            "To auto-wake, use: vox sleep --until HH:MM or vox sleep --for DURATION"
        )

    until = None
    if args.until:
        until = _compute_until(args.until)
    elif args.duration:
        until = time.time() + parse_duration(args.duration)

    write_sleep(until=until)

    if until:
        wake_dt = datetime.datetime.fromtimestamp(until)
        print(f"Sleep activated until {wake_dt.strftime('%H:%M')}.")
    else:
        print("Sleep activated.")


def _sleep_off():
    """Disable sleep (resume daemons)."""
    if os.path.exists(core.SLEEP_FILE):
        clear_sleep()
        print("Wakeup: all daemons resumed.")
    else:
        print("No active sleep to cancel.")
    has_between = _has_between_range_sessions()
    if has_between:
        write_wakeup()
        print("Early wake activated for daemons between ranges.")
    else:
        print("All daemons are within their ranges.")


def _main():
    args = parse_args()
    if args.action == "off":
        _sleep_off()
    else:
        _sleep_on(args)


if __name__ == "__main__":
    main()
