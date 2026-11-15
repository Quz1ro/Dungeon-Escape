"""Формат часу й відновлення локальних таблиць результатів."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from dungeon_escape.records import format_time, clean_scores


class RecordsTests(unittest.TestCase):
    def test_time_formats_seconds_minutes_and_hours(self):
        for seconds, expected in ((0, '00:00:00'), (9, '00:00:09'), (61, '00:01:01'),
                                  (3661.9, '01:01:01'), (86400, '24:00:00')):
            self.assertEqual(format_time(seconds), expected)

    def test_invalid_records_are_ignored_and_top_is_limited_to_ten(self):
        entries = [{'name': 'Тест', 'seconds': n, 'moves': 20} for n in range(20, 0, -1)]
        entries += [{'seconds': float('nan'), 'moves': 2}, {'seconds': -1, 'moves': 2},
                    {'seconds': 2, 'moves': -1}, {'seconds': True, 'moves': 1}, None]
        result = clean_scores({'solo': {'1': entries}, 'coop': []})
        self.assertEqual(len(result['solo']['1']), 10)
        self.assertEqual([e['seconds'] for e in result['solo']['1']], list(range(1, 11)))
        self.assertEqual(result['coop'], {})
        self.assertEqual(clean_scores([]), {'solo': {}, 'coop': {}})
