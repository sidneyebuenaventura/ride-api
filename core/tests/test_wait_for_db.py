from unittest.mock import patch

from django.core.management import call_command
from django.db.utils import OperationalError
from django.test import TestCase


class WaitForDbCommandTests(TestCase):
    @patch("core.management.commands.wait_for_db.time.sleep")
    @patch("core.management.commands.wait_for_db.connection.ensure_connection")
    def test_returns_immediately_when_db_is_already_up(self, mock_ensure, mock_sleep):
        call_command("wait_for_db")
        mock_ensure.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("core.management.commands.wait_for_db.time.sleep")
    @patch("core.management.commands.wait_for_db.connection.ensure_connection")
    def test_retries_until_the_db_comes_up(self, mock_ensure, mock_sleep):
        mock_ensure.side_effect = [OperationalError(), OperationalError(), None]
        call_command("wait_for_db", "--delay", "0")
        self.assertEqual(mock_ensure.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("core.management.commands.wait_for_db.time.sleep")
    @patch("core.management.commands.wait_for_db.connection.ensure_connection")
    def test_gives_up_after_max_attempts(self, mock_ensure, mock_sleep):
        mock_ensure.side_effect = OperationalError()
        with self.assertRaises(SystemExit):
            call_command("wait_for_db", "--max-attempts", "3", "--delay", "0")
        self.assertEqual(mock_ensure.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 3)
