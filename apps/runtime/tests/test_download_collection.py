import unittest
from unittest.mock import Mock
from actions import _matching_download, ActionExecutionError


class DownloadCollectionTests(unittest.TestCase):
    def test_first_matching_row_wins_over_other_names_and_older_matches(self):
        rows = []
        for name in ["Outro_1.xlsx", "Relatorio_2026.xlsx", "Relatorio_2025.xlsx"]:
            row = Mock()
            row.is_visible.return_value = True
            row.locator.return_value.inner_text.return_value = name
            rows.append(row)
        scope = Mock()
        scope.locator.return_value.count.return_value = len(rows)
        scope.locator.return_value.nth.side_effect = rows.__getitem__
        result = _matching_download(scope, {"rows": "tr", "name": ".name", "button": "a"}, "Relatorio_*.xlsx")
        self.assertIs(result, rows[1].locator.return_value)
        rows[2].is_visible.assert_not_called()

    def test_no_match_does_not_return_an_unrelated_file(self):
        scope = Mock()
        scope.locator.return_value.count.return_value = 0
        self.assertIsNone(_matching_download(scope, {"rows": "tr", "name": ".name", "button": "a"}, "Relatorio_*.xlsx"))
