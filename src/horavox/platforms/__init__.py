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
"""Platform detection and service registration backends."""

import sys


def get_platform():
    """Return the current platform backend module."""
    if sys.platform == "linux":
        from horavox.platforms import linux

        return linux
    elif sys.platform == "darwin":  # pragma: no cover
        from horavox.platforms import macos

        return macos
    elif sys.platform == "win32":  # pragma: no cover
        from horavox.platforms import windows

        return windows
    else:
        raise RuntimeError(f"Unsupported platform: {sys.platform}")
