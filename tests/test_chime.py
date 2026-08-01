"""Unit tests for the chime companion command (horavox.chime)."""

import json
import os
from unittest import mock

import pytest

from horavox import chime


class TestParseTime:
    def test_full_hour(self):
        assert chime.parse_time("10:00") == (10, 0)

    def test_half_hour(self):
        assert chime.parse_time("10:30") == (10, 30)

    def test_midnight(self):
        assert chime.parse_time("0:00") == (0, 0)

    def test_two_digit_hour(self):
        assert chime.parse_time("23:59") == (23, 59)

    @pytest.mark.parametrize("bad", ["10", "10:60", "24:00", "-1:00", "aa:bb", "10:00:00", ""])
    def test_invalid_raises(self, bad):
        with pytest.raises(ValueError):
            chime.parse_time(bad)


class TestStrikesForHour:
    @pytest.mark.parametrize(
        "hour,expected",
        [
            (0, 12),  # midnight
            (1, 1),
            (10, 10),
            (11, 11),
            (12, 12),  # noon
            (13, 1),
            (22, 10),
            (23, 11),
        ],
    )
    def test_twelve_hour_form(self, hour, expected):
        assert chime.strikes_for_hour(hour) == expected


class TestChime:
    @staticmethod
    def _sequence(hour, minute):
        # _mp3_path returns its 'kind' ("cut"/"end") so the sequence is easy to assert.
        # The whole strike must be a SINGLE _play_all call (one mpg123 process = no gaps).
        with mock.patch.object(chime, "_mp3_path", side_effect=lambda kind: kind):
            with mock.patch.object(chime, "_play_all") as play:
                chime.chime(hour, minute)
        if play.call_count == 0:
            return None
        assert play.call_count == 1
        return play.call_args.args[0]

    def test_full_hour_plays_cuts_then_end(self):
        # 9 cuts + 1 end = 10 bells, end last, in one call
        assert self._sequence(10, 0) == ["cut"] * 9 + ["end"]

    def test_one_oclock_single_end_no_cuts(self):
        assert self._sequence(1, 0) == ["end"]

    def test_midnight_twelve_bells(self):
        assert self._sequence(0, 0) == ["cut"] * 11 + ["end"]

    def test_half_hour_single_end(self):
        assert self._sequence(10, 30) == ["end"]

    def test_other_minute_is_silent(self):
        assert self._sequence(10, 15) is None


class TestMp3Path:
    def test_default_uses_bundled_data_dir(self, monkeypatch):
        monkeypatch.delenv("CHIME_DIR", raising=False)
        with mock.patch.object(chime, "_chime_config", return_value={}):
            assert chime._mp3_path("cut") == os.path.join(chime.DATA_DIR, "chime_cut.mp3")

    def test_chime_dir_env_override(self, monkeypatch):
        monkeypatch.setenv("CHIME_DIR", "/sounds")
        with mock.patch.object(chime, "_chime_config", return_value={}):
            assert chime._mp3_path("end") == os.path.join("/sounds", "chime_end.mp3")

    def test_config_override_wins_over_env(self, monkeypatch):
        monkeypatch.setenv("CHIME_DIR", "/sounds")
        cfg = {"mp3": {"cut": "~/my_cut.mp3", "end": "/abs/my_end.mp3"}}
        with mock.patch.object(chime, "_chime_config", return_value=cfg):
            assert chime._mp3_path("cut") == os.path.expanduser("~/my_cut.mp3")
            assert chime._mp3_path("end") == "/abs/my_end.mp3"

    def test_partial_config_falls_back(self, monkeypatch):
        monkeypatch.delenv("CHIME_DIR", raising=False)
        with mock.patch.object(chime, "_chime_config", return_value={"mp3": {"cut": "/only.mp3"}}):
            assert chime._mp3_path("cut") == "/only.mp3"
            assert chime._mp3_path("end") == os.path.join(chime.DATA_DIR, "chime_end.mp3")


class TestChimeConfig:
    def test_reads_chime_section(self, monkeypatch, tmp_path):
        import horavox.config as config

        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps({"settings": {}, "chime": {"mp3": {"cut": "/c.mp3"}}}))
        monkeypatch.setattr(config, "CONFIG_PATH", str(cfg_file))
        assert chime._chime_config() == {"mp3": {"cut": "/c.mp3"}}

    def test_missing_config_returns_empty(self, monkeypatch, tmp_path):
        import horavox.config as config

        monkeypatch.setattr(config, "CONFIG_PATH", str(tmp_path / "nope.json"))
        assert chime._chime_config() == {}

    def test_corrupt_config_returns_empty(self, monkeypatch, tmp_path):
        import horavox.config as config

        cfg_file = tmp_path / "config.json"
        cfg_file.write_text("{ not json")
        monkeypatch.setattr(config, "CONFIG_PATH", str(cfg_file))
        assert chime._chime_config() == {}


class TestPlayAll:
    def test_runs_mpg123_once_with_all_files(self):
        # A single process for the whole sequence — this is what removes the gap
        with mock.patch.object(chime.os.path, "exists", return_value=True):
            with mock.patch.object(chime.subprocess, "run") as run:
                chime._play_all(["/a.mp3", "/a.mp3", "/b.mp3"])
        run.assert_called_once_with(["mpg123", "-q", "/a.mp3", "/a.mp3", "/b.mp3"], check=False)

    def test_missing_files_warned_and_skipped(self, capsys):
        with mock.patch.object(chime.os.path, "exists", side_effect=lambda p: p == "/a.mp3"):
            with mock.patch.object(chime.subprocess, "run") as run:
                chime._play_all(["/a.mp3", "/b.mp3"])
        run.assert_called_once_with(["mpg123", "-q", "/a.mp3"], check=False)
        assert "missing sound file: /b.mp3" in capsys.readouterr().err

    def test_all_missing_skips_mpg123(self, capsys):
        with mock.patch.object(chime.os.path, "exists", return_value=False):
            with mock.patch.object(chime.subprocess, "run") as run:
                chime._play_all(["/a.mp3"])
        run.assert_not_called()
        assert "missing sound file" in capsys.readouterr().err

    def test_mpg123_missing_is_tolerated(self, capsys):
        with mock.patch.object(chime.os.path, "exists", return_value=True):
            with mock.patch.object(chime.subprocess, "run", side_effect=FileNotFoundError):
                chime._play_all(["/a.mp3"])
        assert "mpg123 not found" in capsys.readouterr().err


class TestMain:
    def test_no_args_usage_returns_1(self, capsys):
        assert chime.main(["chime.py"]) == 1
        assert "Usage" in capsys.readouterr().out

    def test_help_returns_0(self, capsys):
        assert chime.main(["chime.py", "--help"]) == 0
        assert "Usage" in capsys.readouterr().out

    def test_invalid_time_returns_1(self, capsys):
        assert chime.main(["chime.py", "bogus"]) == 1
        assert "invalid time" in capsys.readouterr().err

    def test_valid_time_dispatches_to_chime(self):
        with mock.patch.object(chime, "chime") as c:
            assert chime.main(["chime.py", "10:00"]) == 0
        c.assert_called_once_with(10, 0)
