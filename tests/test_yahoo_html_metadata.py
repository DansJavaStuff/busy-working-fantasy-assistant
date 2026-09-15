from unittest import TestCase

from tools.yahoo_html_metadata import (
    inspect_html,
    snapshot_name_from_label,
)


class YahooHtmlMetadataTests(TestCase):
    def test_week_projection_label(self):
        self.assertEqual(
            snapshot_name_from_label(
                "Week 2 (proj)"
            ),
            "week_2_projection",
        )

    def test_plain_week_label_is_actual(self):
        self.assertEqual(
            snapshot_name_from_label(
                "Week 7"
            ),
            "week_7_actual",
        )

    def test_next_four_weeks_projection_label(self):
        self.assertEqual(
            snapshot_name_from_label(
                "Next 4 Weeks (proj)"
            ),
            "next_4_weeks_projection",
        )

    def test_unknown_label_is_not_guessed(self):
        self.assertIsNone(
            snapshot_name_from_label(
                "Season Total"
            )
        )

    def test_saved_page_metadata_is_extracted(self):
        html = """
        <html>
          <head>
            <link rel="canonical"
                  href="https://football.fantasysports.yahoo.com/f1/688636/players?stat1=S_PW_3&amp;fteam=2&amp;myteam=1">
          </head>
          <body>
            <select>
              <option value="S_PW_2">Week 2 (proj)</option>
              <option value="S_PW_3" selected>Week 3 (proj)</option>
            </select>
          </body>
        </html>
        """

        result = inspect_html(html)

        self.assertEqual(
            result["snapshot_name"],
            "week_3_projection",
        )
        self.assertEqual(
            result["classification_source"],
            "selected_option",
        )
        self.assertEqual(
            result["selected_value"],
            "S_PW_3",
        )
        self.assertEqual(
            result["stat1"],
            "S_PW_3",
        )
        self.assertEqual(
            result["fteam"],
            "2",
        )
        self.assertEqual(
            result["myteam"],
            "1",
        )

    def test_missing_selected_option_is_reported_unknown(self):
        html = """
        <html>
          <head>
            <link rel="canonical"
                  href="https://football.fantasysports.yahoo.com/f1/688636/players?stat1=S_PW_4">
          </head>
          <body>
            <select>
              <option value="S_PW_4">Week 4 (proj)</option>
            </select>
          </body>
        </html>
        """

        result = inspect_html(html)

        self.assertIsNone(
            result["snapshot_name"]
        )
        self.assertEqual(
            result["stat1"],
            "S_PW_4",
        )
