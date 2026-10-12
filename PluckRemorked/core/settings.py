import json
import os

APP_NAME = "PluckReMorked"
SETTINGS_FILE = "settings.json"


def _root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_settings_path():
    return os.path.join(_root(), SETTINGS_FILE)


def load_settings():
    defaults = {
        "always_on_top": True,
        "ball_x": 800,
        "ball_y": 400,
        "custom_data_path": "",
    }
    path = get_settings_path()
    if not os.path.exists(path):
        return defaults
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for k, v in defaults.items():
                data.setdefault(k, v)
            return data
    except Exception:
        return defaults


def save_settings(s):
    try:
        with open(get_settings_path(), "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Settings save error: {e}")