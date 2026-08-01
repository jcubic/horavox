## 0.6.0
### Feature
* new `chime` script
### Bugfix
* fix aliases to work like in git
* fix completion of new aliases

## 0.5.0
### Feature
* extend `vox timer` command
### Bugfix
* hide `onnxruntime` warnings

## 0.4.0
### Feature
* `vox timer`
### Bugfix
* clear expired sleep file
* fix tests to not require `pip install .`

## 0.3.1
### Bugfix
* fix sleep/wakeup mechanism

## 0.3.0
### Feature
* add `vox list` sub-command
* add `vox service`
* add `vox at` command
* add `vox config` command
* add `vox sleep` / `vox wakeup` to mute and resume running daemons
* add time-based messages (mapping) via `vox config mapping.add`
* add shell completion
* add update available notification message
* add `--message` option to `vox now` (and new `vox at`)
* add command validation in `vox service add` (strips `vox` prefix, rejects unknown commands)
* add `--exec` flag to `vox clock` and `vox at` for running commands after announcements
* improve `vox voice` TUI
### Bugfix
* fix cleaning old session files
* migrate legacy voice directory (`~/.horavox/voices/`) to new location (`~/.horavox/models/`)

## 0.2.0
### Feature
* add interactive stop of background jobs
* introduce git-style commands system
### Bug fix
* fix handling kill of multiple commands run in background

## 0.1.0
* initial release
