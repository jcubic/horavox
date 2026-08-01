#!/usr/bin/env python3
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
"""chime.py — strike the hour like a bell / grandfather clock.

Usage: chime.py HH:MM

- On the hour (MM == 00): strikes the hour in 12-hour form. It plays
  chime_cut.mp3 (hour - 1) times followed by one chime_end.mp3, so the total
  number of bells equals the hour: 10:00 -> 9 cuts + 1 end = 10 bells,
  1:00 -> 1 bell, midnight/noon -> 12 bells.
- On the half hour (MM == 30): a single chime_end.mp3.
- Any other minute: nothing.

Installed as its own `chime` command (not a vox subcommand), meant for
HoraVox's --exec, e.g.:

    vox clock --freq 30 --exec 'chime "$TIME"'

chime_cut.mp3 and chime_end.mp3 ship in the package's data/ directory. Each can
be overridden via the HoraVox config (highest priority)::

    vox config chime.mp3.cut /path/to/cut.mp3
    vox config chime.mp3.end /path/to/end.mp3

or point CHIME_DIR at a directory holding both files. A silent blank.mp3 is
played first to wake up Bluetooth audio so the first bell isn't clipped.
Playback uses mpg123 (the same MP3 player HoraVox requires) and is blocking,
so the whole thing plays back-to-back as one continuous chime.
"""

import os
import subprocess
import sys

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
# Silent MP3 played first to wake up Bluetooth audio so the first bell isn't clipped.
BLANK_MP3 = os.path.join(DATA_DIR, "blank.mp3")


def _chime_config():
    """Return the 'chime' section of the HoraVox config (best-effort, {} on error)."""
    try:
        from horavox.config import load_config

        return load_config().get("chime", {})
    except Exception:
        return {}


def _mp3_path(kind):
    """Resolve the mp3 path for 'cut'/'end': config override, then CHIME_DIR, then bundled."""
    configured = _chime_config().get("mp3", {}).get(kind)
    if configured:
        return os.path.expanduser(configured)
    base = os.environ.get("CHIME_DIR") or DATA_DIR
    return os.path.join(base, f"chime_{kind}.mp3")


def parse_time(value):
    """Parse an 'HH:MM' string into (hour, minute). Raise ValueError if invalid."""
    parts = value.split(":")
    if len(parts) != 2:
        raise ValueError(value)
    hour, minute = int(parts[0]), int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(value)
    return hour, minute


def strikes_for_hour(hour):
    """Number of bells for a 24-hour hour, in 12-hour form (12 at 0/12, else h%12)."""
    return (hour + 11) % 12 + 1


def _play_all(paths):
    """Play the given MP3s back-to-back in a single mpg123 process.

    One process keeps the audio device open across all files, and mpg123's
    gapless decoding (on by default) trims MP3 frame padding, so the strikes
    play as one continuous chime with no silence between them.
    """
    existing = [p for p in paths if os.path.exists(p)]
    for p in paths:
        if not os.path.exists(p):
            sys.stderr.write(f"chime: missing sound file: {p}\n")
    if not existing:
        return
    try:
        subprocess.run(["mpg123", "-q", *existing], check=False)
    except FileNotFoundError:
        sys.stderr.write("chime: mpg123 not found (install: sudo apt install mpg123)\n")


def chime(hour, minute):
    """Strike for the given time: full hour on MM==00, single bell on MM==30.

    Each strike is prefixed with the silent blank.mp3 to wake up Bluetooth
    audio, all played in one process so the bells stay gapless.
    """
    if minute == 0:
        cut, end = _mp3_path("cut"), _mp3_path("end")
        _play_all([BLANK_MP3] + [cut] * (strikes_for_hour(hour) - 1) + [end])
    elif minute == 30:
        _play_all([BLANK_MP3, _mp3_path("end")])


def main(argv=None):
    args = (sys.argv if argv is None else argv)[1:]
    if not args or args[0] in ("-h", "--help"):
        print("Usage: chime.py HH:MM  (10:00 strikes 10, 10:30 strikes once)")
        return 0 if args else 1
    try:
        hour, minute = parse_time(args[0])
    except ValueError:
        sys.stderr.write(f"chime: invalid time '{args[0]}', expected HH:MM\n")
        return 1
    chime(hour, minute)
    return 0


if __name__ == "__main__":
    sys.exit(main())
