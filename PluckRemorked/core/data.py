import json
import os
import ssl
import time
import urllib.request

DATA_URL = "https://raw.githubusercontent.com/skzysz/Pluck/refs/heads/main/data.json"
DATA_CACHE = "data_cache.json"
UPDATE_INTERVAL = 900

_MEM = {"rules": [], "laws": []}
_LAST_UPDATE = 0
_LAST_KEY = None


def _root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _cache_path():
    return os.path.join(_root(), DATA_CACHE)


def _fetch_web(timeout=10):
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(DATA_URL, headers={"User-Agent": "PluckReMorked/1.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            try:
                with open(_cache_path(), "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            print("Data: loaded from cloud")
            return data
    except Exception as e:
        print(f"Data: cloud failed ({e})")
        return None


def _fetch_cache():
    path = _cache_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            print("Data: loaded from cache")
            return data
    except Exception:
        return None


def _fetch_file(path):
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"Data: loaded from {path}")
            return data
    except Exception as e:
        print(f"Data: file error ({e})")
        return None


def load_data(force_refresh=False, custom_path=""):
    global _MEM, _LAST_UPDATE, _LAST_KEY
    key = f"file:{custom_path}" if custom_path else "cloud"
    now = time.time()
    need = force_refresh or (now - _LAST_UPDATE > UPDATE_INTERVAL) or (_LAST_KEY != key)
    if not need and _MEM.get("rules"):
        return _MEM
    if custom_path:
        data = _fetch_file(custom_path) or _fetch_web() or _fetch_cache()
    else:
        data = _fetch_web() or _fetch_cache()
    if data is not None:
        _MEM = data
        _LAST_UPDATE = now
        _LAST_KEY = key
        return data
    return {"rules": [], "laws": []}