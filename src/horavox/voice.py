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
"""vox voice — manage Piper voice models with interactive browser."""

import argparse
import datetime
import sys

from voxkit import BrowserConfig

from horavox.core import (
    beep_count_for_minute,
    detect_language,
    get_spoken_time,
    get_voice_manager,
    load_language_data,
    load_piper_voice,
    log_error,
    speak,
)

SHOW_CURSOR = "\033[?25h"


def setup_parser(parser):
    parser.add_argument(
        "--lang",
        type=str,
        default=None,
        metavar="LANG",
        help="Language code, e.g. pl, en (default: from system locale)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_voices",
        help="List available voices (non-interactive)",
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Manage Piper voice models",
        prog="vox voice",
    )
    setup_parser(parser)
    return parser.parse_args()


def get_default_voice_key(voices, config_voice=None):
    """Determine which voice key would be used as the default."""
    if config_voice:
        for v in voices:
            if v["key"] == config_voice:
                return config_voice
    installed = [v for v in voices if v["installed"]]
    if not installed:
        return None
    for v in installed:
        if "-medium" in v["key"]:
            return v["key"]
    return installed[0]["key"]


def cmd_list(lang, config_voice=None):
    """Print voice list to stdout (non-interactive, no colors)."""
    vm = get_voice_manager()
    voices = vm.list_voices(lang)
    if not voices:
        print(f"No voices found for language '{lang}'.")
        return
    default_key = get_default_voice_key(voices, config_voice)
    lang_name = vm.get_language_name(lang)
    print(f"Available voices for {lang_name} ({lang}):\n")
    print(f"  {'Voice':<40} {'Quality':<10} {'Size':<10} {'Status'}")
    print(f"  {'-' * 40} {'-' * 10} {'-' * 10} {'-' * 10}")
    for v in voices:
        marks = []
        if v["installed"]:
            marks.append("[*]")
        if v["key"] == default_key:
            marks.append("[D]")
        mark = " ".join(marks)
        print(f"  {v['key']:<40} {v['quality']:<10} {v['size_mb']:.0f} MB     {mark}")


def _speak_with_voice(voice_key, lang, mode="classic"):
    """Load a voice by key and speak the current time."""
    vm = get_voice_manager()
    onnx_path = vm.get_path(voice_key)
    if not onnx_path:
        return
    voice = load_piper_voice(str(onnx_path))
    lang_data, _ = load_language_data(lang, mode)
    now = datetime.datetime.now()
    text = get_spoken_time(lang_data, now.hour, now.minute)
    speak(voice, text, beep_count=beep_count_for_minute(now.minute))


def cmd_interactive(lang, config_voice=None, mode="classic"):
    """Interactive voice browser with install/uninstall."""
    vm = get_voice_manager()
    config = BrowserConfig(
        lang=lang,
        default_voice=config_voice,
        test_fn=lambda key: _speak_with_voice(key, lang, mode),
    )
    vm.browse(config=config)


def main():  # pragma: no cover
    try:
        _main()
    except KeyboardInterrupt:
        sys.stdout.write(SHOW_CURSOR + "\n")
        sys.stdout.flush()
    except Exception:
        sys.stdout.write(SHOW_CURSOR)
        sys.stdout.flush()
        log_error()
        raise


def _main():
    args = parse_args()
    from horavox.config import apply_config, load_config

    apply_config(args)
    lang = args.lang or detect_language()
    settings = load_config()["settings"]
    config_voice = settings.get("voice")
    mode = settings.get("mode", "classic")

    if args.list_voices:
        cmd_list(lang, config_voice)
    else:
        cmd_interactive(lang, config_voice, mode)


if __name__ == "__main__":
    main()
