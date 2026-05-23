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
"""Instance registry — CRUD for ~/.horavox/data.json."""

import json
import os
import uuid

from horavox.core import USER_DIR

REGISTRY_PATH = os.path.join(USER_DIR, "data.json")


def _load():
    if not os.path.exists(REGISTRY_PATH):
        return {"instances": []}
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data):
    os.makedirs(USER_DIR, exist_ok=True)
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def list_instances():
    return _load()["instances"]


def add_instance(command):
    data = _load()
    instance_id = uuid.uuid4().hex[:6]
    from datetime import datetime, timezone

    entry = {
        "id": instance_id,
        "command": command,
        "installed_at": datetime.now(timezone.utc).isoformat(),
    }
    data["instances"].append(entry)
    _save(data)
    return entry


def remove_instance(instance_id):
    data = _load()
    before = len(data["instances"])
    data["instances"] = [i for i in data["instances"] if i["id"] != instance_id]
    if len(data["instances"]) == before:
        return False
    _save(data)
    return True


def remove_all():
    data = _load()
    count = len(data["instances"])
    data["instances"] = []
    _save(data)
    return count


def get_instance(instance_id):
    for inst in list_instances():
        if inst["id"] == instance_id:
            return inst
    return None
