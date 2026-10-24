"""Прототип 3: об’єднаний лабіринт із ключем, виходом і патрулем."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dungeon_escape.app import main

if __name__ == "__main__":
    raise SystemExit(main("03"))
