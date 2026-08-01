# HoraVox — Agent Context

## What this is

A multi-language speaking clock CLI using [Piper](https://github.com/rhasspy/piper) TTS. Runs offline with local AI voice models. Git-style subcommands (`vox <command>`).

## Project structure

```text
src/horavox/
  __init__.py     re-exports __version__ and main
  core.py         shared library — paths, logging, language, TTS, voice, sessions
  main.py         CLI dispatcher (vox <command>)
  clock.py        vox clock — speaking clock loop + daemon
  now.py          vox now — speak once
  list.py         vox list — list running daemons
  stop.py         vox stop — stop daemons (interactive if multiple)
  sleep.py        vox sleep — mute/resume daemons (on/off, auto-wake on range restart)
  wakeup.py       vox wakeup — thin wrapper, same as 'vox sleep off'
  timer.py        vox timer — count down to time/duration; reminders (--reminders/--name), --background, --exec
  voice.py        vox voice — interactive voice browser (i/u keys, arrow nav)
  service.py      vox service — install/remove/list/start/run autostart instances
  registry.py     CRUD for ~/.horavox/data.json instance registry
  config.py       vox config — get/set defaults and aliases
  chime.py        `chime` command (NOT a vox subcommand) — strike the hour, for --exec
  platforms/
    __init__.py   platform detection
    linux.py      systemd user service backend
    macos.py      launchd user agent backend
    windows.py    Windows startup folder backend
  data/
    lang/{en,pl}.json  time idiom data per language
    blank.mp3   silent MP3 for Bluetooth audio wake-up
    beep.mp3    beep sound for hour/half-hour signals
    chime_cut.mp3 / chime_end.mp3  bell sounds for the `chime` command
tests/
  test_core.py        unit tests for core (90% target)
  test_commands.py    command tests with mocked core
  test_install.py     service/registry/platform tests
  test_cli.py         E2E subprocess tests (HOME isolated to /tmp)
  test_chime.py       tests for horavox.chime
```

`chime.py` is a package module but NOT a vox subcommand — it installs as its own `chime` console command (entry point in pyproject) for use with `--exec`, e.g. `vox clock --freq 30 --exec 'chime "$TIME"'`. mp3 resolution per file (`chime._mp3_path`): config `chime.mp3.{cut,end}` (via `load_config`) → `CHIME_DIR` env → bundled `data/chime_{cut,end}.mp3`. Paths resolved at call time (not import) so config is honored. The whole strike is played by a **single** `mpg123` process (`_play_all` passes all files as args) — do NOT revert to one `subprocess` per file, that reintroduces an audible gap between bells (process spawn + audio-device reopen). `main()` returns an int exit code (console_scripts wraps it in `sys.exit`).

## Runtime data (`~/.horavox/`)

- `models/` — downloaded `.onnx` Piper models (managed by voxkit)
- `cache/voices.json` — Hugging Face catalog cache (24h TTL)
- `sessions/<uuid>.json` — running daemon metadata `{pid, command, type, start, end}`
- `sessions/<uuid>.pid` — daemon PID file (from daemonize lib)
- `sleep.json` — sleep state file (created by `vox sleep`, deleted by `vox sleep off`)
- `horavox.log` — spoken words + error tracebacks

## Commands

| Command | Purpose |
|---------|---------|
| `vox clock` | Run the clock (foreground or `--background`) |
| `vox now` | Speak current time once (`--time HH:MM` to override) |
| `vox list` | List running daemon PIDs (`--verbose` shows command line) |
| `vox stop` | Stop daemon(s) — direct if one, interactive (inquirer) if multiple, `--pid N` for specific |
| `vox sleep` | Mute all daemons (`off` to resume) — auto-wakes on range restart, or use `--until`/`--for` |
| `vox wakeup` | Same as `vox sleep off` |
| `vox at` | Speak time at specified times, one-shot or recurring (`--repeat`) |
| `vox timer` | Count down to a clock time (`10:30`) or duration (`30m`); optional `--reminders 30m,1h,1h30m --name X` announce remaining time ("in one hour X" / "za godzinę X"); at target says "now X"/"teraz X" or `--message` |
| `vox voice` | Interactive voice browser (arrow keys, `i`=install, `u`=uninstall, `q`=quit) |
| `vox service add` | Add a command as an autostart service instance |
| `vox service delete` | Delete installed service instances (`--all` for all) |
| `vox service list` | List installed service instances |
| `vox service start` | Start the service (register and run) |
| `vox service restart` | Restart the service |
| `vox service status` | Show service and instance status |
| `vox service run` | Internal — manager process that supervises installed instances |

`vox-<name>` executables in `$PATH` work as `vox <name>` (git-style plugins).

**Alias dispatch** (`main.py`): three kinds, keyed by the alias name/value. (1) Name == builtin → value is default args injected into that command (`alias.clock = "--freq 30"`). (2) Name != builtin, value starts with a command → git-style *new command* (`alias.nap = "timer 30m -m X"` → `vox nap` runs `vox timer 30m -m X`; user args appended). (3) Value starts with `!` → git-style *shell alias*: `_run_shell_alias` runs `sh -c '<body> "$@"' <name> <args>` and exits with its code (the `!f(){...};f` pattern gets args via `$@`). Builtins are never shadowed; new-command expansion is single-level and can resolve to `vox-<name>` externals. `build_parser` (argcomplete) registers new-command aliases as subparsers via `_add_alias_subparsers` so they tab-complete (inheriting the target builtin's options); option-first/empty/unparseable alias values are skipped. Completion is dynamic — build_parser reads config live each run.

## Time modes

- **classic** (default) — idiomatic ("quarter past five", "wpół do szóstej"). 12-hour names in Polish.
- **modern** — digital ("five fifteen", "siedemnasta piętnaście"). 24-hour in Polish.

Selected with `--mode classic|modern` on `vox clock` and `vox now`.

## Polling architecture (clock loop)

Every 1 second, recompute next slot from wall clock. Fire when within `[-5s, +3.5s]` of target (warm-up window). Why: avoids drift bugs from `time.sleep(big_number)` overshooting past the grace window. Resilient to laptop suspend, NTP jumps, scheduler stalls.

`prepare_speech` synthesizes WAV + plays `blank.mp3` (~2.3s) **before** target so speech starts on the dot. `play_speech` fires at exactly target. `beep_count_for_minute`: 2 beeps on the hour, 1 on the half hour.

## Key invariants

- **`NOSOUND`/`VOLUME`/`VERBOSE`** are module-level globals in `core.py`. Subcommands set them via `core.configure(...)`. **Always reference as `core.NOSOUND` etc.**, never `from horavox.core import NOSOUND` — that copies the value at import time and breaks `--debug`/`--nosound`.
- **Polish 12-hour next-hour overrides**: at 23:30 we say "wpół do dwunastej" not "wpół do północy". Implemented via optional `next_hour_midnight` / `next_hour_midnight_alt` fields in language JSON.
- **Spoken durations** (`vox timer` reminders) are separate from clock times: top-level `durations` block in each `lang/*.json` (read via `core.load_durations`, not `load_language_data` which drops top-level keys). `core.spoken_duration()` decomposes h/m/s and renders each part via `core.plural_category(lang, n)` — Polish uses one/few/many (few = n%10 in 2-4 excluding teens), English uses one/other. Number words come from `durations.numbers` (Polish forms are **feminine**, e.g. "dwie"; noun forms are tuned for the accusative "za …" template, e.g. "godzinę"). Count `1` uses the unit's `"one"` phrase directly (Polish drops the number: just "godzinę"). Reminder wording/word-order lives entirely in the `template`/`now`/`join` strings, so other languages can reorder `{name}`/`{duration}`.
- **Voice catalog URLs**: overridable via `HORAVOX_VOICES_JSON_URL` and `HORAVOX_VOICES_BASE_URL` env vars (for CI/mirrors).
- **Onnxruntime noise**: always load Piper voices via `core.load_piper_voice(path)`, never `PiperVoice.load` directly. Unless `--verbose`, it redirects the process **stderr fd (2)** to `/dev/null` during the load (`core._suppressed_native_stderr`), because onnxruntime's device-discovery warnings (`GetGpuDevices` on virtual DRM devices, e.g. evdi/DisplayLink) are written straight to fd 2 by the native layer, bypassing Python's `sys.stderr` and logger severity.
- **TEMP_WAV** is per-process (`/tmp/horavox-<pid>.wav`) — safe for concurrent instances.

## Testing

- `make test` — run pytest
- `make coverage` — pytest with coverage, writes `coverage.lcov`
- `make lint` — ruff check + format check
- E2E tests use `HOME=/tmp/horavox-test-...` to avoid touching real `~/.horavox`
- `--debug` flag (alias for `--nosound --verbose`) lets tests inspect output without audio

## Publishing

- Bump `VERSION` in `Makefile` (single source of truth)
- `make publish` — updates version in `pyproject.toml` + `cli.py` + README badge, builds, uploads to PyPI
- `make publish-test` — uploads to TestPyPI

## CI

`.github/workflows/ci.yml`: lint → test (uploads `coverage.lcov` artifact) → coveralls (only on push to `jcubic/horavox`, not PRs/forks). Concurrency group cancels older runs on same ref.
