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
"""vox completion — generate shell completion scripts."""

import argparse
import sys


def setup_parser(parser):
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--bash", action="store_true", help="Output bash completion script")
    group.add_argument("--zsh", action="store_true", help="Output zsh completion script")
    group.add_argument("--fish", action="store_true", help="Output fish completion script")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate shell completion scripts",
        prog="vox completion",
    )
    setup_parser(parser)
    return parser.parse_args()


def main():
    try:
        _main()
    except KeyboardInterrupt:
        pass


def _main():
    args = parse_args()

    try:
        import argcomplete
    except ImportError:
        print("Error: argcomplete is not installed. Run: pip install argcomplete", file=sys.stderr)
        sys.exit(1)

    if args.bash:
        shell = "bash"
    elif args.zsh:
        shell = "zsh"
    else:
        shell = "fish"

    print(argcomplete.shellcode(["vox"], shell=shell))


if __name__ == "__main__":
    main()
