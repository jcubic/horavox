"""Unit tests for command modules — main, clock, now, stop, voice.

Tests the option parsing and dispatch logic by mocking core functions.
"""

import argparse
import os
import sys
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
        import datetime

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
        import datetime

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
        import datetime

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
        import datetime

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
        import datetime

        from horavox.at import parse_date

        assert parse_date("2026-05-10") == datetime.date(2026, 5, 10)

    def test_parse_date_invalid(self):
        from horavox.at import parse_date

        with pytest.raises(SystemExit):
            parse_date("not-a-date")

    def test_parse_date_values_exact_date(self):
        import datetime

        from horavox.at import parse_date_values

        result = parse_date_values("2026-05-10")
        assert result == [datetime.date(2026, 5, 10)]

    def test_parse_date_values_multiple_dates(self):
        import datetime

        from horavox.at import parse_date_values

        result = parse_date_values("2026-05-10,2026-05-12")
        assert result == [datetime.date(2026, 5, 10), datetime.date(2026, 5, 12)]

    def test_parse_date_values_day_name(self):
        import datetime

        from horavox.at import parse_date_values

        result = parse_date_values("monday")
        assert len(result) == 1
        assert result[0].weekday() == 0
        assert result[0] > datetime.date.today()

    def test_parse_date_values_mixed(self):
        import datetime

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
        import datetime

        from horavox.at import parse_date_values

        result = parse_date_values("2026-05-10,2026-05-10")
        assert result == [datetime.date(2026, 5, 10)]

    def test_parse_date_values_invalid_string(self):
        from horavox.at import parse_date_values

        with pytest.raises(SystemExit):
            parse_date_values("not-a-date")

    def test_parse_date_values_sorted(self):
        import datetime

        from horavox.at import parse_date_values

        result = parse_date_values("2026-12-25,2026-05-10")
        assert result == [datetime.date(2026, 5, 10), datetime.date(2026, 12, 25)]

    def test_date_with_exit_at_scheduled_time(self):
        import datetime

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

    def test_run_at_once_multiple_dates(self, capsys):
        import datetime

        from horavox import at as at_mod
        from horavox.at import run_at_once

        core.configure(debug=True)
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
        import datetime

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
        import datetime

        from horavox.at import _next_weekday

        today = datetime.date.today()
        result = _next_weekday(today.weekday())
        assert result > today
        assert result == today + datetime.timedelta(days=7)

    def test_next_weekday_tomorrow(self):
        import datetime

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
        import datetime

        from horavox.at import _next_repeat_target

        monday_noon = datetime.datetime(2026, 5, 4, 12, 0, 0)
        schedule = [(14, 0)]
        repeat_days = {0}  # Monday only
        target = _next_repeat_target(monday_noon, schedule, repeat_days)
        assert target == datetime.datetime(2026, 5, 4, 14, 0)

    def test_next_repeat_target_skips_day(self):
        import datetime

        from horavox.at import _next_repeat_target

        tuesday_noon = datetime.datetime(2026, 5, 5, 12, 0, 0)
        schedule = [(10, 0)]
        repeat_days = {0}  # Monday only
        target = _next_repeat_target(tuesday_noon, schedule, repeat_days)
        assert target.weekday() == 0
        assert target.date() == datetime.date(2026, 5, 11)

    def test_repeat_wrong_day_no_speak(self, capsys):
        """--exit on a day not in repeat_days should not speak."""
        import datetime

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

    def test_list_has_installed_marker(self, capsys):
        from horavox import voice

        with mock.patch.object(core, "is_voice_installed", return_value=True):
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

    def test_get_lang_name(self):
        from horavox.voice import get_lang_name

        name = get_lang_name("en")
        assert isinstance(name, str)
        assert len(name) > 0

    def test_get_lang_name_unknown(self):
        from horavox.voice import get_lang_name

        name = get_lang_name("zz")
        assert name == "zz"

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

    def test_render_list(self):
        from horavox.voice import render_list

        voices = [
            {"key": "test_voice", "quality": "medium", "size_mb": 60, "installed": True},
            {"key": "other_voice", "quality": "high", "size_mb": 100, "installed": False},
        ]
        lines = render_list(voices, 0, "Test", "tt")
        text = "\n".join(lines)
        assert "test_voice" in text
        assert "other_voice" in text
        assert "[*]" in text
        assert ">" in text

    def test_progress_bar(self, capsys):
        from horavox.voice import progress_bar

        progress_bar("test.onnx", 5, 1024, 10240)
        # Just verify it doesn't crash; output goes to stdout

    def test_progress_bar_zero_total(self):
        from horavox.voice import progress_bar

        progress_bar("test.onnx", 0, 0, 0)  # should return early

    def test_progress_bar_complete(self, capsys):
        from horavox.voice import progress_bar

        progress_bar("test.onnx", 10, 1024, 10240)  # 100%

    def test_render_list_no_status(self):
        from horavox.voice import render_list

        voices = [{"key": "v1", "quality": "low", "size_mb": 30, "installed": False}]
        lines = render_list(voices, 0, "Test", "tt")
        assert any("v1" in line for line in lines)
        assert not any("status" in line.lower() for line in lines)

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

    def test_render_list_shows_default_marker(self):
        from horavox.voice import render_list

        voices = [
            {"key": "en_US-lessac-medium", "quality": "medium", "size_mb": 60, "installed": True},
            {"key": "en_US-other-high", "quality": "high", "size_mb": 100, "installed": False},
        ]
        lines = render_list(voices, 0, "English", "en", default_key="en_US-lessac-medium")
        text = "\n".join(lines)
        assert "[D]" in text
        assert "[*]" in text

    def test_render_list_no_default_when_none(self):
        from horavox.voice import render_list

        voices = [
            {"key": "en_US-lessac-medium", "quality": "medium", "size_mb": 60, "installed": False},
        ]
        lines = render_list(voices, 0, "English", "en", default_key=None)
        text = "\n".join(lines)
        assert "[D]" not in text

    def test_cmd_list_shows_default_marker(self, capsys):
        from horavox.voice import cmd_list

        with mock.patch.object(core, "is_voice_installed", return_value=True):
            cmd_list("pl")
        out = capsys.readouterr().out
        assert "[D]" in out

    def test_cmd_list_config_voice_default(self, capsys):
        from horavox.voice import cmd_list

        with mock.patch.object(core, "is_voice_installed", return_value=True):
            cmd_list("pl", config_voice="pl_PL-darkman-medium")
        out = capsys.readouterr().out
        assert "[D]" in out

    def test_render_list_with_status(self):
        from horavox.voice import render_list

        voices = [{"key": "v1", "quality": "low", "size_mb": 30, "installed": False}]
        lines = render_list(voices, 0, "Test", "tt", status="Done!")
        assert any("Done!" in line for line in lines)

    def test_draw(self, capsys):
        from horavox.voice import draw

        draw(["line1", "line2"], 0)
        out = capsys.readouterr().out
        assert "line1" in out
        assert "line2" in out

    def test_draw_overwrite(self, capsys):
        from horavox.voice import draw

        draw(["first"], 0)
        draw(["second"], 1)
        out = capsys.readouterr().out
        assert "second" in out

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
            # No voices = early return, won't crash
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

    def test_getch_regular_key(self):
        from horavox.voice import getch

        with mock.patch("sys.stdin") as mock_stdin:
            mock_stdin.fileno.return_value = 0
            mock_stdin.read.return_value = "q"
            with mock.patch("termios.tcgetattr", return_value=[]):
                with mock.patch("termios.tcsetattr"):
                    with mock.patch("tty.setraw"):
                        result = getch()
        assert result == "q"

    def test_getch_arrow_up(self):
        from horavox.voice import getch

        with mock.patch("sys.stdin") as mock_stdin:
            mock_stdin.fileno.return_value = 0
            mock_stdin.read.side_effect = ["\x1b", "[", "A"]
            with mock.patch("termios.tcgetattr", return_value=[]):
                with mock.patch("termios.tcsetattr"):
                    with mock.patch("tty.setraw"):
                        result = getch()
        assert result == "UP"

    def test_getch_arrow_down(self):
        from horavox.voice import getch

        with mock.patch("sys.stdin") as mock_stdin:
            mock_stdin.fileno.return_value = 0
            mock_stdin.read.side_effect = ["\x1b", "[", "B"]
            with mock.patch("termios.tcgetattr", return_value=[]):
                with mock.patch("termios.tcsetattr"):
                    with mock.patch("tty.setraw"):
                        result = getch()
        assert result == "DOWN"

    def test_getch_escape_other(self):
        from horavox.voice import getch

        with mock.patch("sys.stdin") as mock_stdin:
            mock_stdin.fileno.return_value = 0
            mock_stdin.read.side_effect = ["\x1b", "x"]
            with mock.patch("termios.tcgetattr", return_value=[]):
                with mock.patch("termios.tcsetattr"):
                    with mock.patch("tty.setraw"):
                        result = getch()
        assert result is None

    def test_cmd_interactive_quit(self):
        """Test interactive mode exits on 'q' key."""
        from horavox import voice

        voices = [
            {"key": "test_v", "quality": "medium", "size_mb": 60, "installed": False},
        ]
        with mock.patch.object(sys, "argv", ["vox voice", "--lang", "en"]):
            with mock.patch.object(voice, "list_voices_for_language", return_value=voices):
                with mock.patch.object(voice, "get_lang_name", return_value="English"):
                    with mock.patch.object(voice, "getch", return_value="q"):
                        with mock.patch.object(voice, "draw"):
                            voice.cmd_interactive("en")

    def test_cmd_interactive_install(self):
        """Test interactive mode installs on 'i' key then quits."""
        from horavox import voice

        voices = [
            {"key": "test_v", "quality": "medium", "size_mb": 60, "installed": False},
        ]
        call_count = [0]

        def fake_getch():
            call_count[0] += 1
            if call_count[0] == 1:
                return "i"
            return "q"

        with mock.patch.object(sys, "argv", ["vox voice", "--lang", "en"]):
            with mock.patch.object(voice, "list_voices_for_language", return_value=voices):
                with mock.patch.object(voice, "get_lang_name", return_value="English"):
                    with mock.patch.object(voice, "getch", side_effect=fake_getch):
                        with mock.patch.object(voice, "draw"):
                            with mock.patch.object(voice, "download_voice") as mock_dl:
                                voice.cmd_interactive("en")
                                mock_dl.assert_called_once_with(
                                    "test_v", progress_cb=voice.progress_bar
                                )
        assert voices[0]["installed"] is True

    def test_cmd_interactive_uninstall(self):
        """Test interactive mode uninstalls on 'u' key then quits."""
        from horavox import voice

        voices = [
            {"key": "test_v", "quality": "medium", "size_mb": 60, "installed": True},
        ]
        call_count = [0]

        def fake_getch():
            call_count[0] += 1
            if call_count[0] == 1:
                return "u"
            return "q"

        with mock.patch.object(voice, "list_voices_for_language", return_value=voices):
            with mock.patch.object(voice, "get_lang_name", return_value="English"):
                with mock.patch.object(voice, "getch", side_effect=fake_getch):
                    with mock.patch.object(voice, "draw"):
                        with mock.patch.object(voice, "uninstall_voice") as mock_rm:
                            voice.cmd_interactive("en")
                            mock_rm.assert_called_once_with("test_v")
        assert voices[0]["installed"] is False

    def test_cmd_interactive_already_installed(self):
        """Pressing 'i' on installed voice shows status."""
        from horavox import voice

        voices = [
            {"key": "v", "quality": "medium", "size_mb": 60, "installed": True},
        ]
        call_count = [0]

        def fake_getch():
            call_count[0] += 1
            if call_count[0] == 1:
                return "i"
            return "q"

        with mock.patch.object(voice, "list_voices_for_language", return_value=voices):
            with mock.patch.object(voice, "get_lang_name", return_value="Test"):
                with mock.patch.object(voice, "getch", side_effect=fake_getch):
                    with mock.patch.object(voice, "draw"):
                        with mock.patch.object(voice, "download_voice") as mock_dl:
                            voice.cmd_interactive("en")
                            mock_dl.assert_not_called()

    def test_cmd_interactive_not_installed_uninstall(self):
        """Pressing 'u' on not-installed voice shows status."""
        from horavox import voice

        voices = [
            {"key": "v", "quality": "medium", "size_mb": 60, "installed": False},
        ]
        call_count = [0]

        def fake_getch():
            call_count[0] += 1
            if call_count[0] == 1:
                return "u"
            return "q"

        with mock.patch.object(voice, "list_voices_for_language", return_value=voices):
            with mock.patch.object(voice, "get_lang_name", return_value="Test"):
                with mock.patch.object(voice, "getch", side_effect=fake_getch):
                    with mock.patch.object(voice, "draw"):
                        with mock.patch.object(voice, "uninstall_voice") as mock_rm:
                            voice.cmd_interactive("en")
                            mock_rm.assert_not_called()

    def test_render_list_has_enter_hint(self):
        from horavox.voice import render_list

        voices = [{"key": "v1", "quality": "low", "size_mb": 30, "installed": False}]
        lines = render_list(voices, 0, "Test", "tt")
        text = "\n".join(lines)
        assert "Enter" in text
        assert "Test" in text

    def test_speak_with_voice(self):
        from horavox.voice import _speak_with_voice

        mock_piper = mock.MagicMock()
        with mock.patch.dict("sys.modules", {"piper": mock_piper}):
            with mock.patch("horavox.voice.speak") as mock_speak:
                with mock.patch("horavox.voice.load_language_data") as mock_lang:
                    mock_lang.return_value = ({"patterns": {}}, "en")
                    with mock.patch("horavox.voice.get_spoken_time", return_value="three o'clock"):
                        _speak_with_voice("en_US-lessac-medium", "en")
            mock_piper.PiperVoice.load.assert_called_once()
            mock_speak.assert_called_once()

    def test_enter_speaks_installed_voice(self):
        from horavox import voice

        voices = [
            {"key": "en_US-lessac-medium", "quality": "medium", "size_mb": 60, "installed": True},
        ]
        with mock.patch.object(voice, "list_voices_for_language", return_value=voices):
            with mock.patch.object(voice, "get_lang_name", return_value="English"):
                with mock.patch.object(voice, "getch", side_effect=["\r", "q"]):
                    with mock.patch.object(voice, "draw"):
                        with mock.patch.object(voice, "_speak_with_voice") as mock_speak:
                            voice.cmd_interactive("en")
                            mock_speak.assert_called_once_with(
                                "en_US-lessac-medium", "en", "classic"
                            )

    def test_enter_installs_then_speaks(self):
        from horavox import voice

        voices = [
            {"key": "en_US-lessac-medium", "quality": "medium", "size_mb": 60, "installed": False},
        ]
        with mock.patch.object(voice, "list_voices_for_language", return_value=voices):
            with mock.patch.object(voice, "get_lang_name", return_value="English"):
                with mock.patch.object(voice, "getch", side_effect=["\r", "q"]):
                    with mock.patch.object(voice, "draw"):
                        with mock.patch.object(voice, "download_voice") as mock_dl:
                            with mock.patch.object(voice, "_speak_with_voice") as mock_speak:
                                voice.cmd_interactive("en")
                                mock_dl.assert_called_once_with(
                                    "en_US-lessac-medium", progress_cb=voice.progress_bar
                                )
                                mock_speak.assert_called_once_with(
                                    "en_US-lessac-medium", "en", "classic"
                                )
                                assert voices[0]["installed"] is True


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
        import datetime

        from horavox import at, core

        core.configure(nosound=True, verbose=True)
        args = argparse.Namespace(voice=None, message=None, time=None, exit=False)
        lang_data = {"hours": {}, "minutes": {}, "connectors": {}}
        schedule = [(10, 0)]
        target_dates = [datetime.date.today() - datetime.timedelta(days=1)]

        at.run_at_once(args, "en", lang_data, datetime.timedelta(0), schedule, target_dates)
        out = capsys.readouterr().out
        assert "passed" in out
        core.configure(verbose=False)

    def test_run_at_once_simulated_time_log(self, capsys):
        import datetime

        from horavox import at, core

        core.configure(nosound=True, verbose=True)
        now = datetime.datetime.now()
        future_time = (now + datetime.timedelta(hours=2)).replace(second=0, microsecond=0)
        args = argparse.Namespace(voice=None, message=None, time="14:00", exit=False)
        lang_data = {"hours": {}, "minutes": {}, "connectors": {}}
        schedule = [(future_time.hour, future_time.minute)]
        target_dates = [datetime.date.today()]
        offset = datetime.timedelta(0)

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
    def test_run_at_once_announces_and_exits(self):
        import datetime

        from horavox import at, core

        core.configure(nosound=True, verbose=True)
        now = datetime.datetime.now().replace(second=0, microsecond=0)
        args = argparse.Namespace(voice=None, message=None, time=None, exit=False)
        lang_data = {"hours": {}, "minutes": {}, "connectors": {}}
        schedule = [(now.hour, now.minute)]
        target_dates = [now.date()]

        with mock.patch.object(at, "prepare_speech"):
            with mock.patch.object(at, "play_beep"):
                with mock.patch.object(at, "play_speech"):
                    with mock.patch("time.sleep"):
                        at.run_at_once(
                            args,
                            "en",
                            lang_data,
                            datetime.timedelta(0),
                            schedule,
                            target_dates,
                        )
        core.configure(verbose=False)

    def test_run_at_once_skips_past_target(self):
        import datetime

        from horavox import at, core

        core.configure(nosound=True, verbose=True)
        now = datetime.datetime.now()
        past = now - datetime.timedelta(minutes=10)
        args = argparse.Namespace(voice=None, message=None, time=None, exit=False)
        lang_data = {"hours": {}, "minutes": {}, "connectors": {}}
        schedule = [(past.hour, past.minute)]
        target_dates = [now.date()]

        at.run_at_once(
            args,
            "en",
            lang_data,
            datetime.timedelta(0),
            schedule,
            target_dates,
        )
        core.configure(verbose=False)


class TestAtRepeatExit:
    def test_run_at_repeat_exit_not_matching(self, capsys):
        import datetime

        from horavox import at, core

        core.configure(nosound=True, verbose=True)
        args = argparse.Namespace(voice=None, message=None, time=None, exit=True)
        lang_data = {"hours": {}, "minutes": {}, "connectors": {}}
        schedule = [(3, 0)]
        repeat_days = {0, 1, 2, 3, 4, 5, 6}

        at.run_at_repeat(args, "en", lang_data, datetime.timedelta(0), schedule, repeat_days)
        out = capsys.readouterr().out
        assert "not at a scheduled time" in out
        core.configure(verbose=False)

    def test_run_at_repeat_logs_with_simulated_time(self, capsys):
        import datetime

        from horavox import at, core

        core.configure(nosound=True, verbose=True)
        args = argparse.Namespace(voice=None, message=None, time="10:00", exit=False)
        lang_data = {"hours": {}, "minutes": {}, "connectors": {}}
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
        import datetime

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
        )
        freq = 60
        h, m = now.hour, now.minute
        if m % freq == 0:
            start_min = (h * 60 + m + 60) % 1440
            end_min = (h * 60 + m + 120) % 1440
        else:
            start_min = ((h * 60 + m) // 60 + 1) * 60 % 1440
            end_min = start_min + 60
        lang_data = {"hours": {}, "minutes": {}, "connectors": {}}
        with mock.patch("horavox.config.get_mapping", return_value=[]):
            with mock.patch("horavox.config.load_config", return_value={"settings": {}}):
                clock.run_clock(args, "en", lang_data, datetime.timedelta(0), start_min, end_min)
        out = capsys.readouterr().out
        assert "outside range" in out or "not at announcement slot" in out
        core.configure(verbose=False)

    def test_clock_loop_log_messages(self, capsys):
        import datetime

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
        )
        lang_data = {"hours": {}, "minutes": {}, "connectors": {}}

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
        import datetime

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
        )
        lang_data = {"hours": {}, "minutes": {}, "connectors": {}}

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
        import datetime

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
        )
        lang_data = {"hours": {}, "minutes": {}, "connectors": {}}

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
        import datetime

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
        )
        lang_data = {"hours": {}, "minutes": {}, "connectors": {}}
        now = datetime.datetime.now().replace(minute=0, second=6, microsecond=0)
        offset = now - datetime.datetime.now()

        with mock.patch("horavox.config.get_mapping", return_value=[]):
            with mock.patch("horavox.config.load_config", return_value={"settings": {}}):
                clock.run_clock(args, "en", lang_data, offset, 0, 23 * 60 + 59)
        core.configure(verbose=False)
