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
"""vox wakeup — resume all sleeping daemons."""

import argparse
import os

from horavox import core
from horavox.core import (
    clear_sleep,
    log_error,
)


def setup_parser(parser):
    pass


def parse_args():
    parser = argparse.ArgumentParser(
        description="Resume all sleeping daemons",
        prog="vox wakeup",
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
    parse_args()
    if os.path.exists(core.SLEEP_FILE):
        clear_sleep()
        print("Wakeup: all daemons resumed.")
    else:
        print("No active sleep to cancel.")


if __name__ == "__main__":
    main()
