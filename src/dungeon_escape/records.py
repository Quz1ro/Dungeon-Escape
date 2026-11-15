"""Локальний топ проходжень і формат часу."""
import math


def format_time(seconds):
    value = max(0, int(seconds))
    hours, rest = divmod(value, 3600)
    minutes, seconds = divmod(rest, 60)
    return f'{hours:02}:{minutes:02}:{seconds:02}'


def clean_scores(raw):
    result = {'solo': {}, 'coop': {}}
    if not isinstance(raw, dict):
        return result
    for mode in result:
        levels = raw.get(mode, {})
        if not isinstance(levels, dict):
            continue
        for number in range(1, 10):
            entries = levels.get(str(number), [])
            if not isinstance(entries, list):
                continue
            valid = []
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                seconds, moves = entry.get('seconds'), entry.get('moves')
                if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
                    continue
                if type(moves) is not int or moves < 0:
                    continue
                name = entry.get('name', 'Гравець')
                if not isinstance(name, str):
                    name = 'Гравець'
                valid.append({'name': name[:20], 'seconds': round(seconds, 3), 'moves': moves})
            if valid:
                result[mode][str(number)] = sorted(valid, key=lambda e: (e['seconds'], e['moves']))[:10]
    return result
