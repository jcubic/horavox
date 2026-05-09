"""vox config — get/set default configuration and aliases."""

import argparse
import json
import os
import sys

from horavox.core import USER_DIR, log_error

CONFIG_PATH = os.path.join(USER_DIR, "config.json")

VALID_SETTINGS = {"lang", "voice", "mode", "volume"}


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {"settings": {}, "alias": {}, "mapping": []}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Migrate flat format to structured
    if "settings" not in data and "alias" not in data:
        data = {"settings": data, "alias": {}}
        save_config(data)
    data.setdefault("settings", {})
    data.setdefault("alias", {})
    # Migrate dict mapping to list format
    if isinstance(data.get("mapping"), dict):
        old = data["mapping"]
        data["mapping"] = [{"time": t, "message": m} for t, m in old.items()]
        save_config(data)
    data.setdefault("mapping", [])
    return data


def get_mapping():
    """Return the mapping list."""
    return load_config()["mapping"]


def save_config(data):
    os.makedirs(USER_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_aliases():
    return load_config()["alias"]


def apply_config(args):
    """Apply config defaults to parsed args. CLI flags always win."""
    settings = load_config()["settings"]
    if getattr(args, "lang", None) is None and "lang" in settings:
        args.lang = settings["lang"]
    if getattr(args, "voice", None) is None and "voice" in settings:
        args.voice = settings["voice"]
    if getattr(args, "mode", "classic") == "classic" and "mode" in settings:
        if not _was_explicit("mode"):
            args.mode = settings["mode"]
    if getattr(args, "volume", 100) == 100 and "volume" in settings:
        if not _was_explicit("volume"):
            args.volume = int(settings["volume"])


def _was_explicit(name):
    """Check if an arg was explicitly passed on the command line."""
    for arg in sys.argv:
        if arg == f"--{name}" or arg.startswith(f"--{name}="):
            return True
    return False


# ==================== dot-path helpers ====================


def _resolve_key(key):
    """Turn a user key into a list of path segments.

    Bare keys that match VALID_SETTINGS are shorthands for settings.X.
    Bare keys that don't match are rejected.
    Dotted keys are split on dots.
    """
    if "." not in key:
        if key in VALID_SETTINGS:
            return ["settings", key]
        print(f"Error: unknown key '{key}'. Valid: {', '.join(sorted(VALID_SETTINGS))}")
        print("Use dotted notation (e.g. alias.name) for other keys.")
        sys.exit(1)
    return key.split(".")


def _get_nested(data, keys):
    for key in keys:
        if not isinstance(data, dict) or key not in data:
            return None
        data = data[key]
    return data


def _set_nested(data, keys, value):
    for key in keys[:-1]:
        if key not in data or not isinstance(data[key], dict):
            data[key] = {}
        data = data[key]
    data[keys[-1]] = value


def _del_nested(data, keys):
    parents = []
    node = data
    for key in keys[:-1]:
        if not isinstance(node, dict) or key not in node:
            return False
        parents.append((node, key))
        node = node[key]
    if not isinstance(node, dict) or keys[-1] not in node:
        return False
    del node[keys[-1]]
    # Clean up empty parent dicts
    for parent, key in reversed(parents):
        if not parent[key]:
            del parent[key]
        else:
            break
    return True


def _flatten(data, prefix=""):
    """Yield (dotted_key, value) pairs for all leaf values."""
    for key in sorted(data):
        path = f"{prefix}.{key}" if prefix else key
        value = data[key]
        if isinstance(value, dict):
            yield from _flatten(value, path)
        elif isinstance(value, list):
            continue
        else:
            yield path, value


def _validate_setting(keys, value):
    """Validate if the path targets a known setting."""
    if keys[0] == "settings" and len(keys) == 2:
        name = keys[1]
        if name not in VALID_SETTINGS:
            print(f"Error: unknown setting '{name}'. Valid: {', '.join(sorted(VALID_SETTINGS))}")
            sys.exit(1)
        if name == "mode" and value not in ("classic", "modern"):
            print(f"Error: mode must be 'classic' or 'modern', got '{value}'")
            sys.exit(1)
        if name == "volume":
            try:
                v = int(value)
                if not 0 <= v <= 100:
                    raise ValueError
            except ValueError:
                print(f"Error: volume must be an integer 0-100, got '{value}'")
                sys.exit(1)
    if keys == ["settings", "mapping", "time"] and value not in ("true", "false"):
        print(f"Error: mapping.time must be 'true' or 'false', got '{value}'")
        sys.exit(1)


# ==================== CLI ====================


def setup_parser(parser):
    parser.add_argument(
        "args",
        nargs="*",
        help="key=value to set, dotted.key=value for nested, or key to get",
    )
    parser.add_argument(
        "--unset",
        type=str,
        metavar="KEY",
        help="Remove a config key (e.g. lang, alias.clock, a.b.c)",
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Get or set default configuration and aliases",
        prog="vox config",
    )
    setup_parser(parser)
    return parser.parse_args()


def main():
    try:
        _main()
    except KeyboardInterrupt:
        pass
    except Exception:
        log_error()
        raise


def _format_mapping_entry(i, entry):
    """Format a single mapping entry for display."""
    parts = [f"  {i}: {entry['time']}"]
    if "message" in entry:
        parts.append(f' "{entry["message"]}"')
    if "date" in entry:
        parts.append(f" ({', '.join(entry['date'])})")
    return "".join(parts)


def _print_mapping(mapping):
    """Print all mapping entries."""
    if not mapping:
        print("No mapping entries.")
        return
    print("Mapping:")
    for i, entry in enumerate(mapping):
        print(_format_mapping_entry(i, entry))


def _validate_date_values(values):
    """Validate date values against known day names and groups."""
    from horavox.at import DAY_GROUPS, DAY_NAMES

    for v in values:
        v = v.strip().lower()
        if v not in DAY_NAMES and v not in DAY_GROUPS:
            valid = sorted(list(DAY_NAMES.keys()) + list(DAY_GROUPS.keys()))
            print(f"Error: unknown day '{v}'. Valid: {', '.join(valid)}")
            sys.exit(1)


def _parse_mapping_args(args_list):
    """Parse mapping add arguments: TIME [MESSAGE] [--date DAY[,DAY...]]"""
    if not args_list:
        print("Error: mapping.add requires at least a time (HH:MM).")
        sys.exit(1)

    time_val = args_list[0]
    from horavox.core import parse_time_arg

    parse_time_arg(time_val)

    entry = {"time": time_val}
    rest = args_list[1:]

    date_idx = None
    for i, arg in enumerate(rest):
        if arg == "--date":
            date_idx = i
            break

    if date_idx is not None:
        msg_parts = rest[:date_idx]
        date_parts = rest[date_idx + 1 :]
        if not date_parts:
            print("Error: --date requires at least one day value.")
            sys.exit(1)
        date_values = []
        for part in date_parts:
            date_values.extend(part.split(","))
        _validate_date_values(date_values)
        entry["date"] = [v.strip().lower() for v in date_values]
    else:
        msg_parts = rest

    if msg_parts:
        entry["message"] = " ".join(msg_parts)

    return entry


def _main():
    # Intercept mapping.add before argparse (it has its own --date flag)
    if len(sys.argv) >= 2 and sys.argv[1] == "mapping.add":
        cfg = load_config()
        entry = _parse_mapping_args(sys.argv[2:])
        cfg["mapping"].append(entry)
        save_config(cfg)
        idx = len(cfg["mapping"]) - 1
        print(f"Added{_format_mapping_entry(idx, entry)}")
        return

    args = parse_args()
    cfg = load_config()

    if args.unset:
        key = args.unset
        if key.startswith("mapping."):
            suffix = key[len("mapping.") :]
            try:
                idx = int(suffix)
            except ValueError:
                keys = _resolve_key(key)
                if _del_nested(cfg, keys):
                    save_config(cfg)
                    print(f"Unset '{key}'.")
                else:
                    print(f"Key '{key}' is not set.")
                return
            mapping = cfg["mapping"]
            if 0 <= idx < len(mapping):
                removed = mapping.pop(idx)
                save_config(cfg)
                print(f"Removed mapping {idx}: {removed['time']}")
            else:
                print(f"Error: mapping index {idx} out of range (0-{len(mapping) - 1}).")
                sys.exit(1)
            return
        keys = _resolve_key(key)
        if _del_nested(cfg, keys):
            save_config(cfg)
            print(f"Unset '{key}'.")
        else:
            print(f"Key '{key}' is not set.")
        return

    if not args.args:
        entries = list(_flatten(cfg))
        mapping = cfg["mapping"]
        if not entries and not mapping:
            print("No configuration set.")
            return
        for path, value in entries:
            print(f"{path}={value}")
        if mapping:
            if entries:
                print()
            _print_mapping(mapping)
        return

    first = args.args[0]

    if first == "mapping":
        _print_mapping(cfg["mapping"])
        return

    # Two-arg form: vox config dotted.key 'value with spaces'
    if "=" not in first and len(args.args) >= 2:
        keys = _resolve_key(first)
        value = " ".join(args.args[1:])
        _validate_setting(keys, value)
        _set_nested(cfg, keys, value)
        save_config(cfg)
        print(f"{first}={value}")
        return

    # Single arg with = (set)
    if "=" in first:
        raw_key, value = first.split("=", 1)
        keys = _resolve_key(raw_key)
        _validate_setting(keys, value)
        _set_nested(cfg, keys, value)
        save_config(cfg)
        print(f"{raw_key}={value}")
        return

    # Get mode
    keys = _resolve_key(first)
    result = _get_nested(cfg, keys)
    if result is None:
        print(f"Key '{first}' is not set.")
    elif isinstance(result, dict):
        entries = list(_flatten(result, first))
        if not entries:
            print(f"Key '{first}' is empty.")
        else:
            for path, value in entries:
                print(f"{path}={value}")
    else:
        print(f"{first}={result}")


if __name__ == "__main__":
    main()
