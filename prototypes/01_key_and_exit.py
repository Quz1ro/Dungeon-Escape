"""Прототип 1: рух, стіни, ключ і замкнений вихід."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dungeon_escape.app import main

if __name__ == "__main__":
    raise SystemExit(main("01"))
