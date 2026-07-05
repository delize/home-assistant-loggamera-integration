"""Tests for the Loggamera API client."""

import unittest
from unittest.mock import MagicMock, patch

from custom_components.loggamera.api import LoggameraAPI, LoggameraAPIError


class TestLoggameraAPI(unittest.TestCase):
    """Test the Loggamera API client."""

    def setUp(self):
        self.api = LoggameraAPI("test_api_key")

    def test_api_initialization(self):
        self.assertEqual(self.api.api_key, "test_api_key")
        self.assertIsNone(self.api.organization_id)

    def test_get_organizations(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"Data": {"Organizations": []}}'
        mock_response.json.return_value = {
            "Data": {"Organizations": [{"Id": 1, "Name": "Test Org", "ParentId": 0}]},
            "Error": None,
        }
        with patch.object(self.api.session, "post", return_value=mock_response) as mock_post:
            result = self.api.get_organizations()

        self.assertEqual(result["Data"]["Organizations"][0]["Name"], "Test Org")
        mock_post.assert_called_once()

    def test_api_error_handling(self):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        with patch.object(self.api.session, "post", return_value=mock_response):
            with self.assertRaises(LoggameraAPIError):
                self.api.get_organizations()


if __name__ == "__main__":
    unittest.main()
