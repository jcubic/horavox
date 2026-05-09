"""Unit tests for horavox.core — language, time, voice, session utilities."""

import json
import os
import sys
import tempfile
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


class TestVoiceManagement:
    def test_is_voice_installed_false(self):
        assert core.is_voice_installed("nonexistent_voice_xyz") is False

    def test_is_voice_installed_true(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "VOICES_DIR", str(tmp_path))
        (tmp_path / "test_voice.onnx").write_text("")
        assert core.is_voice_installed("test_voice") is True

    def test_list_voices_for_unknown_language(self):
        voices = core.list_voices_for_language("zz")
        assert voices == []

    def test_list_voices_returns_list(self):
        voices = core.list_voices_for_language("en")
        assert isinstance(voices, list)
        if voices:
            v = voices[0]
            assert "key" in v
            assert "quality" in v
            assert "size_mb" in v
            assert "installed" in v

    def test_find_voice_for_language_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "VOICES_DIR", str(tmp_path))
        assert core.find_voice_for_language("xx") is None

    def test_find_voice_prefers_medium(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "VOICES_DIR", str(tmp_path))
        (tmp_path / "en_US-low-low.onnx").write_text("")
        (tmp_path / "en_US-lessac-medium.onnx").write_text("")
        result = core.find_voice_for_language("en")
        assert "medium" in result

    def test_find_voice_first_fallback(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "VOICES_DIR", str(tmp_path))
        (tmp_path / "en_US-low-low.onnx").write_text("")
        result = core.find_voice_for_language("en")
        assert result is not None

    def test_resolve_voice_existing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "VOICES_DIR", str(tmp_path))
        (tmp_path / "test_voice.onnx").write_text("")
        path = core.resolve_voice("test_voice", "en")
        assert path.endswith("test_voice.onnx")

    def test_resolve_voice_auto_detect(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "VOICES_DIR", str(tmp_path))
        (tmp_path / "en_US-test-medium.onnx").write_text("")
        path = core.resolve_voice(None, "en")
        assert "en_US" in path

    def test_resolve_voice_no_voice(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "VOICES_DIR", str(tmp_path))
        with pytest.raises(SystemExit):
            core.resolve_voice(None, "zz")

    def test_uninstall_voice(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(core, "VOICES_DIR", str(tmp_path))
        (tmp_path / "test_v.onnx").write_text("")
        (tmp_path / "test_v.onnx.json").write_text("{}")
        core.uninstall_voice("test_v")
        assert not (tmp_path / "test_v.onnx").exists()
        assert not (tmp_path / "test_v.onnx.json").exists()
        assert "uninstalled" in capsys.readouterr().out

    def test_uninstall_voice_not_found(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(core, "VOICES_DIR", str(tmp_path))
        core.uninstall_voice("nonexistent")
        assert "not found" in capsys.readouterr().out

    def test_download_voice_not_in_catalog(self, monkeypatch):
        monkeypatch.setattr(core, "get_voices_catalog", lambda: {})
        with pytest.raises(SystemExit):
            core.download_voice("nonexistent_voice")


# ==================== TTS functions ====================


class TestTTS:
    def teardown_method(self):
        core.NOSOUND = False
        core.VOLUME = 100

    def test_play_blank_nosound(self, monkeypatch):
        core.NOSOUND = True
        called = []
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: called.append(1))
        core.play_blank()
        assert called == []

    def test_play_blank_sound(self, monkeypatch):
        core.NOSOUND = False
        called = []
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: called.append(a))
        core.play_blank()
        assert len(called) == 1
        assert "mpg123" in called[0][0][0]

    def test_play_beep_nosound(self, monkeypatch):
        core.NOSOUND = True
        called = []
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: called.append(1))
        core.play_beep()
        assert called == []

    def test_play_beep_with_volume(self, monkeypatch):
        core.NOSOUND = False
        core.VOLUME = 50
        called = []
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: called.append(a[0]))
        core.play_beep()
        assert len(called) == 1
        assert "-f" in called[0]

    def test_play_beep_full_volume(self, monkeypatch):
        core.NOSOUND = False
        core.VOLUME = 100
        called = []
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: called.append(a[0]))
        core.play_beep()
        assert len(called) == 1
        assert "-f" not in called[0]

    def test_play_speech_nosound(self, monkeypatch):
        core.NOSOUND = True
        called = []
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: called.append(1))
        core.play_speech()
        assert called == []

    def test_play_speech_sound(self, monkeypatch, tmp_path):
        core.NOSOUND = False
        wav = tmp_path / "test.wav"
        wav.write_text("")
        monkeypatch.setattr(core, "TEMP_WAV", str(wav))
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: None)
        core.play_speech()
        assert not wav.exists()  # removed after play

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
        from unittest.mock import MagicMock

        core.NOSOUND = False
        logged = []
        monkeypatch.setattr(core, "log_spoken", lambda t: logged.append(t))
        monkeypatch.setattr(core, "play_blank", lambda: None)

        mock_voice = MagicMock()

        def fake_synthesize(text, wav_file):
            import struct

            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(22050)
            wav_file.writeframes(struct.pack("<h", 0) * 100)

        mock_voice.synthesize_wav = fake_synthesize
        core.prepare_combined_speech(mock_voice, ["hello", "world"], pause_ms=100)
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
        monkeypatch.setattr(core, "VOICES_DIR", str(tmp_path / "voices"))
        monkeypatch.setattr(core, "SESSIONS_DIR", str(tmp_path / "sessions"))
        core.ensure_user_dirs()
        assert (tmp_path / "cache").is_dir()
        assert (tmp_path / "voices").is_dir()
        assert (tmp_path / "sessions").is_dir()


# ==================== scale_wav_volume ====================


class TestScaleWavVolume:
    def _make_wav(self, path, samples_list):
        import array as arr_mod
        import wave as wav_mod

        samples = arr_mod.array("h", samples_list)
        with wav_mod.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(22050)
            w.writeframes(samples.tobytes())

    def _read_wav(self, path):
        import array as arr_mod
        import wave as wav_mod

        with wav_mod.open(path, "rb") as r:
            frames = r.readframes(r.getnframes())
        return arr_mod.array("h", frames)

    def test_no_change_at_100(self, tmp_path):
        core.VOLUME = 100
        wav = str(tmp_path / "test.wav")
        self._make_wav(wav, [1000, -1000, 500])
        core.scale_wav_volume(wav)
        result = self._read_wav(wav)
        assert list(result) == [1000, -1000, 500]
        core.VOLUME = 100

    def test_scale_at_50(self, tmp_path):
        core.VOLUME = 50
        wav = str(tmp_path / "test.wav")
        self._make_wav(wav, [1000, -1000, 500])
        core.scale_wav_volume(wav)
        result = self._read_wav(wav)
        assert result[0] == 500
        assert result[1] == -500
        assert result[2] == 250
        core.VOLUME = 100

    def test_clamp_at_max(self, tmp_path):
        core.VOLUME = 50
        wav = str(tmp_path / "test.wav")
        self._make_wav(wav, [32767, -32768])
        core.scale_wav_volume(wav)
        result = self._read_wav(wav)
        assert result[0] == 16383
        assert result[1] == -16384
        core.VOLUME = 100


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


# ==================== get_voices_catalog ====================


class TestGetVoicesCatalog:
    def test_catalog_fetch_and_cache(self, tmp_path, monkeypatch):
        import json
        from unittest.mock import MagicMock

        monkeypatch.setattr(core, "CACHE_DIR", str(tmp_path / "cache"))
        monkeypatch.setattr(core, "VOICES_DIR", str(tmp_path / "voices"))
        monkeypatch.setattr(core, "SESSIONS_DIR", str(tmp_path / "sessions"))

        catalog_data = {"test_voice": {"language": {"family": "en"}}}
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(catalog_data).encode("utf-8")
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with unittest.mock.patch("urllib.request.urlopen", return_value=mock_resp):
            result = core.get_voices_catalog()
        assert "test_voice" in result

    def test_catalog_error_with_stale_cache(self, tmp_path, monkeypatch, capsys):
        import json

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        monkeypatch.setattr(core, "CACHE_DIR", str(cache_dir))
        monkeypatch.setattr(core, "VOICES_DIR", str(tmp_path / "voices"))
        monkeypatch.setattr(core, "SESSIONS_DIR", str(tmp_path / "sessions"))

        cache_file = cache_dir / "voices.json"
        old_data = {"cached_voice": {"language": {"family": "en"}}}
        cache_file.write_text(json.dumps(old_data))
        old_time = os.path.getmtime(str(cache_file)) - 200000
        os.utime(str(cache_file), (old_time, old_time))

        core.VERBOSE = True
        with unittest.mock.patch("urllib.request.urlopen", side_effect=OSError("no net")):
            result = core.get_voices_catalog()
        assert "cached_voice" in result
        out = capsys.readouterr().out
        assert "cached version" in out
        core.VERBOSE = False

    def test_catalog_error_no_cache_exits(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(core, "CACHE_DIR", str(tmp_path / "cache"))
        monkeypatch.setattr(core, "VOICES_DIR", str(tmp_path / "voices"))
        monkeypatch.setattr(core, "SESSIONS_DIR", str(tmp_path / "sessions"))

        with unittest.mock.patch("urllib.request.urlopen", side_effect=OSError("no net")):
            with pytest.raises(SystemExit):
                core.get_voices_catalog()
        out = capsys.readouterr().out
        assert "could not fetch" in out


# ==================== download_voice ====================


class TestDownloadVoice:
    def test_download_unknown_voice(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(core, "CACHE_DIR", str(tmp_path / "cache"))
        monkeypatch.setattr(core, "VOICES_DIR", str(tmp_path / "voices"))
        monkeypatch.setattr(core, "SESSIONS_DIR", str(tmp_path / "sessions"))

        with unittest.mock.patch.object(core, "get_voices_catalog", return_value={}):
            with pytest.raises(SystemExit):
                core.download_voice("nonexistent_voice")
        out = capsys.readouterr().out
        assert "not found" in out

    def test_download_with_progress_cb(self, tmp_path, monkeypatch):
        monkeypatch.setattr(core, "VOICES_DIR", str(tmp_path / "voices"))

        catalog = {
            "test_voice": {
                "files": {
                    "test_voice.onnx": {"size_bytes": 1024},
                }
            }
        }
        calls = []

        def fake_retrieve(url, dest, reporthook=None):
            with open(dest, "w") as f:
                f.write("fake")
            if reporthook:
                reporthook(1, 512, 1024)

        with unittest.mock.patch.object(core, "get_voices_catalog", return_value=catalog):
            with unittest.mock.patch("urllib.request.urlretrieve", side_effect=fake_retrieve):
                core.download_voice("test_voice", progress_cb=lambda *a: calls.append(a))
        assert len(calls) == 1

    def test_download_without_progress_cb(self, tmp_path, monkeypatch, capsys):
        monkeypatch.setattr(core, "VOICES_DIR", str(tmp_path / "voices"))

        catalog = {
            "test_voice": {
                "files": {
                    "test_voice.onnx": {"size_bytes": 1024000},
                }
            }
        }

        def fake_retrieve(url, dest, reporthook=None):
            with open(dest, "w") as f:
                f.write("fake")

        with unittest.mock.patch.object(core, "get_voices_catalog", return_value=catalog):
            with unittest.mock.patch("urllib.request.urlretrieve", side_effect=fake_retrieve):
                core.download_voice("test_voice")
        out = capsys.readouterr().out
        assert "Downloading" in out
        assert "installed" in out

    def test_download_skips_existing(self, tmp_path, monkeypatch):
        voices_dir = tmp_path / "voices"
        voices_dir.mkdir()
        monkeypatch.setattr(core, "VOICES_DIR", str(voices_dir))

        (voices_dir / "test_voice.onnx").write_text("already here")

        catalog = {
            "test_voice": {
                "files": {
                    "test_voice.onnx": {"size_bytes": 1024},
                }
            }
        }
        with unittest.mock.patch.object(core, "get_voices_catalog", return_value=catalog):
            with unittest.mock.patch("urllib.request.urlretrieve") as mock_ret:
                core.download_voice("test_voice")
                mock_ret.assert_not_called()

    def test_download_error_cleans_up(self, tmp_path, monkeypatch, capsys):
        voices_dir = tmp_path / "voices"
        monkeypatch.setattr(core, "VOICES_DIR", str(voices_dir))

        catalog = {
            "test_voice": {
                "files": {
                    "test_voice.onnx": {"size_bytes": 1024},
                }
            }
        }

        def fake_retrieve(url, dest, reporthook=None):
            with open(dest, "w") as f:
                f.write("partial")
            raise OSError("download failed")

        with unittest.mock.patch.object(core, "get_voices_catalog", return_value=catalog):
            with unittest.mock.patch("urllib.request.urlretrieve", side_effect=fake_retrieve):
                with pytest.raises(SystemExit):
                    core.download_voice("test_voice")
        assert not (voices_dir / "test_voice.onnx").exists()


# ==================== resolve_voice download path ====================


class TestResolveVoiceDownload:
    def test_resolve_named_voice_downloads(self, tmp_path, monkeypatch):
        voices_dir = tmp_path / "voices"
        voices_dir.mkdir()
        monkeypatch.setattr(core, "VOICES_DIR", str(voices_dir))

        def fake_download(key, progress_cb=None):
            (voices_dir / f"{key}.onnx").write_text("fake")

        core.VERBOSE = True
        with unittest.mock.patch.object(core, "download_voice", side_effect=fake_download):
            result = core.resolve_voice("en_US-test-medium", "en")
        assert result.endswith("en_US-test-medium.onnx")
        core.VERBOSE = False
