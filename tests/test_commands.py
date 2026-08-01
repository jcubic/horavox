"""Unit tests for command modules — main, clock, now, stop, voice, sleep, wakeup.

Tests the option parsing and dispatch logic by mocking core functions.
"""

import argparse
import datetime
import json
import os
import sys
import time
from unittest import mock

import pytest

from horavox import core

# ==================== main.py ====================


class TestMainDispatcher:
    def test_no_args_prints_help(self, capsys):
        from horavox.main import main

        with mock.patch.object(sys, "argv", ["vox"]):
            main()
        out = capsys.readouterr().out
        assert "Usage: vox <command>" in out
        assert "clock" in out
        assert "now" in out
        assert "stop" in out
        assert "voice" in out

    def test_help_flag(self, capsys):
        from horavox.main import main

        with mock.patch.object(sys, "argv", ["vox", "--help"]):
            main()
        out = capsys.readouterr().out
        assert "Usage: vox <command>" in out

    def test_version_flag(self, capsys):
        from horavox.main import main

        with mock.patch.object(sys, "argv", ["vox", "--version"]):
            main()
        out = capsys.readouterr().out
        assert core.__version__ in out

    def test_version_short_flag(self, capsys):
        from horavox.main import main

        with mock.patch.object(sys, "argv", ["vox", "-V"]):
            main()
        out = capsys.readouterr().out
        assert core.__version__ in out

    def test_unknown_command(self, capsys):
        from horavox.main import main

        with mock.patch.object(sys, "argv", ["vox", "bogus"]):
            with mock.patch("horavox.main.shutil.which", return_value=None):
                with pytest.raises(SystemExit) as exc:
                    main()
                assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "Unknown command: bogus" in out

    def test_dispatches_to_clock(self):
        from horavox.main import main

        with mock.patch.object(sys, "argv", ["vox", "clock"]):
            with mock.patch("horavox.clock.main") as m:
                main()
                m.assert_called_once()

    def test_dispatches_to_now(self):
        from horavox.main import main

        with mock.patch.object(sys, "argv", ["vox", "now"]):
            with mock.patch("horavox.now.main") as m:
                main()
                m.assert_called_once()

    def test_dispatches_to_stop(self):
        from horavox.main import main

        with mock.patch.object(sys, "argv", ["vox", "stop"]):
            with mock.patch("horavox.stop.main") as m:
                main()
                m.assert_called_once()

    def test_dispatches_to_voice(self):
        from horavox.main import main

        with mock.patch.object(sys, "argv", ["vox", "voice"]):
            with mock.patch("horavox.voice.main") as m:
                main()
                m.assert_called_once()

    def test_external_command(self):
        import shutil as _shutil

        from horavox.main import main

        with mock.patch.object(sys, "argv", ["vox", "my-plugin"]):
            with mock.patch.object(_shutil, "which", return_value="/usr/bin/vox-my-plugin"):
                with mock.patch("os.execvp") as m:
                    main()
                    m.assert_called_once_with("/usr/bin/vox-my-plugin", ["vox-my-plugin"])

    def test_argv_rewrite(self):
        from horavox.main import main

        captured_argv = []

        def fake_main():
            captured_argv.extend(sys.argv)

        with mock.patch.object(sys, "argv", ["vox", "clock", "--verbose"]):
            with mock.patch("horavox.config.get_aliases", return_value={}):
                with mock.patch("horavox.clock.main", side_effect=fake_main):
                    main()
        assert captured_argv == ["vox clock", "--verbose"]


# ==================== now.py ====================


class TestNowCommand:
    def test_debug_with_time(self):
        from horavox import now

        with mock.patch.object(
            sys, "argv", ["vox now", "--debug", "--time", "12:00", "--lang", "en"]
        ):
            with mock.patch.object(now, "speak") as mock_speak:
                now.main()
                mock_speak.assert_called_once()
                text = mock_speak.call_args[0][1]
                assert "noon" in text.lower()

    def test_debug_current_time(self):
        from horavox import now

        with mock.patch.object(sys, "argv", ["vox now", "--debug", "--lang", "en"]):
            with mock.patch.object(now, "speak") as mock_speak:
                now.main()
                mock_speak.assert_called_once()

    def test_modern_mode(self):
        from horavox import now

        with mock.patch.object(
            sys,
            "argv",
            ["vox now", "--debug", "--time", "9:30", "--mode", "modern", "--lang", "en"],
        ):
            with mock.patch.object(now, "speak") as mock_speak:
                now.main()
                text = mock_speak.call_args[0][1]
                assert text == "nine thirty"

    def test_nosound_flag(self):
        from horavox import now

        with mock.patch.object(sys, "argv", ["vox now", "--nosound", "--lang", "en"]):
            with mock.patch.object(now, "speak") as mock_speak:
                now.main()
                mock_speak.assert_called_once()

    def test_message_speaks_custom_text(self):
        from horavox import now

        with mock.patch.object(sys, "argv", ["vox now", "--debug", "-m", "Hello world"]):
            with mock.patch.object(now, "speak") as mock_speak:
                now.main()
                mock_speak.assert_called_once()
                text = mock_speak.call_args[0][1]
                assert text == "Hello world"

    def test_message_long_flag(self):
        from horavox import now

        with mock.patch.object(
            sys, "argv", ["vox now", "--debug", "--message", "Testing one two three"]
        ):
            with mock.patch.object(now, "speak") as mock_speak:
                now.main()
                text = mock_speak.call_args[0][1]
                assert text == "Testing one two three"

    def test_message_ignores_time_flag(self):
        from horavox import now

        with mock.patch.object(
            sys,
            "argv",
            ["vox now", "--debug", "--time", "12:00", "-m", "Custom", "--lang", "en"],
        ):
            with mock.patch.object(now, "speak") as mock_speak:
                now.main()
                text = mock_speak.call_args[0][1]
                assert text == "Custom"

    def test_keyboard_interrupt(self):
        from horavox import now

        with mock.patch.object(sys, "argv", ["vox now", "--debug"]):
            with mock.patch.object(now, "speak", side_effect=KeyboardInterrupt):
                now.main()  # should not raise

    def test_exception_logs_error(self):
        from horavox import now

        with mock.patch.object(sys, "argv", ["vox now", "--debug"]):
            with mock.patch.object(now, "speak", side_effect=RuntimeError("boom")):
                with mock.patch.object(now, "log_error") as mock_log:
                    with pytest.raises(RuntimeError):
                        now.main()
                    mock_log.assert_called_once()


# ==================== stop.py ====================


class TestListCommand:
    def test_list_pids(self, capsys):
        from horavox import list as list_cmd

        sessions = [
            ("/tmp/a.json", {"pid": 111, "command": "vox clock"}),
            ("/tmp/b.json", {"pid": 222, "command": "vox clock --freq 30"}),
        ]
        with mock.patch.object(sys, "argv", ["vox list"]):
            with mock.patch.object(list_cmd, "get_running_sessions", return_value=sessions):
                list_cmd.main()
        out = capsys.readouterr().out
        assert "111" in out
        assert "222" in out
        assert "vox clock" not in out  # no --verbose

    def test_list_verbose(self, capsys):
        from horavox import list as list_cmd

        sessions = [
            ("/tmp/a.json", {"pid": 111, "command": "vox clock --freq 30"}),
        ]
        with mock.patch.object(sys, "argv", ["vox list", "--verbose"]):
            with mock.patch.object(list_cmd, "get_running_sessions", return_value=sessions):
                list_cmd.main()
        out = capsys.readouterr().out
        assert "111" in out
        assert "vox clock --freq 30" in out

    def test_list_empty(self, capsys):
        from horavox import list as list_cmd

        with mock.patch.object(sys, "argv", ["vox list"]):
            with mock.patch.object(list_cmd, "get_running_sessions", return_value=[]):
                list_cmd.main()
        out = capsys.readouterr().out
        assert out.strip() == ""


class TestStopCommand:
    def test_pid_mode(self):
        from horavox import stop

        sessions = [
            ("/tmp/a.json", {"pid": 111, "command": "vox clock"}),
            ("/tmp/b.json", {"pid": 222, "command": "vox clock"}),
        ]
        with mock.patch.object(sys, "argv", ["vox stop", "--pid", "222"]):
            with mock.patch.object(stop, "get_running_sessions", return_value=sessions):
                with mock.patch.object(stop, "kill_session") as mock_kill:
                    stop.main()
                    mock_kill.assert_called_once_with(
                        "/tmp/b.json", {"pid": 222, "command": "vox clock"}
                    )

    def test_pid_not_found(self, capsys):
        from horavox import stop

        with mock.patch.object(sys, "argv", ["vox stop", "--pid", "999"]):
            with mock.patch.object(stop, "get_running_sessions", return_value=[]):
                with pytest.raises(SystemExit):
                    stop.main()
        out = capsys.readouterr().out
        assert "No HoraVox instance with PID 999" in out

    def test_no_instances(self, capsys):
        from horavox import stop

        with mock.patch.object(sys, "argv", ["vox stop"]):
            with mock.patch.object(stop, "get_running_sessions", return_value=[]):
                stop.main()
        out = capsys.readouterr().out
        assert "No HoraVox instances running" in out

    def test_single_instance_direct_kill(self):
        from horavox import stop

        sessions = [("/tmp/a.json", {"pid": 111, "command": "vox clock"})]
        with mock.patch.object(sys, "argv", ["vox stop"]):
            with mock.patch.object(stop, "get_running_sessions", return_value=sessions):
                with mock.patch.object(stop, "kill_session") as mock_kill:
                    stop.main()
                    mock_kill.assert_called_once()

    def test_keyboard_interrupt(self):
        from horavox import stop

        with mock.patch.object(sys, "argv", ["vox stop"]):
            with mock.patch.object(stop, "get_running_sessions", side_effect=KeyboardInterrupt):
                stop.main()  # should not raise

    def test_multiple_inquirer_stop_all(self):
        from horavox import stop

        sessions = [
            ("/tmp/a.json", {"pid": 111, "command": "vox clock"}),
            ("/tmp/b.json", {"pid": 222, "command": "vox clock"}),
        ]
        with mock.patch.object(sys, "argv", ["vox stop"]):
            with mock.patch.object(stop, "get_running_sessions", return_value=sessions):
                with mock.patch.object(stop, "kill_session") as mock_kill:
                    with mock.patch("inquirer.prompt", return_value={"session": "__all__"}):
                        stop.main()
                        assert mock_kill.call_count == 2

    def test_multiple_inquirer_stop_one(self):
        from horavox import stop

        sessions = [
            ("/tmp/a.json", {"pid": 111, "command": "vox clock"}),
            ("/tmp/b.json", {"pid": 222, "command": "vox clock"}),
        ]
        with mock.patch.object(sys, "argv", ["vox stop"]):
            with mock.patch.object(stop, "get_running_sessions", return_value=sessions):
                with mock.patch.object(stop, "kill_session") as mock_kill:
                    with mock.patch("inquirer.prompt", return_value={"session": "/tmp/b.json"}):
                        stop.main()
                        mock_kill.assert_called_once_with(
                            "/tmp/b.json", {"pid": 222, "command": "vox clock"}
                        )

    def test_multiple_inquirer_cancel(self):
        from horavox import stop

        sessions = [
            ("/tmp/a.json", {"pid": 111, "command": "vox clock"}),
            ("/tmp/b.json", {"pid": 222, "command": "vox clock"}),
        ]
        with mock.patch.object(sys, "argv", ["vox stop"]):
            with mock.patch.object(stop, "get_running_sessions", return_value=sessions):
                with mock.patch.object(stop, "kill_session") as mock_kill:
                    with mock.patch("inquirer.prompt", return_value=None):
                        stop.main()
                        mock_kill.assert_not_called()

    def test_multiple_inquirer_keyboard_interrupt(self):
        from horavox import stop

        sessions = [
            ("/tmp/a.json", {"pid": 111, "command": "vox clock"}),
            ("/tmp/b.json", {"pid": 222, "command": "vox clock"}),
        ]
        with mock.patch.object(sys, "argv", ["vox stop"]):
            with mock.patch.object(stop, "get_running_sessions", return_value=sessions):
                with mock.patch("inquirer.prompt", side_effect=KeyboardInterrupt):
                    stop.main()  # should not raise

    def test_parse_args(self):
        from horavox.stop import parse_args

        with mock.patch.object(sys, "argv", ["vox stop", "--pid", "123"]):
            args = parse_args()
        assert args.pid == 123


# ==================== clock.py ====================


class TestClockCommand:
    def test_debug_exit_at_slot(self):
        from horavox import clock

        with mock.patch.object(
            sys, "argv", ["vox clock", "--debug", "--exit", "--time", "12:00", "--lang", "en"]
        ):
            with mock.patch.object(clock, "prepare_speech") as mock_prep:
                with mock.patch.object(clock, "play_speech"):
                    with mock.patch.object(clock, "play_beep"):
                        clock.main()
                        mock_prep.assert_called_once()
                        text = mock_prep.call_args[0][1]
                        assert "noon" in text.lower()

    def test_debug_exit_not_at_slot(self, capsys):
        from horavox import clock

        with mock.patch.object(sys, "argv", ["vox clock", "--debug", "--exit", "--time", "12:01"]):
            with mock.patch.object(clock, "prepare_speech") as mock_prep:
                with mock.patch.object(clock, "play_speech"):
                    clock.main()
                    mock_prep.assert_not_called()
        out = capsys.readouterr().out
        assert "not at announcement slot" in out

    def test_debug_exit_outside_range(self, capsys):
        from horavox import clock

        with mock.patch.object(
            sys,
            "argv",
            ["vox clock", "--debug", "--exit", "--time", "12:00", "--start", "13", "--end", "23"],
        ):
            with mock.patch.object(clock, "prepare_speech") as mock_prep:
                with mock.patch.object(clock, "play_speech"):
                    clock.main()
                    mock_prep.assert_not_called()
        out = capsys.readouterr().out
        assert "outside range" in out

    def test_freq_30(self):
        from horavox import clock

        with mock.patch.object(
            sys, "argv", ["vox clock", "--debug", "--exit", "--time", "12:30", "--freq", "30"]
        ):
            with mock.patch.object(clock, "prepare_speech") as mock_prep:
                with mock.patch.object(clock, "play_speech"):
                    with mock.patch.object(clock, "play_beep"):
                        clock.main()
                        mock_prep.assert_called_once()

    def test_invalid_freq(self):
        from horavox import clock

        with mock.patch.object(sys, "argv", ["vox clock", "--debug", "--exit", "--freq", "7"]):
            with pytest.raises(SystemExit, match="must divide 60 evenly"):
                clock.main()

    def test_invalid_freq_too_high(self):
        from horavox import clock

        with mock.patch.object(sys, "argv", ["vox clock", "--debug", "--exit", "--freq", "99"]):
            with pytest.raises(SystemExit, match="must be 1-60"):
                clock.main()

    def test_modern_mode(self):
        from horavox import clock

        with mock.patch.object(
            sys,
            "argv",
            [
                "vox clock",
                "--debug",
                "--exit",
                "--time",
                "17:00",
                "--mode",
                "modern",
                "--lang",
                "pl",
            ],
        ):
            with mock.patch.object(clock, "prepare_speech") as mock_prep:
                with mock.patch.object(clock, "play_speech"):
                    with mock.patch.object(clock, "play_beep"):
                        clock.main()
                        text = mock_prep.call_args[0][1]
                        assert "siedemnasta" in text

    def test_keyboard_interrupt(self):
        from horavox import clock

        with mock.patch.object(sys, "argv", ["vox clock", "--debug", "--exit", "--time", "12:00"]):
            with mock.patch.object(clock, "prepare_speech", side_effect=KeyboardInterrupt):
                clock.main()  # should not raise

    def test_classic_12_hour(self):
        from horavox import clock

        with mock.patch.object(
            sys, "argv", ["vox clock", "--debug", "--exit", "--time", "17:00", "--lang", "pl"]
        ):
            with mock.patch.object(clock, "prepare_speech") as mock_prep:
                with mock.patch.object(clock, "play_speech"):
                    with mock.patch.object(clock, "play_beep"):
                        clock.main()
                        text = mock_prep.call_args[0][1]
                        assert "piąta" in text  # 12-hour idiomatic

    def test_beep_count_full_hour(self):
        from horavox import clock

        with mock.patch.object(
            sys, "argv", ["vox clock", "--debug", "--exit", "--time", "12:00", "--lang", "en"]
        ):
            with mock.patch.object(clock, "prepare_speech"):
                with mock.patch.object(clock, "play_speech"):
                    with mock.patch.object(clock, "play_beep") as mock_beep:
                        clock.main()
                        assert mock_beep.call_count == 2

    def test_beep_count_half_hour(self):
        from horavox import clock

        with mock.patch.object(
            sys, "argv", ["vox clock", "--debug", "--exit", "--time", "12:30", "--freq", "30"]
        ):
            with mock.patch.object(clock, "prepare_speech"):
                with mock.patch.object(clock, "play_speech"):
                    with mock.patch.object(clock, "play_beep") as mock_beep:
                        clock.main()
                        assert mock_beep.call_count == 1

    def test_background_mode(self):
        from horavox import clock

        with mock.patch.object(sys, "argv", ["vox clock", "--background", "--nosound"]):
            with mock.patch.object(clock, "Daemonize") as mock_daemon:
                mock_instance = mock.MagicMock()
                mock_daemon.return_value = mock_instance
                clock.main()
                mock_daemon.assert_called_once()
                mock_instance.start.assert_called_once()

    def test_run_clock_exit_mode_directly(self):
        """Test run_clock --exit path with a mock args object."""

        from horavox import clock as clock_mod
        from horavox.clock import run_clock

        core.configure(debug=True)
        lang_data, lang = core.load_language_data("en", "classic")
        args = mock.MagicMock()
        args.freq = 60
        args.exit = True
        args.time = "12:00"
        args.voice = None
        now = datetime.datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
        time_offset = now - datetime.datetime.now()
        with mock.patch.object(clock_mod, "prepare_speech") as mock_prep:
            with mock.patch.object(clock_mod, "play_speech"):
                with mock.patch.object(clock_mod, "play_beep"):
                    run_clock(args, lang, lang_data, time_offset, 0, 1439)
                    mock_prep.assert_called_once()

    def test_parse_args_defaults(self):
        from horavox.clock import parse_args

        with mock.patch.object(sys, "argv", ["vox clock"]):
            args = parse_args()
        assert args.freq == 60
        assert args.mode == "classic"
        assert args.volume == 100
        assert args.background is False

    def test_parse_args_all_options(self):
        from horavox.clock import parse_args

        with mock.patch.object(
            sys,
            "argv",
            [
                "vox clock",
                "--lang",
                "pl",
                "--voice",
                "test",
                "--mode",
                "modern",
                "--start",
                "9",
                "--end",
                "22",
                "--freq",
                "30",
                "--time",
                "12:00",
                "--exit",
                "--background",
                "--verbose",
                "--volume",
                "50",
            ],
        ):
            args = parse_args()
        assert args.lang == "pl"
        assert args.voice == "test"
        assert args.mode == "modern"
        assert args.freq == 30
        assert args.exit is True
        assert args.background is True

    def test_run_clock_loop_one_tick(self):
        """Test the main loop fires once then breaks via side effect."""

        from horavox import clock as clock_mod
        from horavox.clock import run_clock

        core.configure(debug=True)
        lang_data, lang = core.load_language_data("en", "classic")
        args = mock.MagicMock()
        args.freq = 60
        args.exit = False
        args.time = None
        args.voice = None
        # Set time to exactly 12:00:00 so the loop fires immediately
        now = datetime.datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
        time_offset = now - datetime.datetime.now()
        call_count = [0]

        def fake_sleep(t):
            call_count[0] += 1
            if call_count[0] > 3:
                raise KeyboardInterrupt

        with mock.patch.object(clock_mod, "prepare_speech"):
            with mock.patch.object(clock_mod, "prepare_combined_speech"):
                with mock.patch.object(clock_mod, "play_speech"):
                    with mock.patch.object(clock_mod, "play_beep"):
                        with mock.patch.object(clock_mod.time, "sleep", side_effect=fake_sleep):
                            try:
                                run_clock(args, lang, lang_data, time_offset, 0, 1439)
                            except KeyboardInterrupt:
                                pass
        assert call_count[0] > 0

    def test_exception_logs_error(self):
        from horavox import clock

        with mock.patch.object(sys, "argv", ["vox clock", "--debug", "--exit", "--time", "12:00"]):
            with mock.patch.object(clock, "prepare_speech", side_effect=RuntimeError("boom")):
                with mock.patch.object(clock, "log_error") as mock_log:
                    with pytest.raises(RuntimeError):
                        clock.main()
                    mock_log.assert_called_once()

    def test_mapping_speaks_combined(self):
        """When a mapping exists for the time, prepare_combined_speech is called."""
        from horavox import clock

        mapping_list = [{"time": "17:00", "message": "feed the cat"}]
        with mock.patch.object(
            sys, "argv", ["vox clock", "--debug", "--exit", "--time", "17:00", "--lang", "en"]
        ):
            with mock.patch("horavox.config.get_mapping", return_value=mapping_list):
                with mock.patch(
                    "horavox.config.load_config",
                    return_value={"settings": {}, "alias": {}, "mapping": []},
                ):
                    with mock.patch.object(clock, "prepare_combined_speech") as mock_comb:
                        with mock.patch.object(clock, "play_speech"):
                            with mock.patch.object(clock, "play_beep"):
                                clock.main()
                                mock_comb.assert_called_once()
                                texts = mock_comb.call_args[0][1]
                                assert len(texts) == 2
                                assert "feed the cat" in texts[1]

    def test_mapping_time_false_speaks_only_message(self):
        """With settings.mapping.time=false, only the message is spoken."""
        from horavox import clock

        mapping_list = [{"time": "17:00", "message": "feed the cat"}]
        with mock.patch.object(
            sys, "argv", ["vox clock", "--debug", "--exit", "--time", "17:00", "--lang", "en"]
        ):
            with mock.patch("horavox.config.get_mapping", return_value=mapping_list):
                with mock.patch(
                    "horavox.config.load_config",
                    return_value={
                        "settings": {"mapping": {"time": "false"}},
                        "alias": {},
                        "mapping": [],
                    },
                ):
                    with mock.patch.object(clock, "prepare_speech") as mock_prep:
                        with mock.patch.object(clock, "play_speech"):
                            with mock.patch.object(clock, "play_beep"):
                                clock.main()
                                mock_prep.assert_called_once()
                                text = mock_prep.call_args[0][1]
                                assert text == "feed the cat"

    def test_no_mapping_speaks_time_only(self):
        """Without mapping, normal prepare_speech is called with time text."""
        from horavox import clock

        with mock.patch.object(
            sys, "argv", ["vox clock", "--debug", "--exit", "--time", "12:00", "--lang", "en"]
        ):
            with mock.patch.object(clock, "prepare_speech") as mock_prep:
                with mock.patch.object(clock, "play_speech"):
                    with mock.patch.object(clock, "play_beep"):
                        clock.main()
                        mock_prep.assert_called_once()
                        text = mock_prep.call_args[0][1]
                        assert "noon" in text.lower()

    def test_mapping_with_date_matches_weekday(self):
        """Mapping with date field only fires on matching weekday."""
        from horavox import clock

        mapping_list = [{"time": "17:00", "message": "weekday msg", "date": ["weekdays"]}]
        with mock.patch.object(
            sys, "argv", ["vox clock", "--debug", "--exit", "--time", "17:00", "--lang", "en"]
        ):
            with mock.patch("horavox.config.get_mapping", return_value=mapping_list):
                with mock.patch(
                    "horavox.config.load_config",
                    return_value={"settings": {}, "alias": {}, "mapping": []},
                ):
                    with mock.patch.object(clock, "prepare_combined_speech") as mock_comb:
                        with mock.patch.object(clock, "prepare_speech") as mock_prep:
                            with mock.patch.object(clock, "play_speech"):
                                with mock.patch.object(clock, "play_beep"):
                                    clock.main()
                                    # One of them should be called depending on current weekday
                                    import datetime

                                    if datetime.datetime.now().weekday() < 5:
                                        mock_comb.assert_called_once()
                                    else:
                                        mock_prep.assert_called_once()

    def test_mapping_without_message_no_combined(self):
        """Mapping entry with time only (no message) just speaks the time."""
        from horavox import clock

        mapping_list = [{"time": "17:00"}]
        with mock.patch.object(
            sys, "argv", ["vox clock", "--debug", "--exit", "--time", "17:00", "--lang", "en"]
        ):
            with mock.patch("horavox.config.get_mapping", return_value=mapping_list):
                with mock.patch(
                    "horavox.config.load_config",
                    return_value={"settings": {}, "alias": {}, "mapping": []},
                ):
                    with mock.patch.object(clock, "prepare_speech") as mock_prep:
                        with mock.patch.object(clock, "play_speech"):
                            with mock.patch.object(clock, "play_beep"):
                                clock.main()
                                mock_prep.assert_called_once()

    def test_find_mapping_message_basic(self):
        from horavox.clock import _find_mapping_message

        mapping = [{"time": "17:00", "message": "feed the cat"}]
        assert _find_mapping_message(mapping, 17, 0, 0) == "feed the cat"

    def test_find_mapping_message_no_match(self):
        from horavox.clock import _find_mapping_message

        mapping = [{"time": "17:00", "message": "feed the cat"}]
        assert _find_mapping_message(mapping, 18, 0, 0) is None

    def test_find_mapping_message_empty(self):
        from horavox.clock import _find_mapping_message

        assert _find_mapping_message([], 17, 0, 0) is None

    def test_find_mapping_message_with_date_match(self):
        from horavox.clock import _find_mapping_message

        mapping = [{"time": "9:00", "message": "stand-up", "date": ["weekdays"]}]
        assert _find_mapping_message(mapping, 9, 0, 0) == "stand-up"  # Monday
        assert _find_mapping_message(mapping, 9, 0, 5) is None  # Saturday

    def test_find_mapping_message_no_date_always_matches(self):
        from horavox.clock import _find_mapping_message

        mapping = [{"time": "12:00", "message": "lunch"}]
        for weekday in range(7):
            assert _find_mapping_message(mapping, 12, 0, weekday) == "lunch"

    def test_find_mapping_message_no_message_field(self):
        from horavox.clock import _find_mapping_message

        mapping = [{"time": "17:00"}]
        assert _find_mapping_message(mapping, 17, 0, 0) is None

    def test_find_mapping_message_midnight_double_zero(self):
        # "00:00" must match midnight even though the clock builds "0:00"
        from horavox.clock import _find_mapping_message

        mapping = [{"time": "00:00", "message": "późno już"}]
        assert _find_mapping_message(mapping, 0, 0, 0) == "późno już"

    def test_find_mapping_message_leading_zero_hour(self):
        # single-digit hours written with a leading zero still match
        from horavox.clock import _find_mapping_message

        mapping = [{"time": "09:30", "message": "stand-up"}]
        assert _find_mapping_message(mapping, 9, 30, 0) == "stand-up"

    def test_find_mapping_message_malformed_time_ignored(self):
        from horavox.clock import _find_mapping_message

        mapping = [{"time": "not-a-time", "message": "x"}, {"time": "0:00", "message": "ok"}]
        assert _find_mapping_message(mapping, 0, 0, 0) == "ok"
        assert _find_mapping_message(mapping, 17, 0, 0) is None

    def test_service_foreground_creates_session(self, tmp_path):
        from horavox import clock

        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()

        with mock.patch.object(
            sys,
            "argv",
            ["vox clock", "--debug", "--exit", "--time", "12:00", "--lang", "en"],
        ):
            with mock.patch.dict(os.environ, {"HORAVOX_SERVICE": "1"}):
                with mock.patch.object(clock, "prepare_speech"):
                    with mock.patch.object(clock, "play_speech"):
                        with mock.patch.object(clock, "play_beep"):
                            with mock.patch("horavox.clock.SESSIONS_DIR", str(sessions_dir)):
                                with mock.patch("horavox.clock.ensure_user_dirs"):
                                    with mock.patch("horavox.clock.create_session") as mock_create:
                                        with mock.patch(
                                            "horavox.clock.remove_session"
                                        ) as mock_remove:
                                            clock.main()
                                            mock_create.assert_called_once()
                                            call_kwargs = mock_create.call_args
                                            assert call_kwargs[1]["session_type"] == "clock"
                                            mock_remove.assert_called_once()

    def test_service_foreground_creates_session_with_range(self, tmp_path):
        from horavox import clock

        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()

        with mock.patch.object(
            sys,
            "argv",
            [
                "vox clock",
                "--debug",
                "--exit",
                "--time",
                "12:00",
                "--lang",
                "en",
                "--start",
                "9:00",
                "--end",
                "22:00",
            ],
        ):
            with mock.patch.dict(os.environ, {"HORAVOX_SERVICE": "1"}):
                with mock.patch.object(clock, "prepare_speech"):
                    with mock.patch.object(clock, "play_speech"):
                        with mock.patch.object(clock, "play_beep"):
                            with mock.patch("horavox.clock.SESSIONS_DIR", str(sessions_dir)):
                                with mock.patch("horavox.clock.ensure_user_dirs"):
                                    with mock.patch("horavox.clock.create_session") as mock_create:
                                        with mock.patch("horavox.clock.remove_session"):
                                            clock.main()
                                            call_kwargs = mock_create.call_args
                                            assert call_kwargs[1]["start"] == "9:00"
                                            assert call_kwargs[1]["end"] == "22:00"


# ==================== config.py ====================


class TestConfigCommand:
    def setup_method(self):
        import tempfile

        self.tmpdir = tempfile.mkdtemp(prefix="horavox-test-cfg-")
        self.config_path = os.path.join(self.tmpdir, "config.json")
        self._patch_path = mock.patch("horavox.config.CONFIG_PATH", self.config_path)
        self._patch_user = mock.patch("horavox.config.USER_DIR", self.tmpdir)
        self._patch_path.start()
        self._patch_user.start()

    def teardown_method(self):
        self._patch_path.stop()
        self._patch_user.stop()

    def test_list_empty(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config"]):
            config.main()
        out = capsys.readouterr().out
        assert "No configuration set" in out

    def test_set_and_list(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "lang=pl"]):
            config.main()
        with mock.patch.object(sys, "argv", ["vox config"]):
            config.main()
        out = capsys.readouterr().out
        assert "lang=pl" in out

    def test_get_key(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "lang=en"]):
            config.main()
        with mock.patch.object(sys, "argv", ["vox config", "lang"]):
            config.main()
        out = capsys.readouterr().out
        assert "lang=en" in out

    def test_get_key_not_set(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "lang"]):
            config.main()
        out = capsys.readouterr().out
        assert "not set" in out

    def test_unset_key(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "lang=pl"]):
            config.main()
        with mock.patch.object(sys, "argv", ["vox config", "--unset", "lang"]):
            config.main()
        out = capsys.readouterr().out
        assert "Unset" in out

    def test_unset_key_not_set(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "--unset", "lang"]):
            config.main()
        out = capsys.readouterr().out
        assert "not set" in out

    def test_invalid_key(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "bogus=x"]):
            with pytest.raises(SystemExit):
                config.main()
        out = capsys.readouterr().out
        assert "unknown key" in out

    def test_invalid_key_get(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "bogus"]):
            with pytest.raises(SystemExit):
                config.main()
        out = capsys.readouterr().out
        assert "unknown key" in out

    def test_invalid_key_unset(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "--unset", "bogus"]):
            with pytest.raises(SystemExit):
                config.main()
        out = capsys.readouterr().out
        assert "unknown key" in out

    def test_invalid_mode_value(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "mode=invalid"]):
            with pytest.raises(SystemExit):
                config.main()
        out = capsys.readouterr().out
        assert "classic" in out and "modern" in out

    def test_invalid_volume_not_integer(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "volume=abc"]):
            with pytest.raises(SystemExit):
                config.main()
        out = capsys.readouterr().out
        assert "0-100" in out

    def test_invalid_volume_out_of_range(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "volume=150"]):
            with pytest.raises(SystemExit):
                config.main()
        out = capsys.readouterr().out
        assert "0-100" in out

    def test_invalid_volume_negative(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "volume=-1"]):
            with pytest.raises(SystemExit):
                config.main()
        out = capsys.readouterr().out
        assert "0-100" in out

    def test_set_volume(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "volume=30"]):
            config.main()
        out = capsys.readouterr().out
        assert "volume=30" in out

    def test_set_all_keys(self, capsys):
        from horavox import config

        for setting in ["lang=pl", "voice=test-voice", "mode=modern", "volume=50"]:
            with mock.patch.object(sys, "argv", ["vox config", setting]):
                config.main()
        with mock.patch.object(sys, "argv", ["vox config"]):
            config.main()
        out = capsys.readouterr().out
        assert "lang=pl" in out
        assert "voice=test-voice" in out
        assert "volume=50" in out
        assert "mode=modern" in out

    def test_keyboard_interrupt(self):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config"]):
            with mock.patch.object(config, "load_config", side_effect=KeyboardInterrupt):
                config.main()

    def test_exception_logs_error(self):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config"]):
            with mock.patch.object(config, "load_config", side_effect=RuntimeError("boom")):
                with mock.patch.object(config, "log_error") as mock_log:
                    with pytest.raises(RuntimeError):
                        config.main()
                    mock_log.assert_called_once()

    def test_set_alias_equals_form(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "alias.clock=--freq 30"]):
            config.main()
        out = capsys.readouterr().out
        assert "alias.clock=--freq 30" in out

    def test_set_alias_two_arg_form(self, capsys):
        from horavox import config

        with mock.patch.object(
            sys, "argv", ["vox config", "alias.clock", "--start 9 --end 1 --freq 30"]
        ):
            config.main()
        out = capsys.readouterr().out
        assert "alias.clock=--start 9 --end 1 --freq 30" in out

    def test_get_alias(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "alias.clock=--freq 30"]):
            config.main()
        with mock.patch.object(sys, "argv", ["vox config", "alias.clock"]):
            config.main()
        out = capsys.readouterr().out
        assert "alias.clock=--freq 30" in out

    def test_get_alias_not_set(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "alias.bogus"]):
            config.main()
        out = capsys.readouterr().out
        assert "not set" in out

    def test_unset_alias(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "alias.clock=--freq 30"]):
            config.main()
        with mock.patch.object(sys, "argv", ["vox config", "--unset", "alias.clock"]):
            config.main()
        out = capsys.readouterr().out
        assert "Unset" in out and "alias.clock" in out

    def test_unset_alias_not_set(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "--unset", "alias.bogus"]):
            config.main()
        out = capsys.readouterr().out
        assert "not set" in out

    def test_list_shows_aliases(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "lang=pl"]):
            config.main()
        with mock.patch.object(sys, "argv", ["vox config", "alias.clock=--freq 30"]):
            config.main()
        with mock.patch.object(sys, "argv", ["vox config"]):
            config.main()
        out = capsys.readouterr().out
        assert "lang=pl" in out
        assert "alias.clock=--freq 30" in out

    def test_set_deep_nested(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "a.b.c=deep"]):
            config.main()
        out = capsys.readouterr().out
        assert "a.b.c=deep" in out
        cfg = config.load_config()
        assert cfg["a"]["b"]["c"] == "deep"

    def test_get_deep_nested(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "a.b.c=deep"]):
            config.main()
        with mock.patch.object(sys, "argv", ["vox config", "a.b.c"]):
            config.main()
        out = capsys.readouterr().out
        assert "a.b.c=deep" in out

    def test_get_branch_node(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "a.b.c=1"]):
            config.main()
        with mock.patch.object(sys, "argv", ["vox config", "a.b.d=2"]):
            config.main()
        with mock.patch.object(sys, "argv", ["vox config", "a.b"]):
            config.main()
        out = capsys.readouterr().out
        assert "a.b.c=1" in out
        assert "a.b.d=2" in out

    def test_unset_deep_nested(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "a.b.c=deep"]):
            config.main()
        with mock.patch.object(sys, "argv", ["vox config", "--unset", "a.b.c"]):
            config.main()
        out = capsys.readouterr().out
        assert "Unset" in out
        cfg = config.load_config()
        assert "a" not in cfg

    def test_unset_cleans_empty_parents(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "a.b.c=1"]):
            config.main()
        with mock.patch.object(sys, "argv", ["vox config", "a.b.d=2"]):
            config.main()
        with mock.patch.object(sys, "argv", ["vox config", "--unset", "a.b.c"]):
            config.main()
        cfg = config.load_config()
        assert cfg["a"]["b"]["d"] == "2"
        assert "c" not in cfg["a"]["b"]

    def test_overwrite_nested_value(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "a.b=old"]):
            config.main()
        with mock.patch.object(sys, "argv", ["vox config", "a.b=new"]):
            config.main()
        cfg = config.load_config()
        assert cfg["a"]["b"] == "new"

    def test_set_through_existing_non_dict(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "a.b=leaf"]):
            config.main()
        with mock.patch.object(sys, "argv", ["vox config", "a.b.c=deep"]):
            config.main()
        cfg = config.load_config()
        assert cfg["a"]["b"]["c"] == "deep"

    def test_validate_setting_via_dot_path(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "settings.mode=invalid"]):
            with pytest.raises(SystemExit):
                config.main()
        out = capsys.readouterr().out
        assert "classic" in out and "modern" in out

    def test_validate_unknown_setting_via_dot_path(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "settings.bogus=x"]):
            with pytest.raises(SystemExit):
                config.main()
        out = capsys.readouterr().out
        assert "unknown setting" in out

    def test_list_shows_deep_nested(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "x.y.z=nested"]):
            config.main()
        with mock.patch.object(sys, "argv", ["vox config"]):
            config.main()
        out = capsys.readouterr().out
        assert "x.y.z=nested" in out

    def test_two_arg_form_deep_nested(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "a.b.c", "value with spaces"]):
            config.main()
        out = capsys.readouterr().out
        assert "a.b.c=value with spaces" in out

    def test_get_empty_branch(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "a.b"]):
            config.main()
        out = capsys.readouterr().out
        assert "not set" in out

    def test_dispatches_from_main(self):
        from horavox.main import main

        with mock.patch.object(sys, "argv", ["vox", "config"]):
            with mock.patch("horavox.config.main") as m:
                main()
                m.assert_called_once()

    def test_mapping_add(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "mapping.add", "17:00", "feed the cat"]):
            config.main()
        out = capsys.readouterr().out
        assert "17:00" in out
        assert "feed the cat" in out
        cfg = config.load_config()
        assert len(cfg["mapping"]) == 1
        assert cfg["mapping"][0]["time"] == "17:00"
        assert cfg["mapping"][0]["message"] == "feed the cat"

    def test_mapping_add_with_date(self, capsys):
        from horavox import config

        with mock.patch.object(
            sys,
            "argv",
            ["vox config", "mapping.add", "9:00", "stand-up", "--date", "weekdays"],
        ):
            config.main()
        cfg = config.load_config()
        assert cfg["mapping"][0]["date"] == ["weekdays"]
        assert cfg["mapping"][0]["message"] == "stand-up"

    def test_mapping_add_with_multiple_dates(self, capsys):
        from horavox import config

        with mock.patch.object(
            sys,
            "argv",
            [
                "vox config",
                "mapping.add",
                "8:00",
                "weekend run",
                "--date",
                "saturday,sunday",
            ],
        ):
            config.main()
        cfg = config.load_config()
        assert cfg["mapping"][0]["date"] == ["saturday", "sunday"]

    def test_mapping_add_time_only(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "mapping.add", "12:00"]):
            config.main()
        cfg = config.load_config()
        assert cfg["mapping"][0] == {"time": "12:00"}

    def test_mapping_add_invalid_date(self):
        from horavox import config

        with mock.patch.object(
            sys,
            "argv",
            ["vox config", "mapping.add", "9:00", "msg", "--date", "bogus"],
        ):
            with pytest.raises(SystemExit):
                config.main()

    def test_mapping_delete_by_index(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "mapping.add", "17:00", "feed the cat"]):
            config.main()
        with mock.patch.object(sys, "argv", ["vox config", "--unset", "mapping.0"]):
            config.main()
        cfg = config.load_config()
        assert len(cfg["mapping"]) == 0

    def test_mapping_list(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "mapping.add", "17:00", "feed the cat"]):
            config.main()
        with mock.patch.object(sys, "argv", ["vox config", "mapping"]):
            config.main()
        out = capsys.readouterr().out
        assert "17:00" in out
        assert "feed the cat" in out

    def test_mapping_shows_in_list_all(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "mapping.add", "17:00", "feed the cat"]):
            config.main()
        with mock.patch.object(sys, "argv", ["vox config"]):
            config.main()
        out = capsys.readouterr().out
        assert "Mapping:" in out
        assert "17:00" in out

    def test_get_mapping_function(self):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "mapping.add", "9:00", "stand-up"]):
            config.main()
        mapping = config.get_mapping()
        assert len(mapping) == 1
        assert mapping[0]["time"] == "9:00"
        assert mapping[0]["message"] == "stand-up"

    def test_set_mapping_time_setting(self, capsys):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "settings.mapping.time=false"]):
            config.main()
        cfg = config.load_config()
        assert cfg["settings"]["mapping"]["time"] == "false"

    def test_mapping_time_invalid_value(self):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "settings.mapping.time=yes"]):
            with pytest.raises(SystemExit):
                config.main()

    def test_mapping_add_no_args(self):
        from horavox import config

        with mock.patch.object(sys, "argv", ["vox config", "mapping.add"]):
            with pytest.raises(SystemExit):
                config.main()

    def test_mapping_migrate_dict_to_list(self):
        import json

        from horavox import config

        with open(self.config_path, "w") as f:
            json.dump(
                {
                    "settings": {},
                    "alias": {},
                    "mapping": {"17:00": "feed the cat"},
                },
                f,
            )
        cfg = config.load_config()
        assert isinstance(cfg["mapping"], list)
        assert cfg["mapping"][0]["time"] == "17:00"
        assert cfg["mapping"][0]["message"] == "feed the cat"


class TestAliasDispatch:
    def setup_method(self):
        import tempfile

        self.tmpdir = tempfile.mkdtemp(prefix="horavox-test-alias-")
        self.config_path = os.path.join(self.tmpdir, "config.json")
        self._patch_path = mock.patch("horavox.config.CONFIG_PATH", self.config_path)
        self._patch_user = mock.patch("horavox.config.USER_DIR", self.tmpdir)
        self._patch_path.start()
        self._patch_user.start()

    def teardown_method(self):
        self._patch_path.stop()
        self._patch_user.stop()

    def _write_config(self, data):
        import json

        os.makedirs(self.tmpdir, exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(data, f)

    def test_alias_injects_args(self):
        self._write_config({"settings": {}, "alias": {"now": "--lang en"}})
        captured_argv = []

        def fake_main():
            captured_argv.extend(sys.argv)

        from horavox.main import main

        with mock.patch.object(sys, "argv", ["vox", "now", "--debug", "--time", "12:00"]):
            with mock.patch("horavox.now.main", side_effect=fake_main):
                main()
        assert captured_argv == ["vox now", "--lang", "en", "--debug", "--time", "12:00"]

    def test_alias_cli_overrides(self):
        self._write_config({"settings": {}, "alias": {"now": "--lang en"}})
        captured_argv = []

        def fake_main():
            captured_argv.extend(sys.argv)

        from horavox.main import main

        with mock.patch.object(sys, "argv", ["vox", "now", "--lang", "pl"]):
            with mock.patch("horavox.now.main", side_effect=fake_main):
                main()
        # alias --lang en comes first, but CLI --lang pl comes last and wins in argparse
        assert "--lang" in captured_argv
        last_lang_idx = len(captured_argv) - 1 - captured_argv[::-1].index("--lang")
        assert captured_argv[last_lang_idx + 1] == "pl"

    def test_no_alias_no_injection(self):
        self._write_config({"settings": {}, "alias": {}})
        captured_argv = []

        def fake_main():
            captured_argv.extend(sys.argv)

        from horavox.main import main

        with mock.patch.object(sys, "argv", ["vox", "now", "--debug"]):
            with mock.patch("horavox.now.main", side_effect=fake_main):
                main()
        assert captured_argv == ["vox now", "--debug"]

    def test_alias_for_different_command(self):
        self._write_config({"settings": {}, "alias": {"clock": "--freq 30"}})
        captured_argv = []

        def fake_main():
            captured_argv.extend(sys.argv)

        from horavox.main import main

        with mock.patch.object(sys, "argv", ["vox", "now", "--debug"]):
            with mock.patch("horavox.now.main", side_effect=fake_main):
                main()
        # clock alias should not affect now command
        assert captured_argv == ["vox now", "--debug"]

    def test_alias_preserves_quoted_values(self):
        self._write_config({"settings": {}, "alias": {"now": "--message 'hello world'"}})
        captured_argv = []

        def fake_main():
            captured_argv.extend(sys.argv)

        from horavox.main import main

        with mock.patch.object(sys, "argv", ["vox", "now"]):
            with mock.patch("horavox.now.main", side_effect=fake_main):
                main()
        assert captured_argv == ["vox now", "--message", "hello world"]

    def test_service_strips_background_from_alias(self):
        self._write_config(
            {"settings": {}, "alias": {"clock": "--start 9 --end 1 --background --freq 30"}}
        )
        captured_argv = []

        def fake_main():
            captured_argv.extend(sys.argv)

        from horavox.main import main

        with mock.patch.dict(os.environ, {"HORAVOX_SERVICE": "1"}):
            with mock.patch.object(sys, "argv", ["vox", "clock", "--lang", "pl"]):
                with mock.patch("horavox.clock.main", side_effect=fake_main):
                    main()
        assert "--background" not in captured_argv
        assert "--start" in captured_argv
        assert "--freq" in captured_argv

    def test_new_command_alias_expands_to_builtin(self):
        # git-style: 'nap' is not a builtin; its value's first token is the command
        self._write_config({"settings": {}, "alias": {"nap": "timer 30m --message 'wstawaj'"}})
        captured_argv = []

        def fake_main():
            captured_argv.extend(sys.argv)

        from horavox.main import main

        with mock.patch.object(sys, "argv", ["vox", "nap"]):
            with mock.patch("horavox.timer.main", side_effect=fake_main):
                with mock.patch("horavox.update.check_for_update"):
                    main()
        assert captured_argv == ["vox timer", "30m", "--message", "wstawaj"]

    def test_new_command_alias_appends_user_args(self):
        self._write_config({"settings": {}, "alias": {"nap": "timer 30m -m 'wstawaj'"}})
        captured_argv = []

        def fake_main():
            captured_argv.extend(sys.argv)

        from horavox.main import main

        with mock.patch.object(sys, "argv", ["vox", "nap", "--volume", "50"]):
            with mock.patch("horavox.timer.main", side_effect=fake_main):
                with mock.patch("horavox.update.check_for_update"):
                    main()
        assert captured_argv == ["vox timer", "30m", "-m", "wstawaj", "--volume", "50"]

    def test_alias_named_like_builtin_injects_not_expands(self):
        # An alias whose name IS a builtin injects default args (never expands)
        self._write_config({"settings": {}, "alias": {"now": "--lang en"}})
        captured_argv = []

        def fake_main():
            captured_argv.extend(sys.argv)

        from horavox.main import main

        with mock.patch.object(sys, "argv", ["vox", "now"]):
            with mock.patch("horavox.now.main", side_effect=fake_main):
                with mock.patch("horavox.update.check_for_update"):
                    main()
        assert captured_argv == ["vox now", "--lang", "en"]

    def test_empty_alias_errors(self):
        self._write_config({"settings": {}, "alias": {"nap": ""}})
        from horavox.main import main

        with mock.patch.object(sys, "argv", ["vox", "nap"]):
            with mock.patch("horavox.update.check_for_update"):
                with pytest.raises(SystemExit):
                    main()

    def test_unknown_non_alias_still_errors(self):
        self._write_config({"settings": {}, "alias": {"nap": "timer 30m"}})
        from horavox.main import main

        with mock.patch.object(sys, "argv", ["vox", "bogus"]):
            with mock.patch("horavox.main.shutil.which", return_value=None):
                with mock.patch("horavox.update.check_for_update"):
                    with pytest.raises(SystemExit):
                        main()

    def test_shell_alias_runs_via_sh_with_args(self):
        # git-style: '!cmd' runs a shell command; CLI args become "$@"
        self._write_config({"settings": {}, "alias": {"greet": "!echo hi"}})
        from horavox.main import main

        with mock.patch.object(sys, "argv", ["vox", "greet", "a", "b"]):
            with mock.patch("horavox.main.subprocess.run") as run:
                run.return_value = mock.Mock(returncode=0)
                with mock.patch("horavox.update.check_for_update"):
                    with pytest.raises(SystemExit) as exc:
                        main()
        run.assert_called_once_with(["sh", "-c", 'echo hi "$@"', "greet", "a", "b"])
        assert exc.value.code == 0

    def test_shell_alias_function_pattern(self):
        # the common !f() { ...; }; f pattern
        body = 'f() { echo "$1"; }; f'
        self._write_config({"settings": {}, "alias": {"fn": "!" + body}})
        from horavox.main import main

        with mock.patch.object(sys, "argv", ["vox", "fn", "x"]):
            with mock.patch("horavox.main.subprocess.run") as run:
                run.return_value = mock.Mock(returncode=0)
                with mock.patch("horavox.update.check_for_update"):
                    with pytest.raises(SystemExit):
                        main()
        run.assert_called_once_with(["sh", "-c", f'{body} "$@"', "fn", "x"])

    def test_shell_alias_exit_code_propagates(self):
        self._write_config({"settings": {}, "alias": {"boom": "!false"}})
        from horavox.main import main

        with mock.patch.object(sys, "argv", ["vox", "boom"]):
            with mock.patch("horavox.main.subprocess.run") as run:
                run.return_value = mock.Mock(returncode=3)
                with mock.patch("horavox.update.check_for_update"):
                    with pytest.raises(SystemExit) as exc:
                        main()
        assert exc.value.code == 3

    def test_empty_shell_alias_errors(self, capsys):
        self._write_config({"settings": {}, "alias": {"x": "!  "}})
        from horavox.main import main

        with mock.patch.object(sys, "argv", ["vox", "x"]):
            with mock.patch("horavox.update.check_for_update"):
                with pytest.raises(SystemExit) as exc:
                    main()
        assert exc.value.code == 1
        assert "empty" in capsys.readouterr().out

    def test_service_strips_background_from_explicit_args(self):
        self._write_config({"settings": {}, "alias": {}})
        captured_argv = []

        def fake_main():
            captured_argv.extend(sys.argv)

        from horavox.main import main

        with mock.patch.dict(os.environ, {"HORAVOX_SERVICE": "1"}):
            with mock.patch.object(sys, "argv", ["vox", "clock", "--background", "--lang", "pl"]):
                with mock.patch("horavox.clock.main", side_effect=fake_main):
                    main()
        assert "--background" not in captured_argv
        assert "--lang" in captured_argv


class TestApplyConfig:
    def setup_method(self):
        import tempfile

        self.tmpdir = tempfile.mkdtemp(prefix="horavox-test-cfg-")
        self.config_path = os.path.join(self.tmpdir, "config.json")
        self._patch_path = mock.patch("horavox.config.CONFIG_PATH", self.config_path)
        self._patch_user = mock.patch("horavox.config.USER_DIR", self.tmpdir)
        self._patch_path.start()
        self._patch_user.start()

    def teardown_method(self):
        self._patch_path.stop()
        self._patch_user.stop()

    def _write_config(self, data):
        import json

        os.makedirs(self.tmpdir, exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(data, f)

    def test_applies_lang(self):
        from horavox.config import apply_config

        self._write_config({"settings": {"lang": "pl"}, "alias": {}})
        args = argparse.Namespace(lang=None, voice=None, mode="classic")
        with mock.patch.object(sys, "argv", ["vox", "now"]):
            apply_config(args)
        assert args.lang == "pl"

    def test_applies_voice(self):
        from horavox.config import apply_config

        self._write_config({"settings": {"voice": "test-voice"}, "alias": {}})
        args = argparse.Namespace(lang=None, voice=None, mode="classic")
        with mock.patch.object(sys, "argv", ["vox", "now"]):
            apply_config(args)
        assert args.voice == "test-voice"

    def test_applies_mode(self):
        from horavox.config import apply_config

        self._write_config({"settings": {"mode": "modern"}, "alias": {}})
        args = argparse.Namespace(lang=None, voice=None, mode="classic")
        with mock.patch.object(sys, "argv", ["vox", "now"]):
            apply_config(args)
        assert args.mode == "modern"

    def test_cli_lang_overrides_config(self):
        from horavox.config import apply_config

        self._write_config({"settings": {"lang": "pl"}, "alias": {}})
        args = argparse.Namespace(lang="en", voice=None, mode="classic")
        with mock.patch.object(sys, "argv", ["vox", "now", "--lang", "en"]):
            apply_config(args)
        assert args.lang == "en"

    def test_cli_voice_overrides_config(self):
        from horavox.config import apply_config

        self._write_config({"settings": {"voice": "config-voice"}, "alias": {}})
        args = argparse.Namespace(lang=None, voice="cli-voice", mode="classic")
        with mock.patch.object(sys, "argv", ["vox", "now", "--voice", "cli-voice"]):
            apply_config(args)
        assert args.voice == "cli-voice"

    def test_cli_mode_overrides_config(self):
        from horavox.config import apply_config

        self._write_config({"settings": {"mode": "modern"}, "alias": {}})
        args = argparse.Namespace(lang=None, voice=None, mode="classic")
        with mock.patch.object(sys, "argv", ["vox", "now", "--mode", "classic"]):
            apply_config(args)
        assert args.mode == "classic"

    def test_no_config_file(self):
        from horavox.config import apply_config

        args = argparse.Namespace(lang=None, voice=None, mode="classic")
        with mock.patch.object(sys, "argv", ["vox", "now"]):
            apply_config(args)
        assert args.lang is None
        assert args.voice is None
        assert args.mode == "classic"

    def test_partial_config(self):
        from horavox.config import apply_config

        self._write_config({"settings": {"lang": "pl"}, "alias": {}})
        args = argparse.Namespace(lang=None, voice=None, mode="classic")
        with mock.patch.object(sys, "argv", ["vox", "now"]):
            apply_config(args)
        assert args.lang == "pl"
        assert args.voice is None
        assert args.mode == "classic"

    def test_applies_volume(self):
        from horavox.config import apply_config

        self._write_config({"settings": {"volume": "30"}, "alias": {}})
        args = argparse.Namespace(lang=None, voice=None, mode="classic", volume=100)
        with mock.patch.object(sys, "argv", ["vox", "now"]):
            apply_config(args)
        assert args.volume == 30

    def test_cli_volume_overrides_config(self):
        from horavox.config import apply_config

        self._write_config({"settings": {"volume": "30"}, "alias": {}})
        args = argparse.Namespace(lang=None, voice=None, mode="classic", volume=80)
        with mock.patch.object(sys, "argv", ["vox", "now", "--volume", "80"]):
            apply_config(args)
        assert args.volume == 80

    def test_migrates_flat_format(self):
        from horavox.config import apply_config

        self._write_config({"lang": "pl", "voice": "test"})
        args = argparse.Namespace(lang=None, voice=None, mode="classic")
        with mock.patch.object(sys, "argv", ["vox", "now"]):
            apply_config(args)
        assert args.lang == "pl"
        assert args.voice == "test"


# ==================== at.py ====================


class TestAtCommand:
    def test_debug_exit_at_scheduled_time(self):
        from horavox import at

        with mock.patch.object(
            sys,
            "argv",
            [
                "vox at",
                "9:00,12:00,18:00",
                "--repeat",
                "everyday",
                "--debug",
                "--exit",
                "--time",
                "12:00",
                "--lang",
                "en",
            ],
        ):
            with mock.patch.object(at, "speak") as mock_speak:
                at.main()
                mock_speak.assert_called_once()
                text = mock_speak.call_args[0][1]
                assert "noon" in text.lower()

    def test_debug_exit_not_at_scheduled_time(self, capsys):
        from horavox import at

        with mock.patch.object(
            sys,
            "argv",
            [
                "vox at",
                "9:00,12:00,18:00",
                "--repeat",
                "everyday",
                "--debug",
                "--exit",
                "--time",
                "12:01",
            ],
        ):
            with mock.patch.object(at, "speak") as mock_speak:
                at.main()
                mock_speak.assert_not_called()
        out = capsys.readouterr().out
        assert "not at a scheduled time" in out

    def test_debug_exit_shows_schedule(self, capsys):
        from horavox import at

        with mock.patch.object(
            sys,
            "argv",
            [
                "vox at",
                "9:00,18:00",
                "--repeat",
                "everyday",
                "--debug",
                "--exit",
                "--time",
                "10:00",
            ],
        ):
            at.main()
        out = capsys.readouterr().out
        assert "9:00" in out
        assert "18:00" in out

    def test_debug_exit_first_time(self):
        from horavox import at

        with mock.patch.object(
            sys,
            "argv",
            [
                "vox at",
                "9:00,12:00",
                "--repeat",
                "everyday",
                "--debug",
                "--exit",
                "--time",
                "9:00",
                "--lang",
                "en",
            ],
        ):
            with mock.patch.object(at, "speak") as mock_speak:
                at.main()
                mock_speak.assert_called_once()

    def test_debug_exit_last_time(self):
        from horavox import at

        with mock.patch.object(
            sys,
            "argv",
            [
                "vox at",
                "9:00,18:00",
                "--repeat",
                "everyday",
                "--debug",
                "--exit",
                "--time",
                "18:00",
                "--lang",
                "en",
            ],
        ):
            with mock.patch.object(at, "speak") as mock_speak:
                at.main()
                mock_speak.assert_called_once()

    def test_single_time(self):
        from horavox import at

        with mock.patch.object(
            sys, "argv", ["vox at", "12:00", "--debug", "--exit", "--time", "12:00", "--lang", "en"]
        ):
            with mock.patch.object(at, "speak") as mock_speak:
                at.main()
                mock_speak.assert_called_once()

    def test_modern_mode(self):
        from horavox import at

        with mock.patch.object(
            sys,
            "argv",
            [
                "vox at",
                "17:00",
                "--repeat",
                "everyday",
                "--debug",
                "--exit",
                "--time",
                "17:00",
                "--mode",
                "modern",
                "--lang",
                "pl",
            ],
        ):
            with mock.patch.object(at, "speak") as mock_speak:
                at.main()
                text = mock_speak.call_args[0][1]
                assert "siedemnasta" in text

    def test_message_option_speaks_custom_text(self):
        from horavox import at

        with mock.patch.object(
            sys,
            "argv",
            [
                "vox at",
                "12:00",
                "--repeat",
                "everyday",
                "--debug",
                "--exit",
                "--time",
                "12:00",
                "--message",
                "Time for lunch",
            ],
        ):
            with mock.patch.object(at, "speak") as mock_speak:
                at.main()
                mock_speak.assert_called_once()
                text = mock_speak.call_args[0][1]
                assert text == "Time for lunch"

    def test_message_short_flag(self):
        from horavox import at

        with mock.patch.object(
            sys,
            "argv",
            [
                "vox at",
                "12:00",
                "--debug",
                "--exit",
                "--time",
                "12:00",
                "-m",
                "Hello world",
            ],
        ):
            with mock.patch.object(at, "speak") as mock_speak:
                at.main()
                mock_speak.assert_called_once()
                text = mock_speak.call_args[0][1]
                assert text == "Hello world"

    def test_message_oneshot_exit(self):
        from horavox import at

        with mock.patch.object(
            sys,
            "argv",
            ["vox at", "12:00", "--debug", "--exit", "--time", "12:00", "-m", "Reminder"],
        ):
            with mock.patch.object(at, "speak") as mock_speak:
                at.main()
                text = mock_speak.call_args[0][1]
                assert text == "Reminder"

    def test_no_message_speaks_time(self):
        from horavox import at

        with mock.patch.object(
            sys,
            "argv",
            [
                "vox at",
                "12:00",
                "--repeat",
                "everyday",
                "--debug",
                "--exit",
                "--time",
                "12:00",
                "--lang",
                "en",
            ],
        ):
            with mock.patch.object(at, "speak") as mock_speak:
                at.main()
                text = mock_speak.call_args[0][1]
                assert "noon" in text.lower()

    def test_message_repeat_loop(self):
        """--message in the repeat main loop (not --exit) speaks custom text."""

        from horavox import at as at_mod
        from horavox.at import run_at_repeat

        core.configure(debug=True)
        lang_data, lang = core.load_language_data("en", "classic")
        args = mock.MagicMock()
        args.exit = False
        args.time = None
        args.voice = None
        args.message = "Take a break"
        schedule = [(12, 0)]
        repeat_days = set(range(7))
        now = datetime.datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
        time_offset = now - datetime.datetime.now()
        call_count = [0]

        def fake_sleep(t):
            call_count[0] += 1
            if call_count[0] > 3:
                raise KeyboardInterrupt

        with mock.patch.object(at_mod, "speak"):
            with mock.patch.object(at_mod, "prepare_speech") as mock_prep:
                with mock.patch.object(at_mod, "play_speech"):
                    with mock.patch.object(at_mod, "play_beep"):
                        with mock.patch.object(at_mod.time, "sleep", side_effect=fake_sleep):
                            try:
                                run_at_repeat(
                                    args, lang, lang_data, time_offset, schedule, repeat_days
                                )
                            except KeyboardInterrupt:
                                pass
        if mock_prep.call_count > 0:
            text = mock_prep.call_args[0][1]
            assert text == "Take a break"

    def test_get_text_with_message(self):
        from horavox.at import _get_text

        args = mock.MagicMock()
        args.message = "Hello world"
        assert _get_text(args, {}, 12, 0) == "Hello world"

    def test_get_text_without_message(self):
        from horavox.at import _get_text

        lang_data, _ = core.load_language_data("en", "classic")
        args = mock.MagicMock()
        args.message = None
        text = _get_text(args, lang_data, 12, 0)
        assert "noon" in text.lower()

    def test_keyboard_interrupt(self):
        from horavox import at

        with mock.patch.object(
            sys, "argv", ["vox at", "12:00", "--debug", "--exit", "--time", "12:00"]
        ):
            with mock.patch.object(at, "speak", side_effect=KeyboardInterrupt):
                at.main()

    def test_exception_logs_error(self):
        from horavox import at

        with mock.patch.object(
            sys, "argv", ["vox at", "12:00", "--debug", "--exit", "--time", "12:00"]
        ):
            with mock.patch.object(at, "speak", side_effect=RuntimeError("boom")):
                with mock.patch.object(at, "log_error") as mock_log:
                    with pytest.raises(RuntimeError):
                        at.main()
                    mock_log.assert_called_once()

    def test_parse_times_sorted(self):
        from horavox.at import parse_times

        result = parse_times("18:00,9:00,12:00")
        assert result == [(9, 0), (12, 0), (18, 0)]

    def test_parse_times_deduplicates(self):
        from horavox.at import parse_times

        result = parse_times("12:00,12:00,9:00")
        assert result == [(9, 0), (12, 0)]

    def test_parse_times_single(self):
        from horavox.at import parse_times

        result = parse_times("9:30")
        assert result == [(9, 30)]

    def test_parse_times_with_spaces(self):
        from horavox.at import parse_times

        result = parse_times("9:00, 12:00, 18:00")
        assert result == [(9, 0), (12, 0), (18, 0)]

    def test_parse_times_empty_error(self):
        from horavox.at import parse_times

        with pytest.raises(SystemExit):
            parse_times("")

    def test_parse_args_basic(self):
        from horavox.at import parse_args

        with mock.patch.object(sys, "argv", ["vox at", "9:00,12:00"]):
            args = parse_args()
        assert args.times == "9:00,12:00"
        assert args.mode == "classic"
        assert args.volume == 100
        assert args.repeat is None
        assert args.date is None

    def test_parse_args_with_date(self):
        from horavox.at import parse_args

        with mock.patch.object(sys, "argv", ["vox at", "9:00", "--date", "2026-05-10"]):
            args = parse_args()
        assert args.times == "9:00"
        assert args.date == "2026-05-10"

    def test_parse_args_with_repeat(self):
        from horavox.at import parse_args

        with mock.patch.object(sys, "argv", ["vox at", "12:55", "--repeat", "sunday,wednesday"]):
            args = parse_args()
        assert args.times == "12:55"
        assert args.repeat == "sunday,wednesday"

    def test_parse_args_all_options(self):
        from horavox.at import parse_args

        with mock.patch.object(
            sys,
            "argv",
            [
                "vox at",
                "9:00",
                "--lang",
                "pl",
                "--voice",
                "test",
                "--mode",
                "modern",
                "--time",
                "9:00",
                "--exit",
                "--background",
                "--verbose",
                "--volume",
                "50",
                "--repeat",
                "everyday",
            ],
        ):
            args = parse_args()
        assert args.times == "9:00"
        assert args.lang == "pl"
        assert args.voice == "test"
        assert args.mode == "modern"
        assert args.exit is True
        assert args.background is True
        assert args.volume == 50
        assert args.repeat == "everyday"

    def test_background_mode_oneshot(self):
        from horavox import at

        with mock.patch.object(sys, "argv", ["vox at", "12:00", "--background", "--nosound"]):
            with mock.patch.object(at, "Daemonize") as mock_daemon:
                mock_instance = mock.MagicMock()
                mock_daemon.return_value = mock_instance
                at.main()
                mock_daemon.assert_called_once()
                mock_instance.start.assert_called_once()

    def test_background_mode_repeat(self):
        from horavox import at

        with mock.patch.object(
            sys, "argv", ["vox at", "12:00", "--repeat", "everyday", "--background", "--nosound"]
        ):
            with mock.patch.object(at, "Daemonize") as mock_daemon:
                mock_instance = mock.MagicMock()
                mock_daemon.return_value = mock_instance
                at.main()
                mock_daemon.assert_called_once()
                mock_instance.start.assert_called_once()

    def test_run_at_repeat_loop_fires(self):
        """Test the repeat loop fires at a scheduled time then breaks."""

        from horavox import at as at_mod
        from horavox.at import run_at_repeat

        core.configure(debug=True)
        lang_data, lang = core.load_language_data("en", "classic")
        args = mock.MagicMock()
        args.exit = False
        args.time = None
        args.voice = None
        schedule = [(12, 0)]
        repeat_days = set(range(7))
        now = datetime.datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
        time_offset = now - datetime.datetime.now()
        call_count = [0]

        def fake_sleep(t):
            call_count[0] += 1
            if call_count[0] > 3:
                raise KeyboardInterrupt

        with mock.patch.object(at_mod, "speak"):
            with mock.patch.object(at_mod, "prepare_speech"):
                with mock.patch.object(at_mod, "play_speech"):
                    with mock.patch.object(at_mod, "play_beep"):
                        with mock.patch.object(at_mod.time, "sleep", side_effect=fake_sleep):
                            try:
                                run_at_repeat(
                                    args, lang, lang_data, time_offset, schedule, repeat_days
                                )
                            except KeyboardInterrupt:
                                pass
        assert call_count[0] > 0

    def test_parse_repeat_single_day(self):
        from horavox.at import parse_repeat

        assert parse_repeat("monday") == {0}

    def test_parse_repeat_multiple_days(self):
        from horavox.at import parse_repeat

        assert parse_repeat("sunday,wednesday") == {2, 6}

    def test_parse_repeat_everyday(self):
        from horavox.at import parse_repeat

        assert parse_repeat("everyday") == set(range(7))

    def test_parse_repeat_weekdays(self):
        from horavox.at import parse_repeat

        assert parse_repeat("weekdays") == {0, 1, 2, 3, 4}

    def test_parse_repeat_weekends(self):
        from horavox.at import parse_repeat

        assert parse_repeat("weekends") == {5, 6}

    def test_parse_repeat_invalid(self):
        from horavox.at import parse_repeat

        with pytest.raises(SystemExit):
            parse_repeat("bogus")

    def test_parse_repeat_empty(self):
        from horavox.at import parse_repeat

        with pytest.raises(SystemExit):
            parse_repeat("")

    def test_parse_date_valid(self):

        from horavox.at import parse_date

        assert parse_date("2026-05-10") == datetime.date(2026, 5, 10)

    def test_parse_date_invalid(self):
        from horavox.at import parse_date

        with pytest.raises(SystemExit):
            parse_date("not-a-date")

    def test_parse_date_values_exact_date(self):

        from horavox.at import parse_date_values

        result = parse_date_values("2026-05-10")
        assert result == [datetime.date(2026, 5, 10)]

    def test_parse_date_values_multiple_dates(self):

        from horavox.at import parse_date_values

        result = parse_date_values("2026-05-10,2026-05-12")
        assert result == [datetime.date(2026, 5, 10), datetime.date(2026, 5, 12)]

    def test_parse_date_values_day_name(self):

        from horavox.at import parse_date_values

        result = parse_date_values("monday")
        assert len(result) == 1
        assert result[0].weekday() == 0
        assert result[0] > datetime.date.today()

    def test_parse_date_values_mixed(self):

        from horavox.at import parse_date_values

        result = parse_date_values("friday,2026-12-25")
        assert len(result) == 2
        friday = [d for d in result if d.weekday() == 4][0]
        assert friday > datetime.date.today()
        assert datetime.date(2026, 12, 25) in result

    def test_parse_date_values_empty_error(self):
        from horavox.at import parse_date_values

        with pytest.raises(SystemExit):
            parse_date_values("")

    def test_parse_date_values_deduplicates(self):

        from horavox.at import parse_date_values

        result = parse_date_values("2026-05-10,2026-05-10")
        assert result == [datetime.date(2026, 5, 10)]

    def test_parse_date_values_invalid_string(self):
        from horavox.at import parse_date_values

        with pytest.raises(SystemExit):
            parse_date_values("not-a-date")

    def test_parse_date_values_sorted(self):

        from horavox.at import parse_date_values

        result = parse_date_values("2026-12-25,2026-05-10")
        assert result == [datetime.date(2026, 5, 10), datetime.date(2026, 12, 25)]

    def test_date_with_exit_at_scheduled_time(self):

        from horavox import at

        target = datetime.date.today()
        date_str = target.strftime("%Y-%m-%d")
        with mock.patch.object(
            sys,
            "argv",
            [
                "vox at",
                "12:00",
                "--date",
                date_str,
                "--debug",
                "--exit",
                "--time",
                "12:00",
                "--lang",
                "en",
            ],
        ):
            with mock.patch.object(at, "speak") as mock_speak:
                at.main()
                mock_speak.assert_called_once()

    def test_date_with_exit_wrong_date(self, capsys):
        from horavox import at

        with mock.patch.object(
            sys,
            "argv",
            [
                "vox at",
                "12:00",
                "--date",
                "2020-01-01",
                "--debug",
                "--exit",
                "--time",
                "12:00",
            ],
        ):
            with mock.patch.object(at, "speak") as mock_speak:
                at.main()
                mock_speak.assert_not_called()
        out = capsys.readouterr().out
        assert "not at a scheduled time" in out

    def test_date_background_mode(self):
        from horavox import at

        with mock.patch.object(
            sys,
            "argv",
            ["vox at", "12:00", "--date", "2026-12-25", "--background", "--nosound"],
        ):
            with mock.patch.object(at, "Daemonize") as mock_daemon:
                mock_instance = mock.MagicMock()
                mock_daemon.return_value = mock_instance
                at.main()
                mock_daemon.assert_called_once()
                mock_instance.start.assert_called_once()

    def test_run_at_once_multiple_dates(self, tmp_path, capsys):

        from horavox import at as at_mod
        from horavox.at import run_at_once

        core.configure(debug=True)
        core.SLEEP_FILE = str(tmp_path / "sleep.json")
        lang_data, lang = core.load_language_data("en", "classic")
        args = mock.MagicMock()
        args.time = None
        args.voice = None
        args.message = None
        schedule = [(12, 0)]
        today = datetime.date.today()
        target_dates = [today, today + datetime.timedelta(days=1)]
        now = datetime.datetime.combine(today, datetime.time(12, 0))
        time_offset = now - datetime.datetime.now()
        call_count = [0]

        def fake_sleep(t):
            call_count[0] += 1
            if call_count[0] > 3:
                raise KeyboardInterrupt

        with mock.patch.object(at_mod, "prepare_speech") as mock_prep:
            with mock.patch.object(at_mod, "play_speech"):
                with mock.patch.object(at_mod, "play_beep"):
                    with mock.patch.object(at_mod.time, "sleep", side_effect=fake_sleep):
                        try:
                            run_at_once(args, lang, lang_data, time_offset, schedule, target_dates)
                        except KeyboardInterrupt:
                            pass
        assert mock_prep.call_count >= 1

    def test_message_with_date_exit(self):

        from horavox import at

        target = datetime.date.today()
        date_str = target.strftime("%Y-%m-%d")
        with mock.patch.object(
            sys,
            "argv",
            [
                "vox at",
                "12:00",
                "--date",
                date_str,
                "--debug",
                "--exit",
                "--time",
                "12:00",
                "-m",
                "Meeting time",
            ],
        ):
            with mock.patch.object(at, "speak") as mock_speak:
                at.main()
                mock_speak.assert_called_once()
                text = mock_speak.call_args[0][1]
                assert text == "Meeting time"

    def test_next_weekday_never_today(self):

        from horavox.at import _next_weekday

        today = datetime.date.today()
        result = _next_weekday(today.weekday())
        assert result > today
        assert result == today + datetime.timedelta(days=7)

    def test_next_weekday_tomorrow(self):

        from horavox.at import _next_weekday

        today = datetime.date.today()
        tomorrow_weekday = (today.weekday() + 1) % 7
        result = _next_weekday(tomorrow_weekday)
        assert result == today + datetime.timedelta(days=1)

    def test_date_and_repeat_error(self, capsys):
        from horavox import at

        with mock.patch.object(
            sys,
            "argv",
            ["vox at", "12:00", "--date", "2026-05-10", "--repeat", "everyday", "--debug"],
        ):
            with pytest.raises(SystemExit) as exc:
                at.main()
            assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "cannot be used together" in out

    def test_oneshot_past_time_exits(self, capsys):
        from horavox import at

        with mock.patch.object(sys, "argv", ["vox at", "0:01", "--date", "2020-01-01", "--debug"]):
            at.main()
        out = capsys.readouterr().out
        assert "passed" in out

    def test_next_repeat_target(self):

        from horavox.at import _next_repeat_target

        monday_noon = datetime.datetime(2026, 5, 4, 12, 0, 0)
        schedule = [(14, 0)]
        repeat_days = {0}  # Monday only
        target = _next_repeat_target(monday_noon, schedule, repeat_days)
        assert target == datetime.datetime(2026, 5, 4, 14, 0)

    def test_next_repeat_target_skips_day(self):

        from horavox.at import _next_repeat_target

        tuesday_noon = datetime.datetime(2026, 5, 5, 12, 0, 0)
        schedule = [(10, 0)]
        repeat_days = {0}  # Monday only
        target = _next_repeat_target(tuesday_noon, schedule, repeat_days)
        assert target.weekday() == 0
        assert target.date() == datetime.date(2026, 5, 11)

    def test_repeat_wrong_day_no_speak(self, capsys):
        """--exit on a day not in repeat_days should not speak."""

        from horavox import at

        now = datetime.datetime(2026, 5, 5, 12, 0, 0)  # Tuesday
        h, m = now.hour, now.minute

        with mock.patch.object(
            sys,
            "argv",
            [
                "vox at",
                f"{h}:{m:02d}",
                "--repeat",
                "monday",
                "--debug",
                "--exit",
                "--time",
                f"{h}:{m:02d}",
            ],
        ):
            with mock.patch("horavox.at.datetime") as mock_dt:
                mock_dt.datetime.now.return_value = now
                mock_dt.datetime.combine = datetime.datetime.combine
                mock_dt.datetime.strptime = datetime.datetime.strptime
                mock_dt.timedelta = datetime.timedelta
                mock_dt.time = datetime.time
                mock_dt.date = datetime.date
                with mock.patch.object(at, "speak") as mock_speak:
                    at.main()
                    mock_speak.assert_not_called()

    def test_dispatches_from_main(self):
        from horavox.main import main

        with mock.patch.object(sys, "argv", ["vox", "at"]):
            with mock.patch("horavox.at.main") as m:
                main()
                m.assert_called_once()

    def test_service_foreground_creates_session(self):
        from horavox import at

        with mock.patch.object(
            sys,
            "argv",
            ["vox at", "12:00", "--repeat", "everyday", "--debug"],
        ):
            with mock.patch.dict(os.environ, {"HORAVOX_SERVICE": "1"}):
                with mock.patch("horavox.at.ensure_user_dirs"):
                    with mock.patch("horavox.at.create_session") as mock_create:
                        with mock.patch("horavox.at.remove_session") as mock_remove:
                            with mock.patch("horavox.at.run_at_repeat"):
                                at.main()
                                mock_create.assert_called_once()
                                assert mock_create.call_args[1]["session_type"] == "at"
                                mock_remove.assert_called_once()

    def test_service_foreground_oneshot_creates_session(self):
        from horavox import at

        with mock.patch.object(
            sys,
            "argv",
            ["vox at", "12:00", "--debug"],
        ):
            with mock.patch.dict(os.environ, {"HORAVOX_SERVICE": "1"}):
                with mock.patch("horavox.at.ensure_user_dirs"):
                    with mock.patch("horavox.at.create_session") as mock_create:
                        with mock.patch("horavox.at.remove_session") as mock_remove:
                            with mock.patch("horavox.at.run_at_once"):
                                at.main()
                                mock_create.assert_called_once()
                                assert mock_create.call_args[1]["session_type"] == "at"
                                mock_remove.assert_called_once()


# ==================== voice.py ====================


class TestVoiceCommand:
    def test_list_flag(self, capsys):
        from horavox import voice

        with mock.patch.object(sys, "argv", ["vox voice", "--list", "--lang", "pl"]):
            voice.main()
        out = capsys.readouterr().out
        assert "pl_PL" in out

    def test_list_unknown_lang(self, capsys):
        from horavox import voice

        with mock.patch.object(sys, "argv", ["vox voice", "--list", "--lang", "zz"]):
            voice.main()
        out = capsys.readouterr().out
        assert "No voices found" in out

    def test_list_has_installed_marker(self, capsys, monkeypatch):
        from horavox import voice

        fake_voices = [
            {
                "key": "pl_PL-darkman-medium",
                "name": "",
                "language": "pl_PL",
                "quality": "medium",
                "region": "",
                "speakers": 1,
                "size_mb": 60,
                "installed": True,
            },
        ]
        mock_vm = mock.MagicMock()
        mock_vm.list_voices.return_value = fake_voices
        mock_vm.get_language_name.return_value = "Polish"
        monkeypatch.setattr(core, "_vm", mock_vm)
        with mock.patch.object(sys, "argv", ["vox voice", "--list", "--lang", "pl"]):
            voice.main()
        out = capsys.readouterr().out
        assert "[*]" in out

    def test_interactive_no_voices(self, capsys):
        from horavox import voice

        with mock.patch.object(sys, "argv", ["vox voice", "--lang", "zz"]):
            voice.main()
        out = capsys.readouterr().out
        assert "No voices found" in out

    def test_cmd_list(self, capsys):
        from horavox.voice import cmd_list

        cmd_list("pl")
        out = capsys.readouterr().out
        assert "pl_PL" in out
        assert "Quality" in out

    def test_cmd_list_no_voices(self, capsys):
        from horavox.voice import cmd_list

        cmd_list("zz")
        out = capsys.readouterr().out
        assert "No voices found" in out

    def test_get_default_voice_key_config_voice(self):
        from horavox.voice import get_default_voice_key

        voices = [
            {"key": "pl_PL-darkman-medium", "installed": True},
            {"key": "pl_PL-mc_speech-medium", "installed": True},
        ]
        assert get_default_voice_key(voices, "pl_PL-mc_speech-medium") == "pl_PL-mc_speech-medium"

    def test_get_default_voice_key_config_not_in_list(self):
        from horavox.voice import get_default_voice_key

        voices = [
            {"key": "pl_PL-darkman-medium", "installed": True},
        ]
        assert get_default_voice_key(voices, "nonexistent-voice") == "pl_PL-darkman-medium"

    def test_get_default_voice_key_prefers_medium(self):
        from horavox.voice import get_default_voice_key

        voices = [
            {"key": "en_US-lessac-high", "installed": True},
            {"key": "en_US-lessac-medium", "installed": True},
            {"key": "en_US-lessac-low", "installed": True},
        ]
        assert get_default_voice_key(voices) == "en_US-lessac-medium"

    def test_get_default_voice_key_falls_back_to_first_installed(self):
        from horavox.voice import get_default_voice_key

        voices = [
            {"key": "en_US-lessac-high", "installed": True},
            {"key": "en_US-lessac-low", "installed": True},
        ]
        assert get_default_voice_key(voices) == "en_US-lessac-high"

    def test_get_default_voice_key_none_installed(self):
        from horavox.voice import get_default_voice_key

        voices = [
            {"key": "en_US-lessac-medium", "installed": False},
        ]
        assert get_default_voice_key(voices) is None

    def test_cmd_list_shows_default_marker(self, capsys, monkeypatch):
        from horavox.voice import cmd_list

        fake_voices = [
            {
                "key": "pl_PL-darkman-medium",
                "name": "",
                "language": "pl_PL",
                "quality": "medium",
                "region": "",
                "speakers": 1,
                "size_mb": 60,
                "installed": True,
            },
        ]
        mock_vm = mock.MagicMock()
        mock_vm.list_voices.return_value = fake_voices
        mock_vm.get_language_name.return_value = "Polish"
        monkeypatch.setattr(core, "_vm", mock_vm)
        cmd_list("pl")
        out = capsys.readouterr().out
        assert "[D]" in out

    def test_cmd_list_config_voice_default(self, capsys, monkeypatch):
        from horavox.voice import cmd_list

        fake_voices = [
            {
                "key": "pl_PL-darkman-medium",
                "name": "",
                "language": "pl_PL",
                "quality": "medium",
                "region": "",
                "speakers": 1,
                "size_mb": 60,
                "installed": True,
            },
        ]
        mock_vm = mock.MagicMock()
        mock_vm.list_voices.return_value = fake_voices
        mock_vm.get_language_name.return_value = "Polish"
        monkeypatch.setattr(core, "_vm", mock_vm)
        cmd_list("pl", config_voice="pl_PL-darkman-medium")
        out = capsys.readouterr().out
        assert "[D]" in out

    def test_parse_args_list(self):
        from horavox.voice import parse_args

        with mock.patch.object(sys, "argv", ["vox voice", "--list", "--lang", "en"]):
            args = parse_args()
        assert args.list_voices is True
        assert args.lang == "en"

    def test_parse_args_no_args_default(self):
        from horavox.voice import parse_args

        with mock.patch.object(sys, "argv", ["vox voice", "--lang", "en"]):
            args = parse_args()
        assert args.list_voices is False

    def test_keyboard_interrupt(self):
        from horavox import voice

        with mock.patch.object(sys, "argv", ["vox voice", "--lang", "zz"]):
            voice.main()

    def test_exception_logs(self):
        from horavox import voice

        with mock.patch.object(sys, "argv", ["vox voice", "--list", "--lang", "en"]):
            with mock.patch.object(voice, "cmd_list", side_effect=RuntimeError("boom")):
                with mock.patch.object(voice, "log_error"):
                    with pytest.raises(RuntimeError):
                        voice.main()

    def test_cmd_list_output(self, capsys):
        from horavox.voice import cmd_list

        cmd_list("en")
        out = capsys.readouterr().out
        assert "en_US" in out or "en_GB" in out
        assert "Quality" in out

    def test_cmd_interactive_delegates_to_browse(self, monkeypatch):
        from horavox import voice

        mock_vm = mock.MagicMock()
        monkeypatch.setattr(core, "_vm", mock_vm)
        voice.cmd_interactive("en")
        mock_vm.browse.assert_called_once()
        config = mock_vm.browse.call_args[1]["config"]
        assert config.lang == "en"

    def test_cmd_interactive_passes_config_voice(self, monkeypatch):
        from horavox import voice

        mock_vm = mock.MagicMock()
        monkeypatch.setattr(core, "_vm", mock_vm)
        voice.cmd_interactive("pl", config_voice="pl_PL-darkman-medium")
        config = mock_vm.browse.call_args[1]["config"]
        assert config.default_voice == "pl_PL-darkman-medium"

    def test_cmd_interactive_passes_test_fn(self, monkeypatch):
        from horavox import voice

        mock_vm = mock.MagicMock()
        monkeypatch.setattr(core, "_vm", mock_vm)
        voice.cmd_interactive("en", mode="modern")
        config = mock_vm.browse.call_args[1]["config"]
        assert config.test_fn is not None

    def test_speak_with_voice(self, monkeypatch):
        from horavox.voice import _speak_with_voice

        mock_piper = mock.MagicMock()
        mock_vm = mock.MagicMock()
        mock_vm.get_path.return_value = "/tmp/test.onnx"
        monkeypatch.setattr(core, "_vm", mock_vm)
        with mock.patch.dict("sys.modules", {"piper": mock_piper}):
            with mock.patch("horavox.voice.speak") as mock_speak:
                with mock.patch("horavox.voice.load_language_data") as mock_lang:
                    mock_lang.return_value = ({"patterns": {}}, "en")
                    with mock.patch("horavox.voice.get_spoken_time", return_value="three o'clock"):
                        _speak_with_voice("en_US-lessac-medium", "en")
            mock_piper.PiperVoice.load.assert_called_once()
            mock_speak.assert_called_once()


# ==================== completion.py ====================


class TestCompletionCommand:
    def test_bash_output(self, capsys):
        from horavox import completion

        with mock.patch.object(sys, "argv", ["vox completion", "--bash"]):
            completion.main()
        out = capsys.readouterr().out
        assert "vox" in out
        assert len(out) > 50

    def test_zsh_output(self, capsys):
        from horavox import completion

        with mock.patch.object(sys, "argv", ["vox completion", "--zsh"]):
            completion.main()
        out = capsys.readouterr().out
        assert "vox" in out

    def test_fish_output(self, capsys):
        from horavox import completion

        with mock.patch.object(sys, "argv", ["vox completion", "--fish"]):
            completion.main()
        out = capsys.readouterr().out
        assert "vox" in out
        assert "fish" in out.lower() or "__fish" in out

    def test_no_shell_flag_errors(self):
        from horavox import completion

        with mock.patch.object(sys, "argv", ["vox completion"]):
            with pytest.raises(SystemExit):
                completion.main()

    def test_dispatches_from_main(self):
        from horavox.main import main

        with mock.patch.object(sys, "argv", ["vox", "completion"]):
            with mock.patch("horavox.completion.main") as m:
                main()
                m.assert_called_once()

    def test_help_shows_completion(self, capsys):
        from horavox.main import main

        with mock.patch.object(sys, "argv", ["vox"]):
            main()
        out = capsys.readouterr().out
        assert "completion" in out


# ==================== build_parser ====================


class TestBuildParser:
    def test_build_parser_has_subcommands(self):
        from horavox.main import build_parser

        parser = build_parser()
        args = parser.parse_args(["clock", "--debug"])
        assert args.command == "clock"
        assert args.debug is True

    def test_build_parser_version(self):
        from horavox.main import build_parser

        parser = build_parser()
        with pytest.raises(SystemExit) as exc:
            parser.parse_args(["--version"])
        assert exc.value.code == 0

    def test_build_parser_service_subcommands(self):
        from horavox.main import build_parser

        parser = build_parser()
        args = parser.parse_args(["service", "list"])
        assert args.command == "service"
        assert args.subcommand == "list"

    def test_build_parser_completion(self):
        from horavox.main import build_parser

        parser = build_parser()
        args = parser.parse_args(["completion", "--bash"])
        assert args.command == "completion"
        assert args.bash is True

    def test_argcomplete_env_triggers_build(self):
        from horavox.main import main

        with mock.patch.dict(os.environ, {"_ARGCOMPLETE": "1"}):
            with mock.patch("horavox.main.build_parser") as mock_build:
                mock_parser = mock.MagicMock()
                mock_build.return_value = mock_parser
                with mock.patch("argcomplete.autocomplete"):
                    main()
                mock_build.assert_called_once()

    def test_build_parser_includes_new_command_alias(self, monkeypatch, tmp_path):
        import json

        import horavox.config as config

        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({"settings": {}, "alias": {"nap": "timer 30m --message x"}}))
        monkeypatch.setattr(config, "CONFIG_PATH", str(cfg))

        from horavox.main import build_parser

        parser = build_parser()
        # the alias is a completable subcommand...
        assert "nap" in parser._subparsers._group_actions[0].choices
        # ...and it inherits the target (timer) options
        args = parser.parse_args(["nap", "5m", "--volume", "50"])
        assert args.command == "nap"
        assert args.volume == 50

    def test_build_parser_skips_builtin_named_alias(self, monkeypatch, tmp_path):
        import json

        import horavox.config as config

        # an alias named like a builtin injects args; it must not add a duplicate subparser
        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({"settings": {}, "alias": {"clock": "--freq 30"}}))
        monkeypatch.setattr(config, "CONFIG_PATH", str(cfg))

        from horavox.main import build_parser

        parser = build_parser()  # must not raise (would if it re-added 'clock')
        assert "clock" in parser._subparsers._group_actions[0].choices

    def test_build_parser_survives_bad_alias(self, monkeypatch, tmp_path):
        import json

        import horavox.config as config

        cfg = tmp_path / "config.json"
        cfg.write_text(
            json.dumps(
                {
                    "settings": {},
                    "alias": {"bad": "", "opt": "--start 9 --freq 30", "nap": "timer 5m"},
                }
            )
        )
        monkeypatch.setattr(config, "CONFIG_PATH", str(cfg))

        from horavox.main import build_parser

        parser = build_parser()
        choices = parser._subparsers._group_actions[0].choices
        assert "nap" in choices
        assert "bad" not in choices  # empty alias value is skipped
        assert "opt" not in choices  # option-first alias can't dispatch, so skipped

    def test_build_parser_tolerates_config_error(self):
        from horavox.main import build_parser

        with mock.patch("horavox.config.get_aliases", side_effect=RuntimeError("boom")):
            parser = build_parser()  # must still build with just the builtins
        assert "clock" in parser._subparsers._group_actions[0].choices

    def test_build_parser_skips_unparseable_alias(self, monkeypatch, tmp_path):
        import json

        import horavox.config as config

        cfg = tmp_path / "config.json"
        cfg.write_text(
            json.dumps({"settings": {}, "alias": {"weird": "timer 'unclosed", "nap": "timer 5m"}})
        )
        monkeypatch.setattr(config, "CONFIG_PATH", str(cfg))

        from horavox.main import build_parser

        parser = build_parser()
        choices = parser._subparsers._group_actions[0].choices
        assert "nap" in choices
        assert "weird" not in choices  # unbalanced quotes -> shlex error -> skipped

    def test_build_parser_includes_shell_alias(self, monkeypatch, tmp_path):
        import json

        import horavox.config as config

        cfg = tmp_path / "config.json"
        cfg.write_text(json.dumps({"settings": {}, "alias": {"greet": "!echo hi"}}))
        monkeypatch.setattr(config, "CONFIG_PATH", str(cfg))

        from horavox.main import build_parser

        parser = build_parser()
        assert "greet" in parser._subparsers._group_actions[0].choices


# ==================== update.py ====================


class TestUpdateCheck:
    def setup_method(self):
        import tempfile

        self.tmpdir = tempfile.mkdtemp(prefix="horavox-test-update-")
        self.cache_file = os.path.join(self.tmpdir, "update.json")
        self._patch_cache = mock.patch("horavox.update.CACHE_FILE", self.cache_file)
        self._patch_dir = mock.patch("horavox.update.CACHE_DIR", self.tmpdir)
        self._patch_cache.start()
        self._patch_dir.start()

    def teardown_method(self):
        self._patch_cache.stop()
        self._patch_dir.stop()

    def _mock_pypi(self, version):
        import json

        response_data = json.dumps({"info": {"version": version}}).encode()
        mock_resp = mock.MagicMock()
        mock_resp.read.return_value = response_data
        mock_resp.__enter__ = mock.Mock(return_value=mock_resp)
        mock_resp.__exit__ = mock.Mock(return_value=False)
        return mock.patch("urllib.request.urlopen", return_value=mock_resp)

    def test_shows_update_when_newer(self, capsys):
        from horavox.update import check_for_update

        with self._mock_pypi("9.9.9"):
            check_for_update()
        err = capsys.readouterr().err
        assert "Update available" in err
        assert "9.9.9" in err
        assert "pip install --upgrade horavox" in err

    def test_respects_no_color(self, capsys):
        from horavox.update import check_for_update

        with self._mock_pypi("9.9.9"):
            with mock.patch.dict(os.environ, {"NO_COLOR": "1"}):
                check_for_update()
        err = capsys.readouterr().err
        assert "\033[" not in err
        assert "Update available" in err

    def test_silent_when_current(self, capsys):
        from horavox.update import check_for_update

        with self._mock_pypi("0.2.0"):
            check_for_update()
        err = capsys.readouterr().err
        assert err == ""

    def test_silent_when_older(self, capsys):
        from horavox.update import check_for_update

        with self._mock_pypi("0.1.0"):
            check_for_update()
        err = capsys.readouterr().err
        assert err == ""

    def test_silent_on_network_error(self, capsys):
        from horavox.update import check_for_update

        with mock.patch("urllib.request.urlopen", side_effect=OSError("no network")):
            check_for_update()
        err = capsys.readouterr().err
        assert err == ""

    def test_uses_cache(self, capsys):
        import json

        from horavox.update import check_for_update

        os.makedirs(self.tmpdir, exist_ok=True)
        with open(self.cache_file, "w") as f:
            json.dump({"latest": "9.9.9"}, f)

        with mock.patch("urllib.request.urlopen") as mock_url:
            check_for_update()
            mock_url.assert_not_called()
        err = capsys.readouterr().err
        assert "9.9.9" in err

    def test_cache_expired_fetches(self, capsys):
        import json

        from horavox.update import check_for_update

        os.makedirs(self.tmpdir, exist_ok=True)
        with open(self.cache_file, "w") as f:
            json.dump({"latest": "0.2.0"}, f)
        # Set mtime to 2 days ago
        old_time = os.path.getmtime(self.cache_file) - 200000
        os.utime(self.cache_file, (old_time, old_time))

        with self._mock_pypi("9.9.9"):
            check_for_update()
        err = capsys.readouterr().err
        assert "9.9.9" in err

    def test_skipped_in_service_mode(self, capsys):
        from horavox.main import main

        with mock.patch.dict(os.environ, {"HORAVOX_SERVICE": "1"}):
            with mock.patch.object(sys, "argv", ["vox", "now", "--debug", "--time", "12:00"]):
                with mock.patch("horavox.now.main"):
                    with mock.patch("horavox.update.check_for_update") as mock_check:
                        main()
                    mock_check.assert_not_called()

    def test_supports_color_no_color_env(self):
        from horavox.update import _supports_color

        with mock.patch.dict(os.environ, {"NO_COLOR": "1"}):
            assert _supports_color() is False

    def test_supports_color_force_color_env(self):
        from horavox.update import _supports_color

        with mock.patch.dict(os.environ, {"FORCE_COLOR": "1"}, clear=False):
            with mock.patch.dict(os.environ, {}, clear=False):
                env = os.environ.copy()
                env.pop("NO_COLOR", None)
                env["FORCE_COLOR"] = "1"
                with mock.patch.dict(os.environ, env, clear=True):
                    assert _supports_color() is True

    def test_supports_color_tty(self):
        from horavox.update import _supports_color

        mock_stderr = mock.MagicMock()
        mock_stderr.isatty.return_value = True
        env = os.environ.copy()
        env.pop("NO_COLOR", None)
        env.pop("FORCE_COLOR", None)
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch("horavox.update.sys.stderr", mock_stderr):
                assert _supports_color() is True

    def test_color_output_when_tty(self, capsys):
        from horavox.update import check_for_update

        mock_stderr = mock.MagicMock()
        mock_stderr.isatty.return_value = True
        mock_stderr.write = sys.stderr.write
        env = os.environ.copy()
        env.pop("NO_COLOR", None)
        env.pop("FORCE_COLOR", None)
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch("horavox.update.sys.stderr", mock_stderr):
                with self._mock_pypi("9.9.9"):
                    check_for_update()
        err = capsys.readouterr().err
        assert "\033[33m" in err or "\033[1m" in err

    def test_no_color_output(self, capsys):
        from horavox.update import check_for_update

        with mock.patch.dict(os.environ, {"NO_COLOR": "1"}):
            with self._mock_pypi("9.9.9"):
                check_for_update()
        err = capsys.readouterr().err
        assert "\033[" not in err
        assert "Update available" in err

    def test_read_cache_os_error(self):
        from horavox.update import _read_cache

        with mock.patch("builtins.open", side_effect=OSError("broken")):
            with mock.patch("os.path.exists", return_value=True):
                with mock.patch("os.path.getmtime", return_value=0):
                    with mock.patch("time.time", return_value=100):
                        assert _read_cache() is None

    def test_write_cache_os_error(self):
        from horavox.update import _write_cache

        with mock.patch("builtins.open", side_effect=OSError("no space")):
            _write_cache("1.0.0")

    def test_check_for_update_outer_exception(self, capsys):
        from horavox.update import check_for_update

        with mock.patch("horavox.update._get_latest_version", side_effect=RuntimeError("boom")):
            check_for_update()
        err = capsys.readouterr().err
        assert err == ""


# ==================== list.py error handling ====================


class TestListErrorHandling:
    def test_keyboard_interrupt(self):
        from horavox import list as list_cmd

        with mock.patch.object(sys, "argv", ["vox list"]):
            with mock.patch.object(list_cmd, "get_running_sessions", side_effect=KeyboardInterrupt):
                list_cmd.main()

    def test_exception_logs_and_raises(self):
        from horavox import list as list_cmd

        with mock.patch.object(sys, "argv", ["vox list"]):
            with mock.patch.object(
                list_cmd, "get_running_sessions", side_effect=RuntimeError("boom")
            ):
                with mock.patch.object(list_cmd, "log_error"):
                    with pytest.raises(RuntimeError, match="boom"):
                        list_cmd.main()


# ==================== completion.py error handling ====================


class TestCompletionErrorHandling:
    def test_keyboard_interrupt(self):
        from horavox import completion

        with mock.patch.object(sys, "argv", ["vox completion", "--bash"]):
            with mock.patch.dict("sys.modules", {"argcomplete": None}):
                with mock.patch("horavox.completion._main", side_effect=KeyboardInterrupt):
                    completion.main()

    def test_argcomplete_missing(self, capsys):
        from horavox import completion

        real_import = (
            __builtins__["__import__"]
            if isinstance(__builtins__, dict)
            else __builtins__.__import__
        )

        def fake_import(name, *a, **kw):
            if name == "argcomplete":
                raise ImportError("no argcomplete")
            return real_import(name, *a, **kw)

        with mock.patch.object(sys, "argv", ["vox completion", "--bash"]):
            with mock.patch("builtins.__import__", side_effect=fake_import):
                with pytest.raises(SystemExit):
                    completion._main()


# ==================== platforms/linux.py ====================


class TestLinuxPlatform:
    def test_vox_path_found(self):
        from horavox.platforms.linux import _vox_path

        with mock.patch("shutil.which", return_value="/usr/local/bin/vox"):
            assert _vox_path() == "/usr/local/bin/vox"

    def test_vox_path_not_found(self):
        from horavox.platforms.linux import _vox_path

        with mock.patch("shutil.which", return_value=None):
            assert _vox_path() == "vox"

    def test_unit_content(self):
        from horavox.platforms.linux import _unit_content

        with mock.patch("horavox.platforms.linux._vox_path", return_value="/usr/bin/vox"):
            content = _unit_content()
        assert "ExecStart=/usr/bin/vox service run" in content
        assert "[Unit]" in content
        assert "WantedBy=default.target" in content

    def test_register(self, tmp_path):
        from horavox.platforms import linux

        unit_path = str(tmp_path / "horavox.service")
        with mock.patch.object(linux, "UNIT_DIR", str(tmp_path)):
            with mock.patch.object(linux, "UNIT_PATH", unit_path):
                with mock.patch.object(linux, "_unit_content", return_value="[Unit]\ntest"):
                    with mock.patch("subprocess.run") as mock_run:
                        linux.register()
        assert os.path.exists(unit_path)
        with open(unit_path) as f:
            assert f.read() == "[Unit]\ntest"
        assert mock_run.call_count == 2

    def test_start(self):
        from horavox.platforms import linux

        with mock.patch("subprocess.run") as mock_run:
            linux.start()
        mock_run.assert_called_once()
        assert "start" in mock_run.call_args[0][0]

    def test_stop(self):
        from horavox.platforms import linux

        with mock.patch("subprocess.run") as mock_run:
            linux.stop()
        mock_run.assert_called_once()
        assert "stop" in mock_run.call_args[0][0]

    def test_reload(self):
        from horavox.platforms import linux

        with mock.patch("subprocess.run") as mock_run:
            linux.reload()
        mock_run.assert_called_once()
        assert "SIGHUP" in mock_run.call_args[0][0]

    def test_unregister(self, tmp_path):
        from horavox.platforms import linux

        unit_path = str(tmp_path / "horavox.service")
        with open(unit_path, "w") as f:
            f.write("test")
        with mock.patch.object(linux, "UNIT_PATH", unit_path):
            with mock.patch("subprocess.run"):
                linux.unregister()
        assert not os.path.exists(unit_path)

    def test_is_running_active(self):
        from horavox.platforms import linux

        result = mock.MagicMock()
        result.stdout = "active\n"
        with mock.patch("subprocess.run", return_value=result):
            assert linux.is_running() is True

    def test_is_running_inactive(self):
        from horavox.platforms import linux

        result = mock.MagicMock()
        result.stdout = "inactive\n"
        with mock.patch("subprocess.run", return_value=result):
            assert linux.is_running() is False


# ==================== config.py additional coverage ====================


class TestConfigAdditionalCoverage:
    def setup_method(self):
        import tempfile

        self.tmpdir = tempfile.mkdtemp(prefix="horavox-test-config-")
        self.config_path = os.path.join(self.tmpdir, "config.json")
        self._patch = mock.patch("horavox.config.CONFIG_PATH", self.config_path)
        self._patch_dir = mock.patch("horavox.config.USER_DIR", self.tmpdir)
        self._patch.start()
        self._patch_dir.start()

    def teardown_method(self):
        self._patch.stop()
        self._patch_dir.stop()
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_del_nested_cleans_empty_parents(self):
        from horavox.config import _del_nested

        data = {"a": {"b": {"c": "value"}}}
        assert _del_nested(data, ["a", "b", "c"]) is True
        assert data == {}

    def test_print_mapping_empty(self, capsys):
        from horavox.config import _print_mapping

        _print_mapping([])
        out = capsys.readouterr().out
        assert "No mapping entries." in out

    def test_parse_mapping_args_empty_date(self):
        from horavox.config import _parse_mapping_args

        with pytest.raises(SystemExit):
            _parse_mapping_args(["9:00", "msg", "--date"])

    def test_mapping_unset_non_int_key_found(self, capsys):
        import json

        from horavox.config import _main

        data = {"settings": {"mapping": {"time": "false"}}, "alias": {}, "mapping": []}
        with open(self.config_path, "w") as f:
            json.dump(data, f)
        with mock.patch.object(sys, "argv", ["vox config", "--unset", "settings.mapping.time"]):
            _main()
        out = capsys.readouterr().out
        assert "Unset" in out

    def test_mapping_unset_non_int_key_not_found(self, capsys):
        import json

        from horavox.config import _main

        data = {"settings": {}, "alias": {}, "mapping": []}
        with open(self.config_path, "w") as f:
            json.dump(data, f)
        with mock.patch.object(sys, "argv", ["vox config", "--unset", "mapping.foo"]):
            _main()
        out = capsys.readouterr().out
        assert "is not set" in out

    def test_mapping_unset_index_out_of_range(self, capsys):
        import json

        from horavox.config import _main

        data = {"settings": {}, "alias": {}, "mapping": [{"time": "9:00"}]}
        with open(self.config_path, "w") as f:
            json.dump(data, f)
        with mock.patch.object(sys, "argv", ["vox config", "--unset", "mapping.5"]):
            with pytest.raises(SystemExit):
                _main()
        out = capsys.readouterr().out
        assert "out of range" in out

    def test_mapping_unset_empty_list(self, capsys):
        import json

        from horavox.config import _main

        data = {"settings": {}, "alias": {}, "mapping": []}
        with open(self.config_path, "w") as f:
            json.dump(data, f)
        with mock.patch.object(sys, "argv", ["vox config", "--unset", "mapping.0"]):
            with pytest.raises(SystemExit):
                _main()
        out = capsys.readouterr().out
        assert "empty" in out.lower()

    def test_config_get_mapping_list(self, capsys):
        import json

        from horavox.config import _main

        data = {
            "settings": {},
            "alias": {},
            "mapping": [{"time": "9:00", "message": "test"}],
        }
        with open(self.config_path, "w") as f:
            json.dump(data, f)
        with mock.patch.object(sys, "argv", ["vox config", "mapping"]):
            _main()
        out = capsys.readouterr().out
        assert "9:00" in out

    def test_get_nested_dict_value(self, capsys):
        import json

        from horavox.config import _main

        data = {
            "settings": {"mapping": {"time": "false"}},
            "alias": {},
            "mapping": [],
        }
        with open(self.config_path, "w") as f:
            json.dump(data, f)
        with mock.patch.object(sys, "argv", ["vox config", "settings.mapping"]):
            _main()
        out = capsys.readouterr().out
        assert "settings.mapping.time=false" in out

    def test_get_single_value(self, capsys):
        import json

        from horavox.config import _main

        data = {"settings": {"lang": "pl"}, "alias": {}, "mapping": []}
        with open(self.config_path, "w") as f:
            json.dump(data, f)
        with mock.patch.object(sys, "argv", ["vox config", "lang"]):
            _main()
        out = capsys.readouterr().out
        assert "lang=pl" in out

    def test_mapping_unset_existing_non_int_key(self, capsys):
        import json

        from horavox.config import _main

        data = {"settings": {}, "alias": {"clock": "--background"}, "mapping": []}
        with open(self.config_path, "w") as f:
            json.dump(data, f)
        with mock.patch.object(sys, "argv", ["vox config", "--unset", "alias.clock"]):
            _main()
        out = capsys.readouterr().out
        assert "Unset" in out

    def test_show_all_with_mapping(self, capsys):
        import json

        from horavox.config import _main

        data = {
            "settings": {"lang": "pl"},
            "alias": {},
            "mapping": [{"time": "9:00", "message": "hello"}],
        }
        with open(self.config_path, "w") as f:
            json.dump(data, f)
        with mock.patch.object(sys, "argv", ["vox config"]):
            _main()
        out = capsys.readouterr().out
        assert "settings.lang=pl" in out
        assert "9:00" in out

    def test_get_empty_dict(self, capsys):
        import json

        from horavox.config import _main

        data = {"settings": {"mapping": {}}, "alias": {}, "mapping": []}
        with open(self.config_path, "w") as f:
            json.dump(data, f)
        with mock.patch.object(sys, "argv", ["vox config", "settings.mapping"]):
            _main()
        out = capsys.readouterr().out
        assert "empty" in out


# ==================== at.py additional coverage ====================


class TestAtFormatDays:
    def test_everyday(self):
        from horavox.at import _format_days

        assert _format_days(set(range(7))) == "everyday"

    def test_weekdays(self):
        from horavox.at import _format_days

        assert _format_days({0, 1, 2, 3, 4}) == "weekdays"

    def test_weekends(self):
        from horavox.at import _format_days

        assert _format_days({5, 6}) == "weekends"

    def test_individual_days(self):
        from horavox.at import _format_days

        result = _format_days({0, 2})
        assert "Monday" in result
        assert "Wednesday" in result


class TestAtRunOnce:
    def test_run_at_once_all_passed(self, capsys):

        from horavox import at, core

        core.configure(nosound=True, verbose=True)
        args = argparse.Namespace(voice=None, message=None, time=None, exit=False, exec_cmd=None)
        lang_data = {
            "hours": {},
            "hours_alt": {},
            "minutes": {},
            "connectors": {},
            "patterns": {"time": "{hour} {minutes}"},
        }
        schedule = [(10, 0)]
        target_dates = [datetime.date.today() - datetime.timedelta(days=1)]

        at.run_at_once(args, "en", lang_data, datetime.timedelta(0), schedule, target_dates)
        out = capsys.readouterr().out
        assert "passed" in out
        core.configure(verbose=False)

    def test_run_at_once_simulated_time_log(self, capsys):

        from horavox import at, core

        core.configure(nosound=True, verbose=True)
        fake_now = datetime.datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
        offset = fake_now - datetime.datetime.now()
        args = argparse.Namespace(voice=None, message=None, time="14:00", exit=False, exec_cmd=None)
        lang_data = {
            "hours": {},
            "hours_alt": {},
            "minutes": {},
            "connectors": {},
            "patterns": {"time": "{hour} {minutes}"},
        }
        schedule = [(14, 0)]
        target_dates = [datetime.date.today()]

        # Run in a thread and cancel quickly
        import threading

        def run():
            try:
                at.run_at_once(args, "en", lang_data, offset, schedule, target_dates)
            except Exception:
                pass

        t = threading.Thread(target=run, daemon=True)
        t.start()
        t.join(timeout=0.5)
        out = capsys.readouterr().out
        assert "Simulated start time" in out
        core.configure(verbose=False)


class TestAtRunOnceLoop:
    def test_run_at_once_announces_and_exits(self, tmp_path):

        from horavox import at, core

        core.configure(nosound=True, verbose=True)
        core.SLEEP_FILE = str(tmp_path / "sleep.json")
        fake_now = datetime.datetime.now().replace(hour=14, minute=0, second=0, microsecond=0)
        offset = fake_now - datetime.datetime.now()
        args = argparse.Namespace(voice=None, message=None, time=None, exit=False, exec_cmd=None)
        lang_data, lang = core.load_language_data("en", "classic")
        schedule = [(14, 0)]
        target_dates = [datetime.date.today()]

        with mock.patch.object(at, "prepare_speech"):
            with mock.patch.object(at, "play_beep"):
                with mock.patch.object(at, "play_speech"):
                    with mock.patch("time.sleep"):
                        at.run_at_once(
                            args,
                            lang,
                            lang_data,
                            offset,
                            schedule,
                            target_dates,
                        )
        core.configure(verbose=False)

    def test_run_at_once_skips_past_target(self, capsys):

        from horavox import at, core

        core.configure(nosound=True, verbose=True)
        fake_now = datetime.datetime.now().replace(hour=15, minute=0, second=0, microsecond=0)
        offset = fake_now - datetime.datetime.now()
        args = argparse.Namespace(voice=None, message=None, time=None, exit=False, exec_cmd=None)
        lang_data, lang = core.load_language_data("en", "classic")
        schedule = [(14, 50)]
        target_dates = [datetime.date.today()]

        at.run_at_once(
            args,
            lang,
            lang_data,
            offset,
            schedule,
            target_dates,
        )
        out = capsys.readouterr().out
        assert "passed" in out.lower()
        core.configure(verbose=False)

    def test_run_at_once_sleep_active_skips(self, capsys):

        from horavox import at, core

        core.configure(nosound=True, verbose=True)
        fake_now = datetime.datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
        offset = fake_now - datetime.datetime.now()
        args = argparse.Namespace(voice=None, message=None, time=None, exit=False, exec_cmd=None)
        lang_data = {
            "hours": {},
            "hours_alt": {},
            "minutes": {},
            "connectors": {},
            "patterns": {"time": "{hour} {minutes}"},
        }
        schedule = [(12, 0)]
        target_dates = [datetime.date.today()]

        with mock.patch.object(at, "is_sleep_active", return_value=True):
            with mock.patch("time.sleep"):
                at.run_at_once(
                    args,
                    "en",
                    lang_data,
                    offset,
                    schedule,
                    target_dates,
                )
        out = capsys.readouterr().out
        assert "sleeping" in out
        core.configure(verbose=False)


class TestAtRepeatExit:
    def test_run_at_repeat_exit_not_matching(self, capsys):

        from horavox import at, core

        core.configure(nosound=True, verbose=True)
        args = argparse.Namespace(voice=None, message=None, time=None, exit=True, exec_cmd=None)
        lang_data = {
            "hours": {},
            "hours_alt": {},
            "minutes": {},
            "connectors": {},
            "patterns": {"time": "{hour} {minutes}"},
        }
        schedule = [(3, 0)]
        repeat_days = {0, 1, 2, 3, 4, 5, 6}

        at.run_at_repeat(args, "en", lang_data, datetime.timedelta(0), schedule, repeat_days)
        out = capsys.readouterr().out
        assert "not at a scheduled time" in out
        core.configure(verbose=False)

    def test_run_at_repeat_logs_with_simulated_time(self, capsys):

        from horavox import at, core

        core.configure(nosound=True, verbose=True)
        args = argparse.Namespace(voice=None, message=None, time="10:00", exit=False, exec_cmd=None)
        lang_data = {
            "hours": {},
            "hours_alt": {},
            "minutes": {},
            "connectors": {},
            "patterns": {"time": "{hour} {minutes}"},
        }
        schedule = [(23, 59)]
        repeat_days = {0, 1, 2, 3, 4, 5, 6}

        import threading

        def run():
            try:
                at.run_at_repeat(
                    args, "en", lang_data, datetime.timedelta(0), schedule, repeat_days
                )
            except Exception:
                pass

        t = threading.Thread(target=run, daemon=True)
        t.start()
        t.join(timeout=0.5)
        out = capsys.readouterr().out
        assert "Simulated start time" in out
        core.configure(verbose=False)


# ==================== clock.py additional coverage ====================


class TestClockLoopCoverage:
    def test_clock_exit_outside_range(self, capsys):

        from horavox import clock, core

        core.configure(nosound=True, verbose=True)
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        args = argparse.Namespace(
            voice=None,
            freq=60,
            time=None,
            exit=True,
            verbose=True,
            nosound=True,
            volume=0,
            debug=True,
            background=False,
            start="0:00",
            end="23:59",
            lang=None,
            mode="classic",
            exec_cmd=None,
        )
        freq = 60
        h, m = now.hour, now.minute
        if m % freq == 0:
            start_min = (h * 60 + m + 60) % 1440
            end_min = (h * 60 + m + 120) % 1440
        else:
            start_min = ((h * 60 + m) // 60 + 1) * 60 % 1440
            end_min = start_min + 60
        lang_data = {
            "hours": {},
            "hours_alt": {},
            "minutes": {},
            "connectors": {},
            "patterns": {"time": "{hour} {minutes}"},
        }
        with mock.patch("horavox.config.get_mapping", return_value=[]):
            with mock.patch("horavox.config.load_config", return_value={"settings": {}}):
                clock.run_clock(args, "en", lang_data, datetime.timedelta(0), start_min, end_min)
        out = capsys.readouterr().out
        assert "outside range" in out or "not at announcement slot" in out
        core.configure(verbose=False)

    def test_clock_loop_log_messages(self, capsys):

        from horavox import clock, core

        core.configure(nosound=True, verbose=True)
        args = argparse.Namespace(
            voice=None,
            freq=30,
            time="10:00",
            exit=False,
            verbose=True,
            nosound=True,
            volume=0,
            debug=True,
            background=False,
            exec_cmd=None,
        )
        lang_data = {
            "hours": {},
            "hours_alt": {},
            "minutes": {},
            "connectors": {},
            "patterns": {"time": "{hour} {minutes}"},
        }

        call_count = [0]

        def fake_sleep(secs):
            call_count[0] += 1
            if call_count[0] >= 2:
                raise KeyboardInterrupt

        with mock.patch("horavox.config.get_mapping", return_value=[]):
            with mock.patch("horavox.config.load_config", return_value={"settings": {}}):
                with mock.patch("time.sleep", side_effect=fake_sleep):
                    try:
                        clock.run_clock(
                            args, "en", lang_data, datetime.timedelta(0), 0, 23 * 60 + 59
                        )
                    except KeyboardInterrupt:
                        pass
        out = capsys.readouterr().out
        assert "HoraVox started" in out
        assert "every 30 min" in out
        assert "Simulated start time" in out
        assert "Time range" in out or "every 30 minutes" in out
        core.configure(verbose=False)

    def test_clock_loop_in_range_announce(self):

        from horavox import clock, core

        core.configure(nosound=True, verbose=True)
        now = datetime.datetime.now().replace(minute=0, second=0, microsecond=0)
        offset = now - datetime.datetime.now()

        args = argparse.Namespace(
            voice=None,
            freq=60,
            time=None,
            exit=False,
            verbose=True,
            nosound=True,
            volume=0,
            debug=True,
            background=False,
            exec_cmd=None,
        )
        lang_data = {
            "hours": {},
            "hours_alt": {},
            "minutes": {},
            "connectors": {},
            "patterns": {"time": "{hour} {minutes}"},
        }

        call_count = [0]

        def fake_sleep(secs):
            call_count[0] += 1
            if call_count[0] >= 3:
                raise KeyboardInterrupt

        with mock.patch("horavox.config.get_mapping", return_value=[]):
            with mock.patch("horavox.config.load_config", return_value={"settings": {}}):
                with mock.patch.object(clock, "get_spoken_time", return_value="twelve o'clock"):
                    with mock.patch.object(clock, "prepare_speech"):
                        with mock.patch.object(clock, "prepare_combined_speech"):
                            with mock.patch.object(clock, "play_beep"):
                                with mock.patch.object(clock, "play_speech"):
                                    with mock.patch("time.sleep", side_effect=fake_sleep):
                                        try:
                                            clock.run_clock(
                                                args, "en", lang_data, offset, 0, 23 * 60 + 59
                                            )
                                        except KeyboardInterrupt:
                                            pass
        core.configure(verbose=False)

    def test_clock_loop_outside_range_skips(self, capsys):

        from horavox import clock, core

        core.configure(nosound=True, verbose=True)
        now = datetime.datetime.now().replace(minute=0, second=0, microsecond=0)
        offset = now - datetime.datetime.now()

        args = argparse.Namespace(
            voice=None,
            freq=60,
            time=None,
            exit=False,
            verbose=True,
            nosound=True,
            volume=0,
            debug=True,
            background=False,
            exec_cmd=None,
        )
        lang_data = {
            "hours": {},
            "hours_alt": {},
            "minutes": {},
            "connectors": {},
            "patterns": {"time": "{hour} {minutes}"},
        }

        start_min = (now.hour * 60 + 120) % 1440
        end_min = (now.hour * 60 + 180) % 1440

        call_count = [0]

        def fake_sleep(secs):
            call_count[0] += 1
            if call_count[0] >= 3:
                raise KeyboardInterrupt

        with mock.patch("horavox.config.get_mapping", return_value=[]):
            with mock.patch("horavox.config.load_config", return_value={"settings": {}}):
                with mock.patch("time.sleep", side_effect=fake_sleep):
                    try:
                        clock.run_clock(args, "en", lang_data, offset, start_min, end_min)
                    except KeyboardInterrupt:
                        pass
        out = capsys.readouterr().out
        assert "outside range" in out
        core.configure(verbose=False)

    def test_clock_next_announcement_frac_gte_5(self):

        from horavox import clock, core

        core.configure(nosound=True, verbose=True)
        args = argparse.Namespace(
            voice=None,
            freq=60,
            time=None,
            exit=True,
            verbose=True,
            nosound=True,
            volume=0,
            debug=True,
            background=False,
            exec_cmd=None,
        )
        lang_data = {
            "hours": {},
            "hours_alt": {},
            "minutes": {},
            "connectors": {},
            "patterns": {"time": "{hour} {minutes}"},
        }
        now = datetime.datetime.now().replace(minute=0, second=6, microsecond=0)
        offset = now - datetime.datetime.now()

        with mock.patch("horavox.config.get_mapping", return_value=[]):
            with mock.patch("horavox.config.load_config", return_value={"settings": {}}):
                clock.run_clock(args, "en", lang_data, offset, 0, 23 * 60 + 59)
        core.configure(verbose=False)

    def test_clock_loop_sleep_active_skips(self, capsys):

        from horavox import clock, core

        core.configure(nosound=True, verbose=True)
        now = datetime.datetime.now().replace(minute=0, second=0, microsecond=0)
        offset = now - datetime.datetime.now()

        args = argparse.Namespace(
            voice=None,
            freq=60,
            time=None,
            exit=False,
            verbose=True,
            nosound=True,
            volume=0,
            debug=True,
            background=False,
            exec_cmd=None,
        )
        lang_data = {
            "hours": {},
            "hours_alt": {},
            "minutes": {},
            "connectors": {},
            "patterns": {"time": "{hour} {minutes}"},
        }

        call_count = [0]

        def fake_sleep(secs):
            call_count[0] += 1
            if call_count[0] >= 3:
                raise KeyboardInterrupt

        with mock.patch("horavox.config.get_mapping", return_value=[]):
            with mock.patch("horavox.config.load_config", return_value={"settings": {}}):
                with mock.patch.object(clock, "is_sleep_active", return_value=True):
                    with mock.patch("time.sleep", side_effect=fake_sleep):
                        try:
                            clock.run_clock(args, "en", lang_data, offset, 0, 23 * 60 + 59)
                        except KeyboardInterrupt:
                            pass
        out = capsys.readouterr().out
        assert "sleeping" in out
        core.configure(verbose=False)

    def test_clock_loop_early_wake_announces(self, tmp_path, capsys):
        from horavox import clock, core

        core.configure(nosound=True, verbose=True)
        now = datetime.datetime.now().replace(minute=0, second=0, microsecond=0)
        offset = now - datetime.datetime.now()

        args = argparse.Namespace(
            voice=None,
            freq=60,
            time=None,
            exit=False,
            verbose=True,
            nosound=True,
            volume=0,
            debug=True,
            background=False,
            exec_cmd=None,
        )
        lang_data = {
            "hours": {},
            "hours_alt": {},
            "minutes": {},
            "connectors": {},
            "patterns": {"time": "{hour} {minutes}"},
        }

        start_min = (now.hour + 2) * 60
        end_min = (now.hour + 10) * 60 % (24 * 60)

        call_count = [0]

        def fake_sleep(secs):
            call_count[0] += 1
            if call_count[0] >= 3:
                raise KeyboardInterrupt

        core.SLEEP_FILE = str(tmp_path / "sleep.json")
        core.WAKEUP_FILE = str(tmp_path / "wakeup.json")
        core.write_wakeup()

        with mock.patch("horavox.config.get_mapping", return_value=[]):
            with mock.patch("horavox.config.load_config", return_value={"settings": {}}):
                with mock.patch.object(clock, "get_spoken_time", return_value="test"):
                    with mock.patch.object(clock, "prepare_speech"):
                        with mock.patch.object(clock, "prepare_combined_speech"):
                            with mock.patch.object(clock, "play_beep"):
                                with mock.patch.object(clock, "play_speech"):
                                    with mock.patch("time.sleep", side_effect=fake_sleep):
                                        try:
                                            clock.run_clock(
                                                args, "en", lang_data, offset, start_min, end_min
                                            )
                                        except KeyboardInterrupt:
                                            pass
        out = capsys.readouterr().out
        assert "early wake" in out.lower()
        core.configure(verbose=False)


# ==================== sleep.py ====================


class TestSleepCommand:
    def test_noop_when_no_sessions(self, tmp_path, monkeypatch, capsys):
        from horavox.sleep import _main

        monkeypatch.setattr(core, "SLEEP_FILE", str(tmp_path / "sleep.json"))
        monkeypatch.setattr(core, "SESSIONS_DIR", str(tmp_path / "sessions"))
        monkeypatch.setattr(sys, "argv", ["vox sleep"])
        _main()
        assert not (tmp_path / "sleep.json").exists()
        assert "no running sessions" in capsys.readouterr().out.lower()

    def test_sleep_creates_file(self, tmp_path, monkeypatch, capsys):
        from horavox.sleep import _main

        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        session_file = sessions_dir / "test.json"
        session_file.write_text(
            json.dumps(
                {
                    "pid": os.getpid(),
                    "command": "vox clock --start 8 --end 22",
                    "type": "clock",
                    "start": "8:00",
                    "end": "22:00",
                }
            )
        )
        monkeypatch.setattr(core, "SLEEP_FILE", str(tmp_path / "sleep.json"))
        monkeypatch.setattr(core, "SESSIONS_DIR", str(sessions_dir))
        monkeypatch.setattr(sys, "argv", ["vox sleep"])
        _main()
        assert (tmp_path / "sleep.json").exists()
        assert "Sleep activated" in capsys.readouterr().out

    def test_sleep_error_no_range(self, tmp_path, monkeypatch):
        from horavox.sleep import _main

        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        session_file = sessions_dir / "test.json"
        session_file.write_text(
            json.dumps({"pid": os.getpid(), "command": "vox clock", "type": "clock"})
        )
        monkeypatch.setattr(core, "SLEEP_FILE", str(tmp_path / "sleep.json"))
        monkeypatch.setattr(core, "SESSIONS_DIR", str(sessions_dir))
        monkeypatch.setattr(sys, "argv", ["vox sleep"])
        with pytest.raises(SystemExit):
            _main()
        assert not (tmp_path / "sleep.json").exists()

    def test_sleep_no_range_allowed_with_until(self, tmp_path, monkeypatch, capsys):
        from horavox.sleep import _main

        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        session_file = sessions_dir / "test.json"
        session_file.write_text(
            json.dumps({"pid": os.getpid(), "command": "vox clock", "type": "clock"})
        )
        monkeypatch.setattr(core, "SLEEP_FILE", str(tmp_path / "sleep.json"))
        monkeypatch.setattr(core, "SESSIONS_DIR", str(sessions_dir))
        monkeypatch.setattr(sys, "argv", ["vox sleep", "--until", "08:00"])
        _main()
        assert (tmp_path / "sleep.json").exists()

    def test_sleep_with_for_duration(self, tmp_path, monkeypatch, capsys):
        from horavox.sleep import _main

        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        session_file = sessions_dir / "test.json"
        session_file.write_text(
            json.dumps(
                {
                    "pid": os.getpid(),
                    "command": "vox clock --start 8 --end 22",
                    "type": "clock",
                    "start": "8:00",
                    "end": "22:00",
                }
            )
        )
        monkeypatch.setattr(core, "SLEEP_FILE", str(tmp_path / "sleep.json"))
        monkeypatch.setattr(core, "SESSIONS_DIR", str(sessions_dir))
        monkeypatch.setattr(sys, "argv", ["vox sleep", "--for", "2h"])
        _main()
        data = json.loads((tmp_path / "sleep.json").read_text())
        assert data["until"] > time.time()
        assert "Sleep activated until" in capsys.readouterr().out

    def test_sleep_warns_about_at(self, tmp_path, monkeypatch, capsys):
        from horavox.sleep import _main

        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        session_file = sessions_dir / "clock.json"
        session_file.write_text(
            json.dumps(
                {
                    "pid": os.getpid(),
                    "command": "vox clock --start 8 --end 22",
                    "type": "clock",
                    "start": "8:00",
                    "end": "22:00",
                }
            )
        )
        at_file = sessions_dir / "at.json"
        at_file.write_text(
            json.dumps({"pid": os.getpid(), "command": "vox at 12:00", "type": "at"})
        )
        monkeypatch.setattr(core, "SLEEP_FILE", str(tmp_path / "sleep.json"))
        monkeypatch.setattr(core, "SESSIONS_DIR", str(sessions_dir))
        monkeypatch.setattr(sys, "argv", ["vox sleep"])
        _main()
        out = capsys.readouterr().out
        assert "Warning" in out
        assert "vox at" in out

    def test_until_and_for_conflict(self, tmp_path, monkeypatch):
        from horavox.sleep import _main

        monkeypatch.setattr(sys, "argv", ["vox sleep", "--until", "08:00", "--for", "2h"])
        with pytest.raises(SystemExit):
            _main()

    def test_fallback_type_detection_from_command(self, tmp_path, monkeypatch):
        from horavox.sleep import _main

        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        session_file = sessions_dir / "test.json"
        session_file.write_text(json.dumps({"pid": os.getpid(), "command": "vox clock"}))
        monkeypatch.setattr(core, "SLEEP_FILE", str(tmp_path / "sleep.json"))
        monkeypatch.setattr(core, "SESSIONS_DIR", str(sessions_dir))
        monkeypatch.setattr(sys, "argv", ["vox sleep"])
        with pytest.raises(SystemExit):
            _main()

    def test_fallback_type_detection_at(self, tmp_path, monkeypatch, capsys):
        from horavox.sleep import _main

        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        clock_file = sessions_dir / "clock.json"
        clock_file.write_text(
            json.dumps(
                {
                    "pid": os.getpid(),
                    "command": "vox clock --start 8 --end 22",
                    "type": "clock",
                    "start": "8:00",
                    "end": "22:00",
                }
            )
        )
        at_file = sessions_dir / "at.json"
        at_file.write_text(json.dumps({"pid": os.getpid(), "command": "vox at 12:00"}))
        monkeypatch.setattr(core, "SLEEP_FILE", str(tmp_path / "sleep.json"))
        monkeypatch.setattr(core, "SESSIONS_DIR", str(sessions_dir))
        monkeypatch.setattr(sys, "argv", ["vox sleep"])
        _main()
        out = capsys.readouterr().out
        assert "Warning" in out


class TestSessionTypeDetection:
    def test_session_type_from_field(self):
        from horavox.sleep import _session_type

        assert _session_type({"type": "clock"}) == "clock"

    def test_session_type_from_command_clock(self):
        from horavox.sleep import _session_type

        assert _session_type({"command": "vox clock --start 8"}) == "clock"

    def test_session_type_from_command_at(self):
        from horavox.sleep import _session_type

        assert _session_type({"command": "vox at 12:00"}) == "at"

    def test_session_type_unknown(self):
        from horavox.sleep import _session_type

        assert _session_type({"command": "something else"}) is None


class TestParseDuration:
    def test_hours(self):
        from horavox.sleep import parse_duration

        assert parse_duration("2h") == 7200

    def test_minutes(self):
        from horavox.sleep import parse_duration

        assert parse_duration("30m") == 1800

    def test_hours_and_minutes(self):
        from horavox.sleep import parse_duration

        assert parse_duration("1h30m") == 5400

    def test_invalid(self):
        from horavox.sleep import parse_duration

        with pytest.raises(SystemExit):
            parse_duration("abc")

    def test_zero(self):
        from horavox.sleep import parse_duration

        with pytest.raises(SystemExit):
            parse_duration("0h0m")


# ==================== sleep off / wakeup ====================


class TestSleepOff:
    def test_sleep_off_removes_sleep(self, tmp_path, monkeypatch, capsys):
        from horavox.sleep import _main

        sleep_file = tmp_path / "sleep.json"
        sleep_file.write_text('{"timestamp": 1}')
        monkeypatch.setattr(core, "SLEEP_FILE", str(sleep_file))
        monkeypatch.setattr(sys, "argv", ["vox sleep", "off"])
        with mock.patch("horavox.sleep._has_between_range_sessions", return_value=False):
            _main()
        assert not sleep_file.exists()
        out = capsys.readouterr().out
        assert "resumed" in out
        assert "within their ranges" in out

    def test_sleep_off_no_active_sleep(self, tmp_path, monkeypatch, capsys):
        from horavox.sleep import _main

        monkeypatch.setattr(core, "SLEEP_FILE", str(tmp_path / "sleep.json"))
        monkeypatch.setattr(sys, "argv", ["vox sleep", "off"])
        with mock.patch("horavox.sleep._has_between_range_sessions", return_value=False):
            _main()
        out = capsys.readouterr().out
        assert "No active sleep" in out
        assert "within their ranges" in out

    def test_sleep_off_between_ranges_writes_early_wake(self, tmp_path, monkeypatch, capsys):
        from horavox.sleep import _main

        sleep_file = tmp_path / "sleep.json"
        sleep_file.write_text('{"timestamp": 1}')
        monkeypatch.setattr(core, "SLEEP_FILE", str(sleep_file))
        monkeypatch.setattr(core, "WAKEUP_FILE", str(tmp_path / "wakeup.json"))
        monkeypatch.setattr(sys, "argv", ["vox sleep", "off"])
        with mock.patch("horavox.sleep._has_between_range_sessions", return_value=True):
            _main()
        assert (tmp_path / "wakeup.json").exists()
        out = capsys.readouterr().out
        assert "Early wake activated" in out

    def test_sleep_off_no_sleep_between_ranges(self, tmp_path, monkeypatch, capsys):
        from horavox.sleep import _main

        monkeypatch.setattr(core, "SLEEP_FILE", str(tmp_path / "sleep.json"))
        monkeypatch.setattr(core, "WAKEUP_FILE", str(tmp_path / "wakeup.json"))
        monkeypatch.setattr(sys, "argv", ["vox sleep", "off"])
        with mock.patch("horavox.sleep._has_between_range_sessions", return_value=True):
            _main()
        out = capsys.readouterr().out
        assert "No active sleep" in out
        assert "Early wake activated" in out
        assert (tmp_path / "wakeup.json").exists()

    def test_has_between_range_sessions_in_range(self, tmp_path, monkeypatch):
        from horavox.sleep import _has_between_range_sessions

        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        session_file = sessions_dir / "test.json"
        session_file.write_text(
            json.dumps(
                {
                    "pid": os.getpid(),
                    "type": "clock",
                    "start": "0:00",
                    "end": "23:59",
                }
            )
        )
        monkeypatch.setattr(core, "SESSIONS_DIR", str(sessions_dir))
        assert not _has_between_range_sessions()

    def test_has_between_range_sessions_outside_range(self, tmp_path, monkeypatch):
        import datetime

        from horavox.sleep import _has_between_range_sessions

        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        now = datetime.datetime.now()
        start_h = (now.hour + 2) % 24
        end_h = (now.hour + 4) % 24
        session_file = sessions_dir / "test.json"
        session_file.write_text(
            json.dumps(
                {
                    "pid": os.getpid(),
                    "type": "clock",
                    "start": f"{start_h}:00",
                    "end": f"{end_h}:00",
                }
            )
        )
        monkeypatch.setattr(core, "SESSIONS_DIR", str(sessions_dir))
        assert _has_between_range_sessions()

    def test_has_between_range_sessions_no_range(self, tmp_path, monkeypatch):
        from horavox.sleep import _has_between_range_sessions

        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        session_file = sessions_dir / "test.json"
        session_file.write_text(json.dumps({"pid": os.getpid(), "type": "clock"}))
        monkeypatch.setattr(core, "SESSIONS_DIR", str(sessions_dir))
        assert not _has_between_range_sessions()

    def test_has_between_range_sessions_skips_at(self, tmp_path, monkeypatch):
        from horavox.sleep import _has_between_range_sessions

        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        session_file = sessions_dir / "test.json"
        session_file.write_text(json.dumps({"pid": os.getpid(), "type": "at"}))
        monkeypatch.setattr(core, "SESSIONS_DIR", str(sessions_dir))
        assert not _has_between_range_sessions()


# ==================== wakeup.py ====================


class TestWakeupCommand:
    def test_wakeup_calls_sleep_off(self, tmp_path, monkeypatch, capsys):
        from horavox.wakeup import _main

        sleep_file = tmp_path / "sleep.json"
        sleep_file.write_text('{"timestamp": 1}')
        monkeypatch.setattr(core, "SLEEP_FILE", str(sleep_file))
        monkeypatch.setattr(sys, "argv", ["vox wakeup"])
        with mock.patch("horavox.sleep._has_between_range_sessions", return_value=False):
            _main()
        assert not sleep_file.exists()
        out = capsys.readouterr().out
        assert "resumed" in out


# ==================== list.py sleep marker ====================


class TestListSleepMarker:
    def test_list_shows_sleeping(self, tmp_path, monkeypatch, capsys):
        from horavox.list import _main

        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        session_file = sessions_dir / "test.json"
        session_file.write_text(json.dumps({"pid": os.getpid(), "command": "vox clock"}))
        sleep_file = tmp_path / "sleep.json"
        sleep_file.write_text('{"timestamp": 1}')
        monkeypatch.setattr(core, "SESSIONS_DIR", str(sessions_dir))
        monkeypatch.setattr(core, "SLEEP_FILE", str(sleep_file))
        monkeypatch.setattr(sys, "argv", ["vox list"])
        _main()
        out = capsys.readouterr().out
        assert "[sleeping]" in out

    def test_list_no_sleeping(self, tmp_path, monkeypatch, capsys):
        from horavox.list import _main

        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        session_file = sessions_dir / "test.json"
        session_file.write_text(json.dumps({"pid": os.getpid(), "command": "vox clock"}))
        monkeypatch.setattr(core, "SESSIONS_DIR", str(sessions_dir))
        monkeypatch.setattr(core, "SLEEP_FILE", str(tmp_path / "sleep.json"))
        monkeypatch.setattr(sys, "argv", ["vox list"])
        _main()
        out = capsys.readouterr().out
        assert "[sleeping]" not in out


# ==================== --exec flag ====================


class TestExecFlag:
    def test_clock_parser_accepts_exec(self):
        from horavox.clock import parse_args

        with mock.patch.object(
            sys, "argv", ["vox clock", "--exec", "notify-send '$TEXT'", "--exit"]
        ):
            args = parse_args()
        assert args.exec_cmd == "notify-send '$TEXT'"

    def test_at_parser_accepts_exec(self):
        from horavox.at import parse_args

        with mock.patch.object(sys, "argv", ["vox at", "12:00", "--exec", "notify-send '$TEXT'"]):
            args = parse_args()
        assert args.exec_cmd == "notify-send '$TEXT'"

    def test_exec_called_in_at_exit_mode(self, tmp_path, monkeypatch):
        from horavox.at import _main

        monkeypatch.setattr(core, "NOSOUND", True)
        monkeypatch.setattr(core, "VERBOSE", False)
        monkeypatch.setattr(core, "SESSIONS_DIR", str(tmp_path / "sessions"))
        monkeypatch.setattr(core, "SLEEP_FILE", str(tmp_path / "sleep.json"))
        monkeypatch.setattr(
            sys,
            "argv",
            ["vox at", "12:00", "--exit", "--debug", "--exec", "echo $TEXT", "--time", "12:00"],
        )
        with mock.patch("horavox.core.subprocess.Popen") as mock_popen:
            _main()
        mock_popen.assert_called_once()
        env = mock_popen.call_args.kwargs["env"]
        assert "TEXT" in env
        assert env["TEXT"] != ""
        assert env["TIME"] == "12:00"
        assert "DATE" in env
        assert env["MESSAGE"] == ""

    def test_exec_receives_message(self, tmp_path, monkeypatch):
        from horavox.at import _main

        monkeypatch.setattr(core, "NOSOUND", True)
        monkeypatch.setattr(core, "VERBOSE", False)
        monkeypatch.setattr(core, "SESSIONS_DIR", str(tmp_path / "sessions"))
        monkeypatch.setattr(core, "SLEEP_FILE", str(tmp_path / "sleep.json"))
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "vox at",
                "12:00",
                "--exit",
                "--debug",
                "--exec",
                "echo $TEXT",
                "--message",
                "Time for lunch",
                "--time",
                "12:00",
            ],
        )
        with mock.patch("horavox.core.subprocess.Popen") as mock_popen:
            _main()
        env = mock_popen.call_args.kwargs["env"]
        assert env["TEXT"] == "Time for lunch"
        assert env["MESSAGE"] == "Time for lunch"


# ==================== timer.py ====================


class TestTimerCommand:
    def test_generic_message_and_double_beep(self):
        from horavox import timer

        with mock.patch.object(sys, "argv", ["vox timer", "5m", "--debug", "--lang", "en"]):
            with mock.patch.object(timer.time, "sleep") as mock_sleep:
                with mock.patch.object(timer, "speak") as mock_speak:
                    timer.main()
                    mock_sleep.assert_called_once_with(300)
                    mock_speak.assert_called_once()
                    text = mock_speak.call_args[0][1]
                    assert text == "time is up"
                    assert mock_speak.call_args.kwargs["beep_count"] == 2

    def test_custom_message(self):
        from horavox import timer

        with mock.patch.object(sys, "argv", ["vox timer", "5m", "--debug", "-m", "noodles ready"]):
            with mock.patch.object(timer.time, "sleep"):
                with mock.patch.object(timer, "speak") as mock_speak:
                    timer.main()
                    assert mock_speak.call_args[0][1] == "noodles ready"

    def test_polish_generic_message(self):
        from horavox import timer

        with mock.patch.object(sys, "argv", ["vox timer", "10s", "--debug", "--lang", "pl"]):
            with mock.patch.object(timer.time, "sleep") as mock_sleep:
                with mock.patch.object(timer, "speak") as mock_speak:
                    timer.main()
                    mock_sleep.assert_called_once_with(10)
                    assert mock_speak.call_args[0][1] == "czas minął"

    def test_full_name_duration(self):
        from horavox import timer

        with mock.patch.object(sys, "argv", ["vox timer", "2 minutes", "--debug", "--lang", "en"]):
            with mock.patch.object(timer.time, "sleep") as mock_sleep:
                with mock.patch.object(timer, "speak"):
                    timer.main()
                    mock_sleep.assert_called_once_with(120)

    def test_invalid_duration_exits(self):
        from horavox import timer

        with mock.patch.object(sys, "argv", ["vox timer", "banana", "--debug"]):
            with pytest.raises(SystemExit):
                timer.main()

    def test_dispatches_from_main(self):
        from horavox.main import main

        with mock.patch.object(sys, "argv", ["vox", "timer", "5m", "--debug", "--lang", "en"]):
            with mock.patch("horavox.timer.time.sleep"):
                with mock.patch("horavox.timer.speak") as mock_speak:
                    with mock.patch("horavox.update.check_for_update"):
                        main()
                        mock_speak.assert_called_once()

    def test_keyboard_interrupt(self):
        from horavox import timer

        with mock.patch.object(sys, "argv", ["vox timer", "5m", "--debug"]):
            with mock.patch.object(timer.time, "sleep", side_effect=KeyboardInterrupt):
                timer.main()  # should not raise

    def test_exception_logs_error(self):
        from horavox import timer

        with mock.patch.object(sys, "argv", ["vox timer", "5m", "--debug"]):
            with mock.patch.object(timer.time, "sleep", side_effect=RuntimeError("boom")):
                with mock.patch.object(timer, "log_error") as mock_log:
                    with pytest.raises(RuntimeError):
                        timer.main()
                    mock_log.assert_called_once()

    def test_parse_args_defaults(self):
        from horavox import timer

        with mock.patch.object(sys, "argv", ["vox timer", "5m"]):
            args = timer.parse_args()
            assert args.duration == "5m"
            assert args.message is None
            assert args.background is False
            assert args.exec_cmd is None

    def test_exec_runs_when_timer_ends(self):
        from horavox import timer

        with mock.patch.object(
            sys, "argv", ["vox timer", "5m", "--debug", "-m", "done", "--exec", "echo hi"]
        ):
            with mock.patch.object(timer.time, "sleep"):
                with mock.patch.object(timer, "speak"):
                    with mock.patch.object(timer, "run_exec") as mock_exec:
                        timer.main()
                        mock_exec.assert_called_once()
                        # run_exec(command, text, target, message)
                        assert mock_exec.call_args[0][0] == "echo hi"
                        assert mock_exec.call_args[0][1] == "done"
                        assert mock_exec.call_args[0][3] == "done"

    def test_background_mode(self):
        from horavox import timer

        with mock.patch.object(sys, "argv", ["vox timer", "5m", "--background", "--nosound"]):
            with mock.patch.object(timer, "Daemonize") as mock_daemon:
                mock_instance = mock.MagicMock()
                mock_daemon.return_value = mock_instance
                timer.main()
                mock_daemon.assert_called_once()
                mock_instance.start.assert_called_once()

    def test_service_foreground_creates_session(self):
        from horavox import timer

        with mock.patch.object(sys, "argv", ["vox timer", "5m", "--debug"]):
            with mock.patch.dict(os.environ, {"HORAVOX_SERVICE": "1"}):
                with mock.patch("horavox.timer.ensure_user_dirs"):
                    with mock.patch("horavox.timer.create_session") as mock_create:
                        with mock.patch("horavox.timer.remove_session") as mock_remove:
                            with mock.patch("horavox.timer.run_timer"):
                                timer.main()
                                mock_create.assert_called_once()
                                assert mock_create.call_args[1]["session_type"] == "timer"
                                mock_remove.assert_called_once()

    def test_load_voice_nosound_returns_none(self):
        from horavox import timer

        args = argparse.Namespace(voice=None)
        with mock.patch.object(core, "NOSOUND", True):
            assert timer._load_voice(args, "en") is None

    def test_load_voice_loads_piper(self):
        from horavox import timer

        args = argparse.Namespace(voice="en_US-lessac-medium")
        mock_piper = mock.MagicMock()
        with mock.patch.object(core, "NOSOUND", False):
            with mock.patch.object(timer, "resolve_voice", return_value="/tmp/x.onnx"):
                with mock.patch.dict("sys.modules", {"piper": mock_piper}):
                    voice = timer._load_voice(args, "en")
        mock_piper.PiperVoice.load.assert_called_once_with("/tmp/x.onnx")
        assert voice is mock_piper.PiperVoice.load.return_value

    def test_run_timer_speaks_and_runs_exec(self):
        from horavox import timer

        args = argparse.Namespace(voice=None, exec_cmd="echo hi", message="done")
        with mock.patch.object(core, "NOSOUND", True):
            with mock.patch.object(timer.time, "sleep") as mock_sleep:
                with mock.patch.object(timer, "speak") as mock_speak:
                    with mock.patch.object(timer, "run_exec") as mock_exec:
                        timer.run_timer(args, "en", "done", 42)
        mock_sleep.assert_called_once_with(42)
        mock_speak.assert_called_once()
        assert mock_speak.call_args.kwargs["beep_count"] == timer.END_BEEPS
        mock_exec.assert_called_once()
        assert mock_exec.call_args[0][0] == "echo hi"

    # ---- reminder mode ----

    def test_target_datetime_duration(self):
        from horavox import timer

        now = datetime.datetime(2026, 7, 21, 10, 0, 0)
        assert timer._target_datetime("30m", now) == now + datetime.timedelta(minutes=30)

    def test_target_datetime_absolute_future(self):
        from horavox import timer

        now = datetime.datetime(2026, 7, 21, 10, 0, 0)
        assert timer._target_datetime("10:30", now) == datetime.datetime(2026, 7, 21, 10, 30, 0)

    def test_target_datetime_absolute_rolls_to_tomorrow(self):
        from horavox import timer

        now = datetime.datetime(2026, 7, 21, 11, 0, 0)
        assert timer._target_datetime("10:30", now) == datetime.datetime(2026, 7, 22, 10, 30, 0)

    def test_parse_reminders_sorted_and_deduped(self):
        from horavox import timer

        assert timer._parse_reminders("1h,30m,1h,1h30m") == [1800, 3600, 5400]

    def test_parse_reminders_empty(self):
        from horavox import timer

        assert timer._parse_reminders(None) == []

    def test_final_text_message_wins(self):
        from horavox import timer

        args = argparse.Namespace(message="Czas wyjść", name="pociąg")
        assert timer._final_text(args, "pl", core.load_durations("pl")) == "Czas wyjść"

    def test_final_text_now_with_name(self):
        from horavox import timer

        args = argparse.Namespace(message=None, name="pociąg")
        assert timer._final_text(args, "pl", core.load_durations("pl")) == "teraz pociąg"
        args_en = argparse.Namespace(message=None, name="the train")
        assert timer._final_text(args_en, "en", core.load_durations("en")) == "now the train"

    def test_final_text_generic_without_name(self):
        from horavox import timer

        args = argparse.Namespace(message=None, name=None)
        assert timer._final_text(args, "pl", core.load_durations("pl")) == "czas minął"

    def test_reminder_text_english(self):
        from horavox import timer

        args = argparse.Namespace(name="the train")
        d = core.load_durations("en")
        assert timer._reminder_text(args, "en", d, 3600) == "in one hour the train"
        assert timer._reminder_text(args, "en", d, 1800) == "in thirty minutes the train"
        assert (
            timer._reminder_text(args, "en", d, 5400) == "in one hour and thirty minutes the train"
        )

    def test_reminder_text_polish(self):
        from horavox import timer

        args = argparse.Namespace(name="pociąg")
        d = core.load_durations("pl")
        assert timer._reminder_text(args, "pl", d, 3600) == "za godzinę pociąg"
        assert timer._reminder_text(args, "pl", d, 1800) == "za trzydzieści minut pociąg"
        assert timer._reminder_text(args, "pl", d, 5400) == "za godzinę i trzydzieści minut pociąg"

    def test_reminder_text_no_name_trimmed(self):
        from horavox import timer

        args = argparse.Namespace(name=None)
        assert (
            timer._reminder_text(args, "en", core.load_durations("en"), 1800) == "in thirty minutes"
        )

    def test_build_events_sorts_and_appends_final(self):
        from horavox import timer

        args = argparse.Namespace(name="the train")
        d = core.load_durations("en")
        now = datetime.datetime(2026, 7, 21, 3, 0, 0)
        target = datetime.datetime(2026, 7, 21, 5, 0, 0)
        events = timer._build_events(
            args, "en", d, now, target, [1800, 3600, 5400], "now the train"
        )
        times = [e[0] for e in events]
        assert times == sorted(times)
        # 1h30m before (3:30), 1h before (4:00), 30m before (4:30), then target (5:00)
        assert [t.strftime("%H:%M") for t in times] == ["03:30", "04:00", "04:30", "05:00"]
        assert events[0][1] == "in one hour and thirty minutes the train"
        assert events[-1][1] == "now the train"

    def test_build_events_skips_past_reminders(self):
        from horavox import timer

        args = argparse.Namespace(name=None)
        d = core.load_durations("en")
        now = datetime.datetime(2026, 7, 21, 4, 45, 0)
        target = datetime.datetime(2026, 7, 21, 5, 0, 0)
        # 1h before (4:00) is in the past relative to now (4:45) -> skipped
        events = timer._build_events(args, "en", d, now, target, [3600, 600], "time is up")
        assert [t.strftime("%H:%M") for t, _ in events] == ["04:50", "05:00"]

    def test_run_reminders_fires_all_events(self):
        from horavox import timer

        now = datetime.datetime.now()
        events = [(now, "za godzinę pociąg"), (now, "teraz pociąg")]
        args = argparse.Namespace(voice=None, exec_cmd=None, message=None)
        with mock.patch.object(core, "NOSOUND", True):
            with mock.patch.object(timer, "prepare_speech") as mock_prep:
                with mock.patch.object(timer, "play_beep"):
                    with mock.patch.object(timer, "play_speech") as mock_play:
                        with mock.patch.object(timer.time, "sleep"):
                            timer.run_reminders(args, "pl", events)
        assert mock_prep.call_count == 2
        assert mock_play.call_count == 2

    def test_run_reminders_skips_past_event(self):
        from horavox import timer

        past = datetime.datetime.now() - datetime.timedelta(seconds=30)
        now = datetime.datetime.now()
        events = [(past, "old"), (now, "teraz pociąg")]
        args = argparse.Namespace(voice=None, exec_cmd=None, message=None)
        with mock.patch.object(core, "NOSOUND", True):
            with mock.patch.object(timer, "prepare_speech") as mock_prep:
                with mock.patch.object(timer, "play_beep"):
                    with mock.patch.object(timer, "play_speech"):
                        with mock.patch.object(timer.time, "sleep"):
                            timer.run_reminders(args, "pl", events)
        assert mock_prep.call_count == 1

    def test_run_reminders_waits_then_fires(self):
        from horavox import timer

        fire = datetime.datetime(2026, 7, 21, 5, 0, 0)
        args = argparse.Namespace(voice=None, exec_cmd=None, message=None)
        # now() sequence: far before target (tick wait), at target (fire),
        # then a moment before target inside the fire branch (remaining > 0 sleep)
        nows = [
            fire - datetime.timedelta(seconds=10),
            fire,
            fire - datetime.timedelta(seconds=1),
        ]
        with mock.patch.object(core, "NOSOUND", True):
            with mock.patch.object(timer, "prepare_speech"):
                with mock.patch.object(timer, "play_beep"):
                    with mock.patch.object(timer, "play_speech"):
                        with mock.patch.object(timer.time, "sleep") as mock_sleep:
                            with mock.patch.object(timer.datetime, "datetime") as mock_dt:
                                mock_dt.now.side_effect = nows
                                timer.run_reminders(args, "pl", [(fire, "teraz pociąg")])
        # one tick wait + one remaining-time sleep
        assert mock_sleep.call_count == 2

    def test_main_dispatches_to_run_reminders(self):
        from horavox import timer

        # Duration target (now+3h) so both reminders are always in the future,
        # regardless of wall-clock time when the test runs.
        with mock.patch.object(
            sys,
            "argv",
            ["vox timer", "3h", "--reminders", "30m,1h", "--name", "the train", "--debug"],
        ):
            with mock.patch.object(timer, "run_reminders") as mock_run:
                timer.main()
                mock_run.assert_called_once()
                events = mock_run.call_args[0][2]
                # two reminders + final target
                assert len(events) == 3
