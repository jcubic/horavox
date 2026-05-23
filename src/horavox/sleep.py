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
"""vox sleep — mute all running daemons until range restart or explicit wakeup."""

import argparse
import datetime
import re
import sys
import time

from horavox.core import (
    get_running_sessions,
    log_error,
    parse_time_arg,
    write_sleep,
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


def setup_parser(parser):
    parser.add_argument(
        "--until",
        type=str,
        default=None,
        metavar="HH:MM",
        help="Auto-wake at the given time",
    )
    parser.add_argument(
        "--for",
        type=str,
        default=None,
        dest="duration",
        metavar="DURATION",
        help="Auto-wake after duration (e.g. 2h, 30m, 1h30m)",
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Mute all running daemons",
        prog="vox sleep",
    )
    setup_parser(parser)
    return parser.parse_args()


def main():
    try:
        _main()
    except KeyboardInterrupt:
        pass
    except Exception:
        log_error()
        raise


def _main():
    args = parse_args()

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
            "Warning: running 'vox at' instances will stay muted until 'vox wakeup'.\n"
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


if __name__ == "__main__":
    main()
