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
"""vox stop — stop running background instances."""

import argparse
import sys

from horavox.core import (
    get_running_sessions,
    kill_session,
    log_error,
)


def setup_parser(parser):
    parser.add_argument(
        "--pid",
        type=int,
        default=None,
        metavar="PID",
        help="Stop a specific instance by PID",
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Stop running background instances",
        prog="vox stop",
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


def _main():
    args = parse_args()
    sessions = get_running_sessions()

    # --pid mode: stop a specific instance
    if args.pid is not None:
        for path, data in sessions:
            if data["pid"] == args.pid:
                kill_session(path, data)
                return
        print(f"No HoraVox instance with PID {args.pid}.")
        sys.exit(1)

    # Interactive mode
    if not sessions:
        print("No HoraVox instances running.")
        return

    if len(sessions) == 1:
        path, data = sessions[0]
        kill_session(path, data)
        return

    # Multiple instances: interactive selection with arrow keys
    import inquirer

    STOP_ALL = "__all__"
    choices = []
    for path, data in sessions:
        label = f"PID {data['pid']}  {data.get('command', '?')}"
        choices.append((label, path))
    choices.append(("Stop all", STOP_ALL))

    try:
        questions = [
            inquirer.List(
                "session",
                message=f"{len(sessions)} instances running. Select to stop",
                choices=choices,
            )
        ]
        answer = inquirer.prompt(questions)
    except KeyboardInterrupt:
        return

    if answer is None:
        return

    selected = answer["session"]
    if selected == STOP_ALL:
        for path, data in sessions:
            kill_session(path, data)
    else:
        for path, data in sessions:
            if path == selected:
                kill_session(path, data)
                break


if __name__ == "__main__":
    main()
