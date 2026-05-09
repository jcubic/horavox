"""vox voice — manage Piper voice models with interactive browser."""

import argparse
import os
import sys
import termios
import tty

from horavox.core import (
    VOICES_DIR,
    beep_count_for_minute,
    detect_language,
    download_voice,
    get_spoken_time,
    get_voices_catalog,
    list_voices_for_language,
    load_language_data,
    log_error,
    speak,
    uninstall_voice,
)

CYAN = "\033[36m"

GREEN = "\033[32m"
BOLD = "\033[1m"
RESET = "\033[0m"
CLEAR_LINE = "\033[2K"
HIDE_CURSOR = "\033[?25l"
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


def get_lang_name(lang):
    """Get the English name for a language code."""
    catalog = get_voices_catalog()
    for _, info in catalog.items():
        if info.get("language", {}).get("family", "") == lang:
            return info.get("language", {}).get("name_english", lang)
    return lang


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
    voices = list_voices_for_language(lang)
    if not voices:
        print(f"No voices found for language '{lang}'.")
        return
    default_key = get_default_voice_key(voices, config_voice)
    lang_name = get_lang_name(lang)
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


def getch():
    """Read a single keypress. Returns 'UP', 'DOWN', or a character."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            ch2 = sys.stdin.read(1)
            if ch2 == "[":
                ch3 = sys.stdin.read(1)
                if ch3 == "A":
                    return "UP"
                if ch3 == "B":
                    return "DOWN"
            return None
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def render_list(voices, cursor, lang_name, lang, status="", default_key=None):
    """Render the voice list with cursor and status line."""
    lines = []
    lines.append(f"Voices for {lang_name} ({lang}):")
    lines.append("")
    for i, v in enumerate(voices):
        arrow = ">" if i == cursor else " "
        marks = ""
        if v["installed"]:
            marks += f" {GREEN}[*]{RESET}"
        if v["key"] == default_key:
            marks += f" {CYAN}[D]{RESET}"
        if not marks:
            marks = "    "
        line = f"  {arrow} {v['key']:<40} {v['quality']:<8} {v['size_mb']:>3.0f} MB{marks}"
        lines.append(line)
    lines.append("")
    nav = f"{BOLD}↑/↓{RESET} Navigate"
    enter = f"{BOLD}Enter{RESET} Test"
    inst = f"{BOLD}i{RESET} Install"
    uninst = f"{BOLD}u{RESET} Uninstall"
    quit_hint = f"{BOLD}q{RESET} Quit"
    lines.append(f"  {nav}  {enter}  {inst}  {uninst}  {quit_hint}")
    if status:
        lines.append(f"  {status}")
    return lines


def draw(lines, prev_line_count):
    """Draw lines, clearing any previous output first."""
    # Move up to overwrite previous render
    if prev_line_count > 0:
        sys.stdout.write(f"\033[{prev_line_count}A")
    for line in lines:
        sys.stdout.write(f"\r{CLEAR_LINE}{line}\n")
    # Clear any leftover lines from previous longer render
    if prev_line_count > len(lines):
        for _ in range(prev_line_count - len(lines)):
            sys.stdout.write(f"\r{CLEAR_LINE}\n")
        sys.stdout.write(f"\033[{prev_line_count - len(lines)}A")
    sys.stdout.flush()


def progress_bar(filename, block_num, block_size, total_size):
    """Render a download progress bar on the current line."""
    if total_size <= 0:
        return
    downloaded = block_num * block_size
    pct = min(100, downloaded * 100 // total_size)
    bar_width = 30
    filled = bar_width * pct // 100
    bar = "█" * filled + "░" * (bar_width - filled)
    sys.stdout.write("\033[s")  # save cursor
    sys.stdout.write(f"\r{CLEAR_LINE}  Downloading {filename}... [{bar}] {pct}%")
    sys.stdout.flush()
    if pct >= 100:
        sys.stdout.write(f"\r{CLEAR_LINE}")
        sys.stdout.write("\033[u")  # restore cursor
        sys.stdout.flush()


def _speak_with_voice(voice_key, lang, mode="classic"):
    """Load a voice by key and speak the current time."""
    import datetime
    import os

    from piper import PiperVoice

    onnx_path = os.path.join(VOICES_DIR, f"{voice_key}.onnx")
    voice = PiperVoice.load(onnx_path)
    lang_data, _ = load_language_data(lang, mode)
    now = datetime.datetime.now()
    text = get_spoken_time(lang_data, now.hour, now.minute)
    speak(voice, text, beep_count=beep_count_for_minute(now.minute))


def cmd_interactive(lang, config_voice=None, mode="classic"):
    """Interactive voice browser with install/uninstall."""
    voices = list_voices_for_language(lang)
    if not voices:
        print(f"No voices found for language '{lang}'.")
        return

    lang_name = get_lang_name(lang)
    default_key = get_default_voice_key(voices, config_voice)
    cursor = 0
    prev_lines = 0
    status = ""

    sys.stdout.write(HIDE_CURSOR)
    sys.stdout.flush()

    try:
        while True:
            lines = render_list(voices, cursor, lang_name, lang, status, default_key)
            draw(lines, prev_lines)
            prev_lines = len(lines)
            status = ""

            key = getch()
            if key == "UP" and cursor > 0:
                cursor -= 1
            elif key == "DOWN" and cursor < len(voices) - 1:
                cursor += 1
            elif key in ("q", "\x03", "\x1b"):  # q, Ctrl-C, Esc
                break
            elif key == "i":
                v = voices[cursor]
                if v["installed"]:
                    status = f"'{v['key']}' is already installed."
                else:
                    msg = f"Installing {v['key']}..."
                    lines = render_list(voices, cursor, lang_name, lang, msg, default_key)
                    draw(lines, prev_lines)
                    prev_lines = len(lines)
                    download_voice(v["key"], progress_cb=progress_bar)
                    v["installed"] = True
                    default_key = get_default_voice_key(voices, config_voice)
                    status = f"Installed '{v['key']}'."
            elif key == "u":
                v = voices[cursor]
                if not v["installed"]:
                    status = f"'{v['key']}' is not installed."
                else:
                    with open(os.devnull, "w") as devnull:
                        old_stdout = sys.stdout
                        sys.stdout = devnull
                        try:
                            uninstall_voice(v["key"])
                        finally:
                            sys.stdout = old_stdout
                    v["installed"] = False
                    default_key = get_default_voice_key(voices, config_voice)
                    status = f"Uninstalled '{v['key']}'."
            elif key in ("\r", "\n"):
                v = voices[cursor]
                if not v["installed"]:
                    msg = f"Installing {v['key']}..."
                    lines = render_list(voices, cursor, lang_name, lang, msg, default_key)
                    draw(lines, prev_lines)
                    prev_lines = len(lines)
                    download_voice(v["key"], progress_cb=progress_bar)
                    v["installed"] = True
                    default_key = get_default_voice_key(voices, config_voice)
                status = f"Speaking with '{v['key']}'..."
                lines = render_list(voices, cursor, lang_name, lang, status, default_key)
                draw(lines, prev_lines)
                prev_lines = len(lines)
                sys.stdout.write(SHOW_CURSOR)
                sys.stdout.flush()
                _speak_with_voice(v["key"], lang, mode)
                sys.stdout.write(HIDE_CURSOR)
                sys.stdout.flush()
                status = f"Spoke current time with '{v['key']}'."
    finally:
        sys.stdout.write(SHOW_CURSOR)
        sys.stdout.write("\n")
        sys.stdout.flush()


def main():
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
