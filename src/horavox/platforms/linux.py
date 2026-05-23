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
"""Linux platform backend — systemd user service."""

import os
import shutil
import subprocess

UNIT_DIR = os.path.expanduser("~/.config/systemd/user")
UNIT_NAME = "horavox.service"
UNIT_PATH = os.path.join(UNIT_DIR, UNIT_NAME)


def _vox_path():
    path = shutil.which("vox")
    if path:
        return path
    return "vox"


def _unit_content():
    return f"""\
[Unit]
Description=HoraVox service manager

[Service]
ExecStart={_vox_path()} service run
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
"""


def is_registered():
    return os.path.exists(UNIT_PATH)


def register():
    os.makedirs(UNIT_DIR, exist_ok=True)
    with open(UNIT_PATH, "w", encoding="utf-8") as f:
        f.write(_unit_content())
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", UNIT_NAME], check=True)


def start():
    subprocess.run(["systemctl", "--user", "start", UNIT_NAME], check=True)


def stop():
    subprocess.run(["systemctl", "--user", "stop", UNIT_NAME], capture_output=True)


def reload():
    subprocess.run(["systemctl", "--user", "kill", "-s", "SIGHUP", UNIT_NAME], capture_output=True)


def unregister():
    stop()
    subprocess.run(["systemctl", "--user", "disable", UNIT_NAME], capture_output=True)
    if os.path.exists(UNIT_PATH):
        os.remove(UNIT_PATH)
    subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)


def is_running():
    result = subprocess.run(
        ["systemctl", "--user", "is-active", UNIT_NAME],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() == "active"
