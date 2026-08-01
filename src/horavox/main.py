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
"""HoraVox — main entry point. Dispatches to subcommands."""

import importlib
import os
import shlex
import shutil
import subprocess
import sys

from horavox.core import __version__

COMMANDS = {
    "clock": ("horavox.clock", "Run the speaking clock"),
    "now": ("horavox.now", "Speak the current time once"),
    "stop": ("horavox.stop", "Stop running background instances"),
    "list": ("horavox.list", "List running background instances"),
    "sleep": ("horavox.sleep", "Mute or resume running daemons (on/off)"),
    "wakeup": ("horavox.wakeup", "Resume all sleeping daemons (same as 'sleep off')"),
    "voice": ("horavox.voice", "Manage Piper voice models"),
    "at": ("horavox.at", "Speak the time at specified times"),
    "timer": ("horavox.timer", "Count down for a duration, then beep and speak"),
    "config": ("horavox.config", "Get or set default configuration"),
    "service": ("horavox.service", "Manage autostart service instances"),
    "completion": ("horavox.completion", "Generate shell completion scripts"),
}


def build_parser():
    """Build the full argparse parser tree (used by argcomplete for completion)."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="vox",
        description="HoraVox — the voice of the hour",
    )
    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version=f"vox {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command")
    for name, (module_path, desc) in COMMANDS.items():
        mod = importlib.import_module(module_path)
        sub = subparsers.add_parser(name, help=desc)
        mod.setup_parser(sub)
    _add_alias_subparsers(subparsers)
    return parser


def _run_shell_alias(name, body, args):
    """Run a git-style shell alias ('!command') via sh, then exit.

    Extra CLI args are passed as positional parameters ($1, $2, ...) by
    appending ``"$@"`` to the command, so the common ``!f() { ...; }; f``
    pattern receives them (as ``f "$@"``).
    """
    body = body.strip()
    if not body:
        print(f"Error: shell alias '{name}' is empty.")
        sys.exit(1)
    result = subprocess.run(["sh", "-c", f'{body} "$@"', name, *args])
    sys.exit(result.returncode)


def _add_alias_subparsers(subparsers):
    """Register git-style new-command aliases so tab-completion suggests them.

    A new-command alias (name that is not a builtin) becomes its own subcommand;
    if it expands to a builtin, that builtin's options are attached so the
    alias completes flags too. Best-effort — never break completion on a bad
    config.
    """
    try:
        from horavox.config import get_aliases

        aliases = get_aliases()
    except Exception:
        return
    for alias_name, value in aliases.items():
        if alias_name in COMMANDS or not value:
            continue
        # Shell alias ('!...'): complete the name only (its args are arbitrary).
        if value.startswith("!"):
            subparsers.add_parser(alias_name, help=f"shell alias: {value}")
            continue
        try:
            tokens = shlex.split(value)
        except ValueError:
            continue
        # A new-command alias must start with a target command, not an option;
        # an option-first value can't dispatch, so don't suggest it.
        if not tokens or tokens[0].startswith("-"):
            continue
        sub = subparsers.add_parser(alias_name, help=f"alias for '{value}'")
        target = tokens[0]
        if target in COMMANDS:
            importlib.import_module(COMMANDS[target][0]).setup_parser(sub)


def print_help():
    print(f"vox {__version__} — HoraVox, the voice of the hour\n")
    print("Usage: vox <command> [options]\n")
    print("Commands:")
    for name, (_, desc) in COMMANDS.items():
        print(f"  {name:<12} {desc}")
    print()
    print("Run 'vox <command> --help' for command-specific options.")
    print("Run 'vox --version' to show the version.")


def main():
    # Shell completion: build full parser tree only when completing
    if "_ARGCOMPLETE" in os.environ:
        parser = build_parser()
        import argcomplete

        argcomplete.autocomplete(parser)
        return

    # Update check (skip for service-managed processes and completion)
    if not os.environ.get("HORAVOX_SERVICE"):
        from horavox.update import check_for_update

        check_for_update()

    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print_help()
        return
    if sys.argv[1] in ("--version", "-V"):
        print(f"vox {__version__}")
        return
    cmd = sys.argv[1]
    extra = sys.argv[2:]
    from horavox.config import get_aliases

    aliases = get_aliases()

    # Git-style alias defining a NEW command: a non-builtin name whose value's
    # first token is the target command (e.g. alias.nap = "timer 30m -m X").
    # Builtins are never shadowed — an alias whose name is a builtin injects
    # default args into it instead (handled below).
    if cmd not in COMMANDS and cmd in aliases:
        value = aliases[cmd]
        # Git-style shell alias: value starting with '!' runs a shell command.
        if value.startswith("!"):
            _run_shell_alias(cmd, value[1:], extra)  # exits the process
        expansion = shlex.split(value)
        if not expansion:
            print(f"Error: alias '{cmd}' is empty.")
            sys.exit(1)
        cmd = expansion[0]
        extra = expansion[1:] + extra

    if cmd in COMMANDS:
        alias_args = shlex.split(aliases.get(cmd, "")) if cmd in aliases else []
        merged = alias_args + extra
        if os.environ.get("HORAVOX_SERVICE"):
            merged = [a for a in merged if a != "--background"]
        sys.argv = [f"vox {cmd}"] + merged
        mod = importlib.import_module(COMMANDS[cmd][0])
        mod.main()
        return
    # Try external vox-<cmd> executable (git-style)
    ext = shutil.which(f"vox-{cmd}")
    if ext:
        os.execvp(ext, [f"vox-{cmd}"] + extra)
        return  # execvp never returns, but safety for tests
    print(f"Unknown command: {cmd}\n")
    print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
