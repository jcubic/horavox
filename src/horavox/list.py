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
"""vox list — list running background instances."""

import argparse

from horavox.core import (
    get_running_sessions,
    log_error,
)


def setup_parser(parser):
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Include command line in output",
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="List running background instances",
        prog="vox list",
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
    sessions = get_running_sessions()

    for _, data in sessions:
        if args.verbose:
            print(f"{data['pid']}\t{data.get('command', '?')}")
        else:
            print(data["pid"])


if __name__ == "__main__":
    main()
