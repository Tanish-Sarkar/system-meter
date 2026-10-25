import unittest

from speakup.formatting import format_bytes, format_percentage, format_uptime


class FormattingTests(unittest.TestCase):
    def test_format_bytes_uses_binary_units(self):
        cases = (
            (0, "0 B"),
            (1023, "1023 B"),
            (1024, "1.0 KiB"),
            (1024**2, "1.0 MiB"),
            (1024**3, "1.0 GiB"),
            (int(1.5 * 1024**4), "1.5 TiB"),
        )

        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(format_bytes(value), expected)

    def test_format_bytes_rejects_negative_values(self):
        with self.assertRaises(ValueError):
            format_bytes(-1)

    def test_format_percentage_formats_boundaries_and_unknown_values(self):
        self.assertEqual(format_percentage(0), "0.0%")
        self.assertEqual(format_percentage(45.678), "45.7%")
        self.assertEqual(format_percentage(100), "100.0%")
        self.assertEqual(format_percentage(None), "not available")

    def test_format_percentage_rejects_out_of_range_values(self):
        for value in (-0.1, 100.1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                format_percentage(value)

    def test_format_uptime_formats_minutes_hours_and_days(self):
        cases = (
            (0, "0m"),
            (59, "0m"),
            (60, "1m"),
            (3600, "1h 0m"),
            (86_400, "1d 0h 0m"),
            (183_845, "2d 3h 4m"),
        )

        for seconds, expected in cases:
            with self.subTest(seconds=seconds):
                self.assertEqual(format_uptime(seconds), expected)

    def test_format_uptime_rejects_negative_values(self):
        with self.assertRaises(ValueError):
            format_uptime(-1)
