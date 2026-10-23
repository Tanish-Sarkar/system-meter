import unittest
from contextlib import redirect_stdout
from io import StringIO

from speakup.main import main


class MainTests(unittest.TestCase):
    def test_main_prints_initialization_message(self):
        output = StringIO()

        with redirect_stdout(output):
            main()

        self.assertEqual(
            output.getvalue(),
            "System Meter is initialized! 'speakup' command is ready.\n",
        )
