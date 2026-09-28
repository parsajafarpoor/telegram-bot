"""جلوگیری از ارسال چندباره یادآوری برای یک نفر در یک سال."""
import json
import os

STORE_PATH = os.path.join(os.path.dirname(__file__), "notified.json")


def _key(person, year: int) -> str:
    return f"{year}:{person['name']}:{person['month']}:{person['day']}"


def _load() -> set:
    if not os.path.exists(STORE_PATH):
        return set()
    with open(STORE_PATH, "r", encoding="utf-8") as f:
        return set(json.load(f))


def _save(keys: set):
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(keys), f, ensure_ascii=False, indent=2)


def already_notified(person, year: int) -> bool:
    return _key(person, year) in _load()


def mark_notified(person, year: int):
    keys = _load()
    keys.add(_key(person, year))
    _save(keys)
