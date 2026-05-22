"""Unit tests for horavox.core — language, time, voice, session utilities."""

import datetime
import json
import os
import sys
import tempfile
import time
import unittest.mock

import pytest

from horavox import core

# ==================== configure ====================


class TestConfigure:
    def teardown_method(self):
        core.VERBOSE = False
        core.NOSOUND = False
        core.VOLUME = 100

    def test_defaults(self):
        core.configure()
        assert core.VERBOSE is False
        assert core.NOSOUND is False
        assert core.VOLUME == 100

    def test_verbose(self):
        core.configure(verbose=True)
        assert core.VERBOSE is True

    def test_nosound_sets_volume_zero(self):
        core.configure(nosound=True)
        assert core.NOSOUND is True
        assert core.VOLUME == 0

    def test_volume_zero_sets_nosound(self):
        core.configure(volume=0)
        assert core.NOSOUND is True
        assert core.VOLUME == 0

    def test_volume_50(self):
        core.configure(volume=50)
        assert core.VOLUME == 50
        assert core.NOSOUND is False

    def test_debug_sets_both(self):
        core.configure(debug=True)
        assert core.VERBOSE is True
        assert core.NOSOUND is True
        assert core.VOLUME == 0

    def test_invalid_volume(self):
        with pytest.raises(SystemExit):
            core.configure(volume=200)

    def test_invalid_volume_negative(self):
        with pytest.raises(SystemExit):
            core.configure(volume=-1)


# ==================== detect_language ====================


class TestDetectLanguage:
    def test_returns_string(self):
        lang = core.detect_language()
        assert isinstance(lang, str)
        assert len(lang) >= 1

    def test_fallback_on_failure(self, monkeypatch):
        monkeypatch.setattr("locale.getlocale", lambda: (None, None))
        assert core.detect_language() == "en"

    def test_parses_locale(self, monkeypatch):
        monkeypatch.setattr("locale.getlocale", lambda: ("de_DE", "UTF-8"))
        assert core.detect_language() == "de"

    def test_exception_fallback(self, monkeypatch):
        def raise_err():
            raise RuntimeError("broken")

        monkeypatch.setattr("locale.getlocale", raise_err)
        assert core.detect_language() == "en"


# ==================== load_language_data ====================


class TestLoadLanguageData:
    def test_load_english_classic(self):
        data, lang = core.load_language_data("en", "classic")
        assert lang == "en"
        assert len(data["hours"]) == 24
        assert "full_hour" in data["patterns"]
        assert "quarter_past" in data["patterns"]

    def test_load_english_modern(self):
        data, lang = core.load_language_data("en", "modern")
        assert lang == "en"
        assert "time" in data["patterns"]
        assert len(data["minutes"]) >= 59

    def test_load_polish_classic(self):
        data, lang = core.load_language_data("pl", "classic")
        assert lang == "pl"
        assert data["hours"][0] == "północ"
        assert "next_hour_midnight" in data

    def test_load_polish_modern(self):
        data, lang = core.load_language_data("pl", "modern")
        assert lang == "pl"
        assert "time" in data["patterns"]

    def test_fallback_to_english(self):
        data, lang = core.load_language_data("xx", "classic")
        assert lang == "en"

    def test_hours_alt_defaults_to_hours(self):
        data, _ = core.load_language_data("en", "classic")
        assert "hours_alt" in data

    def test_invalid_mode(self):
        with pytest.raises(SystemExit):
            core.load_language_data("en", "nonexistent")

    def test_invalid_hours_count(self, tmp_path, monkeypatch):
        bad = {"classic": {"hours": ["a"] * 10, "minutes": {}, "patterns": {}}}
        lang_file = tmp_path / "bad.json"
        lang_file.write_text(json.dumps(bad))
        monkeypatch.setattr(core, "LANG_DIR", str(tmp_path))
        with pytest.raises(SystemExit):
            core.load_language_data("bad", "classic")

    def test_invalid_hours_alt_count(self, tmp_path, monkeypatch):
        bad = {
            "classic": {
                "hours": ["a"] * 24,
                "hours_alt": ["b"] * 10,
                "minutes": {},
                "patterns": {
                    "full_hour": "",
                    "quarter_past": "",
                    "half_past": "",
                    "quarter_to": "",
                    "minutes_past": "",
                    "minutes_to": "",
                },
            }
        }
        lang_file = tmp_path / "bad2.json"
        lang_file.write_text(json.dumps(bad))
        monkeypatch.setattr(core, "LANG_DIR", str(tmp_path))
        with pytest.raises(SystemExit):
            core.load_language_data("bad2", "classic")

    def test_missing_pattern(self, tmp_path, monkeypatch):
        bad = {
            "classic": {
                "hours": ["a"] * 24,
                "minutes": {},
                "patterns": {"full_hour": ""},
            }
        }
        lang_file = tmp_path / "bad3.json"
        lang_file.write_text(json.dumps(bad))
        monkeypatch.setattr(core, "LANG_DIR", str(tmp_path))
        with pytest.raises(SystemExit):
            core.load_language_data("bad3", "classic")

    def test_en_not_found(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "LANG_DIR", str(tmp_path))
        with pytest.raises(SystemExit):
            core.load_language_data("en", "classic")


# ==================== get_spoken_time ====================


class TestGetSpokenTime:
    @pytest.fixture
    def en_classic(self):
        data, _ = core.load_language_data("en", "classic")
        return data

    @pytest.fixture
    def en_modern(self):
        data, _ = core.load_language_data("en", "modern")
        return data

    @pytest.fixture
    def pl_classic(self):
        data, _ = core.load_language_data("pl", "classic")
        return data

    @pytest.fixture
    def pl_modern(self):
        data, _ = core.load_language_data("pl", "modern")
        return data

    # English classic
    def test_en_midnight(self, en_classic):
        assert core.get_spoken_time(en_classic, 0, 0) == "midnight"

    def test_en_noon(self, en_classic):
        assert core.get_spoken_time(en_classic, 12, 0) == "noon"

    def test_en_full_hour(self, en_classic):
        assert core.get_spoken_time(en_classic, 3, 0) == "three o'clock"

    def test_en_quarter_past(self, en_classic):
        assert core.get_spoken_time(en_classic, 9, 15) == "quarter past nine"

    def test_en_half_past(self, en_classic):
        assert core.get_spoken_time(en_classic, 10, 30) == "half past ten"

    def test_en_quarter_to(self, en_classic):
        assert core.get_spoken_time(en_classic, 9, 45) == "quarter to ten"

    def test_en_minutes_past(self, en_classic):
        assert core.get_spoken_time(en_classic, 3, 10) == "ten past three"

    def test_en_minutes_to(self, en_classic):
        assert core.get_spoken_time(en_classic, 3, 50) == "ten to four"

    def test_en_one_past(self, en_classic):
        assert core.get_spoken_time(en_classic, 3, 1) == "one past three"

    def test_en_one_to(self, en_classic):
        assert core.get_spoken_time(en_classic, 3, 59) == "one to four"

    # English modern
    def test_en_modern_midnight(self, en_modern):
        assert core.get_spoken_time(en_modern, 0, 0) == "midnight"

    def test_en_modern_time(self, en_modern):
        assert core.get_spoken_time(en_modern, 9, 30) == "nine thirty"

    def test_en_modern_oh_five(self, en_modern):
        assert core.get_spoken_time(en_modern, 9, 5) == "nine oh five"

    def test_en_modern_noon(self, en_modern):
        assert core.get_spoken_time(en_modern, 12, 0) == "noon"

    def test_en_modern_45(self, en_modern):
        assert core.get_spoken_time(en_modern, 5, 45) == "five forty five"

    # Polish classic — 12-hour idiomatic
    def test_pl_midnight(self, pl_classic):
        assert core.get_spoken_time(pl_classic, 0, 0) == "północ"

    def test_pl_noon(self, pl_classic):
        assert core.get_spoken_time(pl_classic, 12, 0) == "dwunasta"

    def test_pl_17_is_piata(self, pl_classic):
        assert core.get_spoken_time(pl_classic, 17, 0) == "piąta"

    def test_pl_quarter_to_six(self, pl_classic):
        assert core.get_spoken_time(pl_classic, 17, 45) == "za kwadrans szósta"

    def test_pl_half_past_approaching_midnight(self, pl_classic):
        assert core.get_spoken_time(pl_classic, 23, 30) == "wpół do dwunastej"

    def test_pl_after_midnight(self, pl_classic):
        assert core.get_spoken_time(pl_classic, 0, 5) == "pięć po północy"

    def test_pl_quarter_past(self, pl_classic):
        assert core.get_spoken_time(pl_classic, 9, 15) == "kwadrans po dziewiątej"

    # Polish modern — 24-hour digital
    def test_pl_modern_17_45(self, pl_modern):
        assert core.get_spoken_time(pl_modern, 17, 45) == "siedemnasta czterdzieści pięć"

    def test_pl_modern_midnight_five(self, pl_modern):
        assert core.get_spoken_time(pl_modern, 0, 5) == "zero pięć"

    def test_pl_modern_9_30(self, pl_modern):
        assert core.get_spoken_time(pl_modern, 9, 30) == "dziewiąta trzydzieści"


# ==================== time utilities ====================


class TestTimeUtilities:
    def test_time_to_minutes(self):
        assert core.time_to_minutes(0, 0) == 0
        assert core.time_to_minutes(12, 30) == 750
        assert core.time_to_minutes(23, 59) == 1439

    def test_is_in_range_normal(self):
        assert core.is_in_range(12, 0, 540, 1320) is True
        assert core.is_in_range(8, 0, 540, 1320) is False
        assert core.is_in_range(23, 0, 540, 1320) is False

    def test_is_in_range_midnight_wrap(self):
        assert core.is_in_range(23, 0, 1320, 360) is True
        assert core.is_in_range(2, 0, 1320, 360) is True
        assert core.is_in_range(12, 0, 1320, 360) is False

    def test_is_in_range_boundary(self):
        assert core.is_in_range(9, 0, 540, 1320) is True
        assert core.is_in_range(22, 0, 540, 1320) is True

    def test_parse_time_range_colon(self):
        assert core.parse_time_range("7:30", "--start") == (7, 30)

    def test_parse_time_range_bare_hour(self):
        assert core.parse_time_range("9", "--start") == (9, 0)

    def test_parse_time_range_two_digits(self):
        assert core.parse_time_range("22", "--end") == (22, 0)

    def test_parse_time_range_invalid(self):
        with pytest.raises(SystemExit):
            core.parse_time_range("25:00", "--start")

    def test_parse_time_range_invalid_minute(self):
        with pytest.raises(SystemExit):
            core.parse_time_range("12:61", "--start")

    def test_parse_time_arg(self):
        assert core.parse_time_arg("16:00") == (16, 0)

    def test_parse_time_arg_invalid(self):
        with pytest.raises(SystemExit):
            core.parse_time_arg("abc")


# ==================== beep_count_for_minute ====================


class TestBeepCount:
    def test_full_hour(self):
        assert core.beep_count_for_minute(0) == 2

    def test_half_hour(self):
        assert core.beep_count_for_minute(30) == 1

    def test_other_minutes(self):
        for m in [1, 10, 15, 20, 29, 31, 45, 59]:
            assert core.beep_count_for_minute(m) == 0


# ==================== voice management ====================


class TestResolveVoice:
    def test_resolve_voice_existing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "_vm", None)
        vm = core.VoiceManager(data_dir=str(tmp_path))
        monkeypatch.setattr(core, "_vm", vm)
        models_dir = tmp_path / "models"
        (models_dir / "test_voice.onnx").write_text("")
        path = core.resolve_voice("test_voice", "en")
        assert "test_voice.onnx" in path

    def test_resolve_voice_no_voice(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "_vm", None)
        vm = core.VoiceManager(data_dir=str(tmp_path))
        monkeypatch.setattr(core, "_vm", vm)
        with pytest.raises(SystemExit):
            core.resolve_voice(None, "zz")


# ==================== Legacy voice migration ====================


class TestMigrateLegacyVoices:
    def test_moves_files_from_voices_to_models(self, tmp_path, monkeypatch):
        voices_dir = tmp_path / "voices"
        voices_dir.mkdir()
        (voices_dir / "en_US-lessac-medium.onnx").write_text("model")
        (voices_dir / "en_US-lessac-medium.onnx.json").write_text("{}")
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        monkeypatch.setattr(core, "LEGACY_VOICES_DIR", str(voices_dir))
        core._migrate_legacy_voices(str(models_dir))
        assert (models_dir / "en_US-lessac-medium.onnx").exists()
        assert (models_dir / "en_US-lessac-medium.onnx.json").exists()
        assert not voices_dir.exists()

    def test_skips_existing_files_in_models(self, tmp_path, monkeypatch):
        voices_dir = tmp_path / "voices"
        voices_dir.mkdir()
        (voices_dir / "voice.onnx").write_text("old")
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        (models_dir / "voice.onnx").write_text("new")
        monkeypatch.setattr(core, "LEGACY_VOICES_DIR", str(voices_dir))
        core._migrate_legacy_voices(str(models_dir))
        assert (models_dir / "voice.onnx").read_text() == "new"
        assert (voices_dir / "voice.onnx").exists()

    def test_noop_when_no_legacy_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "LEGACY_VOICES_DIR", str(tmp_path / "voices"))
        core._migrate_legacy_voices(str(tmp_path / "models"))

    def test_get_voice_manager_triggers_migration(self, tmp_path, monkeypatch):
        voices_dir = tmp_path / "voices"
        voices_dir.mkdir()
        (voices_dir / "pl_PL-test.onnx").write_text("model")
        (voices_dir / "pl_PL-test.onnx.json").write_text("{}")
        monkeypatch.setattr(core, "_vm", None)
        monkeypatch.setattr(core, "USER_DIR", str(tmp_path))
        monkeypatch.setattr(core, "LEGACY_VOICES_DIR", str(voices_dir))
        core.get_voice_manager()
        assert (tmp_path / "models" / "pl_PL-test.onnx").exists()
        assert (tmp_path / "models" / "pl_PL-test.onnx.json").exists()
        monkeypatch.setattr(core, "_vm", None)


# ==================== TTS functions ====================


class TestTTS:
    def teardown_method(self):
        core.NOSOUND = False
        core.VOLUME = 100

    def test_play_blank_nosound(self, monkeypatch):
        core.NOSOUND = True
        called = []
        monkeypatch.setattr("horavox.core.play_mp3", lambda *a, **kw: called.append(1))
        core.play_blank()
        assert called == []

    def test_play_blank_sound(self, monkeypatch):
        core.NOSOUND = False
        called = []
        monkeypatch.setattr("horavox.core.play_mp3", lambda *a, **kw: called.append(a))
        core.play_blank()
        assert len(called) == 1

    def test_play_beep_nosound(self, monkeypatch):
        core.NOSOUND = True
        called = []
        monkeypatch.setattr("horavox.core.play_mp3", lambda *a, **kw: called.append(1))
        core.play_beep()
        assert called == []

    def test_play_beep_with_volume(self, monkeypatch):
        core.NOSOUND = False
        core.VOLUME = 50
        called = []
        monkeypatch.setattr("horavox.core.play_mp3", lambda *a, **kw: called.append((a, kw)))
        core.play_beep()
        assert len(called) == 1
        assert called[0][1].get("volume") == 50

    def test_play_beep_full_volume(self, monkeypatch):
        core.NOSOUND = False
        core.VOLUME = 100
        called = []
        monkeypatch.setattr("horavox.core.play_mp3", lambda *a, **kw: called.append((a, kw)))
        core.play_beep()
        assert len(called) == 1
        assert called[0][1].get("volume") == 100

    def test_play_speech_nosound(self, monkeypatch):
        core.NOSOUND = True
        called = []
        monkeypatch.setattr("horavox.core.play_wav", lambda *a, **kw: called.append(1))
        core.play_speech()
        assert called == []

    def test_play_speech_sound(self, monkeypatch, tmp_path):
        core.NOSOUND = False
        wav = tmp_path / "test.wav"
        wav.write_text("")
        monkeypatch.setattr(core, "TEMP_WAV", str(wav))
        monkeypatch.setattr("horavox.core.play_wav", lambda *a, **kw: None)
        core.play_speech()
        assert not wav.exists()

    def test_prepare_speech_nosound(self, monkeypatch):
        core.NOSOUND = True
        called = []
        monkeypatch.setattr(core, "log_spoken", lambda t: called.append(t))
        core.prepare_speech(None, "test")
        assert called == []  # log_spoken not called in nosound

    def test_speak_nosound(self, monkeypatch):
        core.NOSOUND = True
        core.speak(None, "test", beep_count=2)
        # Should not crash

    def test_prepare_combined_speech_nosound(self, monkeypatch):
        core.NOSOUND = True
        called = []
        monkeypatch.setattr(core, "log_spoken", lambda t: called.append(t))
        core.prepare_combined_speech(None, ["hello", "world"])
        assert called == []  # log_spoken not called in nosound

    def test_prepare_combined_speech_logs_all_texts(self, monkeypatch):
        core.NOSOUND = False
        logged = []
        monkeypatch.setattr(core, "log_spoken", lambda t: logged.append(t))
        monkeypatch.setattr(core, "play_blank", lambda: None)
        monkeypatch.setattr("horavox.core.synthesize_multi", lambda *a, **kw: None)
        monkeypatch.setattr("horavox.core.scale_volume", lambda *a, **kw: None)
        core.prepare_combined_speech(None, ["hello", "world"], pause_ms=100)
        assert logged == ["hello", "world"]


# ==================== session management ====================


class TestSessionManagement:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self._orig_sessions = core.SESSIONS_DIR
        core.SESSIONS_DIR = self.tmpdir

    def teardown_method(self):
        core.SESSIONS_DIR = self._orig_sessions
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_get_running_sessions_empty(self):
        sessions = core.get_running_sessions()
        assert sessions == []

    def test_get_running_sessions_no_dir(self):
        core.SESSIONS_DIR = "/nonexistent/path"
        sessions = core.get_running_sessions()
        assert sessions == []

    def test_create_and_get_session(self):
        pid = os.getpid()
        core.create_session(pid, "test-uuid-1234")
        sessions = core.get_running_sessions()
        assert len(sessions) == 1
        path, data = sessions[0]
        assert data["pid"] == pid
        assert "test-uuid-1234" in path

    def test_stale_session_cleaned(self):
        session_file = os.path.join(self.tmpdir, "stale.json")
        with open(session_file, "w") as f:
            json.dump({"pid": 999999999, "command": "fake"}, f)
        sessions = core.get_running_sessions()
        assert sessions == []
        assert not os.path.exists(session_file)

    def test_invalid_json_cleaned(self):
        session_file = os.path.join(self.tmpdir, "bad.json")
        with open(session_file, "w") as f:
            f.write("not json{{{")
        sessions = core.get_running_sessions()
        assert sessions == []
        assert not os.path.exists(session_file)

    def test_orphaned_pid_cleaned(self):
        pid_file = os.path.join(self.tmpdir, "orphan.pid")
        with open(pid_file, "w") as f:
            f.write("12345")
        core.get_running_sessions()
        assert not os.path.exists(pid_file)

    def test_kill_session(self):
        import subprocess

        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])

        session_file = os.path.join(self.tmpdir, "kill-test.json")
        data = {"pid": proc.pid, "command": "test"}
        with open(session_file, "w") as f:
            json.dump(data, f)

        core.kill_session(session_file, data)
        assert not os.path.exists(session_file)
        proc.wait()

    def test_kill_session_removes_pid_file(self):
        import subprocess

        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])

        session_json = os.path.join(self.tmpdir, "test-sess.json")
        session_pid = os.path.join(self.tmpdir, "test-sess.pid")
        data = {"pid": proc.pid, "command": "test"}
        with open(session_json, "w") as f:
            json.dump(data, f)
        with open(session_pid, "w") as f:
            f.write(str(proc.pid))

        core.kill_session(session_json, data)
        assert not os.path.exists(session_json)
        assert not os.path.exists(session_pid)
        proc.wait()


# ==================== logging ====================


class TestLogging:
    def test_log_to_file(self):
        with tempfile.NamedTemporaryFile(mode="r", suffix=".log", delete=False) as f:
            tmplog = f.name
        orig = core.LOG_FILE
        core.LOG_FILE = tmplog
        try:
            core.log_to_file("test message")
            with open(tmplog) as f:
                content = f.read()
            assert "test message" in content
            assert "[" in content
        finally:
            core.LOG_FILE = orig
            os.unlink(tmplog)

    def test_log_to_file_oserror(self):
        orig = core.LOG_FILE
        core.LOG_FILE = "/nonexistent/dir/file.log"
        core.log_to_file("should not crash")  # should swallow OSError
        core.LOG_FILE = orig

    def test_log_spoken(self):
        with tempfile.NamedTemporaryFile(mode="r", suffix=".log", delete=False) as f:
            tmplog = f.name
        orig = core.LOG_FILE
        core.LOG_FILE = tmplog
        try:
            core.log_spoken("spoken text")
            with open(tmplog) as f:
                assert "spoken text" in f.read()
        finally:
            core.LOG_FILE = orig
            os.unlink(tmplog)

    def test_log_error(self):
        with tempfile.NamedTemporaryFile(mode="r", suffix=".log", delete=False) as f:
            tmplog = f.name
        orig = core.LOG_FILE
        core.LOG_FILE = tmplog
        try:
            try:
                raise ValueError("test error")
            except ValueError:
                core.log_error()
            with open(tmplog) as f:
                content = f.read()
            assert "ValueError" in content
            assert "test error" in content
        finally:
            core.LOG_FILE = orig
            os.unlink(tmplog)

    def test_log_verbose(self, capsys):
        core.VERBOSE = True
        core.log("hello")
        out = capsys.readouterr().out
        assert "hello" in out
        core.VERBOSE = False

    def test_log_silent(self, capsys):
        core.VERBOSE = False
        core.log("hello")
        out = capsys.readouterr().out
        assert out == ""


# ==================== ensure_user_dirs ====================


class TestEnsureUserDirs:
    def test_creates_dirs(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "CACHE_DIR", str(tmp_path / "cache"))
        monkeypatch.setattr(core, "SESSIONS_DIR", str(tmp_path / "sessions"))
        core.ensure_user_dirs()
        assert (tmp_path / "cache").is_dir()
        assert (tmp_path / "sessions").is_dir()


# ==================== remove_session ====================


class TestRemoveSession:
    def test_removes_json_and_pid(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "SESSIONS_DIR", str(tmp_path))
        sid = "test-session-id"
        json_file = tmp_path / f"{sid}.json"
        pid_file = tmp_path / f"{sid}.pid"
        json_file.write_text("{}")
        pid_file.write_text("12345")
        core.remove_session(sid)
        assert not json_file.exists()
        assert not pid_file.exists()

    def test_removes_only_existing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "SESSIONS_DIR", str(tmp_path))
        sid = "test-session-id"
        json_file = tmp_path / f"{sid}.json"
        json_file.write_text("{}")
        core.remove_session(sid)
        assert not json_file.exists()


# ==================== kill_session ====================


class TestKillSession:
    def test_kill_success(self, tmp_path, capsys):
        path = str(tmp_path / "test.json")
        pid_path = str(tmp_path / "test.pid")
        with open(path, "w") as f:
            f.write("{}")
        with open(pid_path, "w") as f:
            f.write("12345")
        data = {"pid": 99999}

        with unittest.mock.patch("os.kill") as mock_kill:
            mock_kill.side_effect = [None, OSError("No such process")]
            core.kill_session(path, data)
        out = capsys.readouterr().out
        assert "Stopped" in out
        assert not os.path.exists(path)

    def test_kill_timeout_sigkill(self, capsys, tmp_path):
        path = str(tmp_path / "test.json")
        pid_path = str(tmp_path / "test.pid")
        with open(path, "w") as f:
            f.write("{}")
        with open(pid_path, "w") as f:
            f.write("12345")
        data = {"pid": 99999}
        import signal

        kill_calls = []

        def fake_kill(pid, sig):
            kill_calls.append(sig)
            if sig == signal.SIGKILL:
                return
            if sig == 0:
                return  # process still alive

        with unittest.mock.patch("os.kill", side_effect=fake_kill):
            with unittest.mock.patch("time.sleep"):
                core.kill_session(path, data)
        assert signal.SIGKILL in kill_calls

    def test_kill_os_error(self, capsys, tmp_path):
        path = str(tmp_path / "test.json")
        with open(path, "w") as f:
            f.write("{}")
        data = {"pid": 99999}
        with unittest.mock.patch("os.kill", side_effect=OSError("Permission denied")):
            core.kill_session(path, data)
        out = capsys.readouterr().out
        assert "Error stopping" in out


# ==================== parse_time_arg error ====================


class TestParseTimeArgError:
    def test_invalid_time_exits(self, capsys):
        with pytest.raises(SystemExit):
            core.parse_time_arg("25:00")

    def test_invalid_format_exits(self, capsys):
        with pytest.raises(SystemExit):
            core.parse_time_arg("abc")


# ==================== Sleep ====================


class TestReadWriteSleep:
    def test_read_sleep_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "SLEEP_FILE", str(tmp_path / "sleep.json"))
        assert core.read_sleep() is None

    def test_write_and_read_sleep(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "SLEEP_FILE", str(tmp_path / "sleep.json"))
        core.write_sleep()
        data = core.read_sleep()
        assert data is not None
        assert "timestamp" in data

    def test_write_sleep_with_until(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "SLEEP_FILE", str(tmp_path / "sleep.json"))
        until = time.time() + 3600
        core.write_sleep(until=until)
        data = core.read_sleep()
        assert data["until"] == until

    def test_clear_sleep(self, tmp_path, monkeypatch):
        sleep_file = tmp_path / "sleep.json"
        monkeypatch.setattr(core, "SLEEP_FILE", str(sleep_file))
        core.write_sleep()
        assert sleep_file.exists()
        core.clear_sleep()
        assert not sleep_file.exists()

    def test_clear_sleep_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "SLEEP_FILE", str(tmp_path / "sleep.json"))
        core.clear_sleep()

    def test_read_sleep_corrupt_json(self, tmp_path, monkeypatch):
        sleep_file = tmp_path / "sleep.json"
        sleep_file.write_text("{invalid json")
        monkeypatch.setattr(core, "SLEEP_FILE", str(sleep_file))
        core.VERBOSE = True
        assert core.read_sleep() is None
        core.VERBOSE = False

    def test_read_sleep_missing_timestamp(self, tmp_path, monkeypatch):
        sleep_file = tmp_path / "sleep.json"
        sleep_file.write_text('{"other": "data"}')
        monkeypatch.setattr(core, "SLEEP_FILE", str(sleep_file))
        assert core.read_sleep() is None

    def test_write_sleep_atomic(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "SLEEP_FILE", str(tmp_path / "sleep.json"))
        core.write_sleep()
        assert not (tmp_path / "sleep.json.tmp").exists()
        assert (tmp_path / "sleep.json").exists()


class TestIsSleepActive:
    def test_no_sleep_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "SLEEP_FILE", str(tmp_path / "sleep.json"))
        assert core.is_sleep_active() is False

    def test_sleep_active_no_range(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "SLEEP_FILE", str(tmp_path / "sleep.json"))
        core.write_sleep()
        assert core.is_sleep_active() is True

    def test_sleep_active_full_day_range(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "SLEEP_FILE", str(tmp_path / "sleep.json"))
        core.write_sleep()
        assert core.is_sleep_active(start_minutes=0, end_minutes=1439) is True

    def test_sleep_expired_until(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "SLEEP_FILE", str(tmp_path / "sleep.json"))
        core.write_sleep(until=time.time() - 10)
        assert core.is_sleep_active() is False
        assert not (tmp_path / "sleep.json").exists()

    def test_sleep_not_expired_until(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "SLEEP_FILE", str(tmp_path / "sleep.json"))
        core.write_sleep(until=time.time() + 3600)
        assert core.is_sleep_active() is True

    def test_auto_wake_range_restarted(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "SLEEP_FILE", str(tmp_path / "sleep.json"))
        yesterday_3pm = datetime.datetime.now().replace(
            hour=15, minute=0, second=0, microsecond=0
        ) - datetime.timedelta(days=1)
        sleep_file = tmp_path / "sleep.json"
        sleep_file.write_text(json.dumps({"timestamp": yesterday_3pm.timestamp()}))
        assert core.is_sleep_active(start_minutes=480, end_minutes=1320) is False

    def test_auto_wake_range_not_restarted(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "SLEEP_FILE", str(tmp_path / "sleep.json"))
        core.write_sleep()
        assert core.is_sleep_active(start_minutes=480, end_minutes=1320) is True

    def test_auto_wake_cross_midnight(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "SLEEP_FILE", str(tmp_path / "sleep.json"))
        two_days_ago_11pm = datetime.datetime.now().replace(
            hour=23, minute=0, second=0, microsecond=0
        ) - datetime.timedelta(days=2)
        sleep_file = tmp_path / "sleep.json"
        sleep_file.write_text(json.dumps({"timestamp": two_days_ago_11pm.timestamp()}))
        assert core.is_sleep_active(start_minutes=1320, end_minutes=120) is False

    def test_cross_midnight_still_sleeping(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "SLEEP_FILE", str(tmp_path / "sleep.json"))
        core.write_sleep()
        assert core.is_sleep_active(start_minutes=1320, end_minutes=120) is True


class TestNextRangeStartAfter:
    def test_sleep_before_range_start(self):
        now = datetime.datetime(2026, 5, 22, 7, 0, 0)
        ts = now.timestamp()
        result = core._next_range_start_after(ts, 480)
        assert result == datetime.datetime(2026, 5, 22, 8, 0, 0)

    def test_sleep_after_range_start(self):
        now = datetime.datetime(2026, 5, 22, 15, 0, 0)
        ts = now.timestamp()
        result = core._next_range_start_after(ts, 480)
        assert result == datetime.datetime(2026, 5, 23, 8, 0, 0)

    def test_sleep_at_range_start(self):
        now = datetime.datetime(2026, 5, 22, 8, 0, 0)
        ts = now.timestamp()
        result = core._next_range_start_after(ts, 480)
        assert result == datetime.datetime(2026, 5, 23, 8, 0, 0)


class TestCreateSessionExtended:
    def test_session_with_type(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "SESSIONS_DIR", str(tmp_path))
        core.create_session(123, "test-id", session_type="clock")
        with open(tmp_path / "test-id.json") as f:
            data = json.load(f)
        assert data["type"] == "clock"
        assert data["pid"] == 123

    def test_session_with_range(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "SESSIONS_DIR", str(tmp_path))
        core.create_session(123, "test-id", session_type="clock", start="8:00", end="22:00")
        with open(tmp_path / "test-id.json") as f:
            data = json.load(f)
        assert data["start"] == "8:00"
        assert data["end"] == "22:00"

    def test_session_without_range(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "SESSIONS_DIR", str(tmp_path))
        core.create_session(123, "test-id", session_type="at")
        with open(tmp_path / "test-id.json") as f:
            data = json.load(f)
        assert "start" not in data
        assert "end" not in data
        assert data["type"] == "at"

    def test_session_backward_compatible(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "SESSIONS_DIR", str(tmp_path))
        core.create_session(123, "test-id")
        with open(tmp_path / "test-id.json") as f:
            data = json.load(f)
        assert "type" not in data
        assert "start" not in data


# ==================== run_exec ====================


class TestRunExec:
    def test_sets_env_vars(self):
        with unittest.mock.patch("horavox.core.subprocess.Popen") as mock_popen:
            target = datetime.datetime(2026, 5, 22, 14, 30)
            core.run_exec("echo test", "quarter past two", target, "reminder")
        env = mock_popen.call_args.kwargs["env"]
        assert env["TEXT"] == "quarter past two"
        assert env["MESSAGE"] == "reminder"
        assert env["TIME"] == "14:30"
        assert env["DATE"] == "2026-05-22"

    def test_none_command_noop(self):
        with unittest.mock.patch("horavox.core.subprocess.Popen") as mock_popen:
            core.run_exec(None, "text", datetime.datetime.now())
        mock_popen.assert_not_called()

    def test_empty_message_defaults_to_empty_string(self):
        with unittest.mock.patch("horavox.core.subprocess.Popen") as mock_popen:
            core.run_exec("echo test", "text", datetime.datetime.now())
        env = mock_popen.call_args.kwargs["env"]
        assert env["MESSAGE"] == ""

    def test_oserror_logged(self):
        with unittest.mock.patch("horavox.core.subprocess.Popen", side_effect=OSError("fail")):
            core.VERBOSE = True
            core.run_exec("bad_cmd", "text", datetime.datetime.now())
            core.VERBOSE = False

    def test_shell_true(self):
        with unittest.mock.patch("horavox.core.subprocess.Popen") as mock_popen:
            core.run_exec("notify-send test", "text", datetime.datetime.now())
        assert mock_popen.call_args.kwargs["shell"] is True
