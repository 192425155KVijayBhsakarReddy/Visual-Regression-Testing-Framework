import unittest
from unittest.mock import patch, MagicMock
from visual_regression.config import Config
from visual_regression.services.jira_service import JiraService

class TestJiraIntegration(unittest.TestCase):
    def test_jira_configured(self):
        self.assertTrue(JiraService.is_configured())
        self.assertEqual(Config.JIRA_PROJECT_KEY, "VRF")
        self.assertEqual(Config.JIRA_EMAIL, "192425155.simats@saveetha.com")

    @patch("requests.get")
    def test_connection_success(self, mock_get):
        # Mock myself
        mock_user = MagicMock()
        mock_user.status_code = 200
        mock_user.json.return_value = {
            "displayName": "KANDUKURI VIJAY BHASKAR REDDY",
            "emailAddress": "192425155.simats@saveetha.com"
        }

        # Mock project
        mock_proj = MagicMock()
        mock_proj.status_code = 200
        mock_proj.json.return_value = {
            "key": "VRF",
            "name": "Visual Regression Testing Framework"
        }

        mock_get.side_effect = [mock_user, mock_proj]

        res = JiraService.test_connection()
        self.assertTrue(res["success"])
        self.assertEqual(res["project_key"], "VRF")
        self.assertEqual(res["user"], "KANDUKURI VIJAY BHASKAR REDDY")

    @patch("requests.post")
    def test_create_visual_bug_mock(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {
            "id": "10249",
            "key": "VRF-40",
            "self": "https://07vijay.atlassian.net/rest/api/3/issue/10249"
        }
        mock_post.return_value = mock_resp

        test_data = {
            "id": 99,
            "application_name": "Test Application",
            "test_url": "http://localhost:5001/",
            "difference_percentage": 2.45,
            "threshold": 0.5,
            "ssim_score": 0.965,
            "viewport": "1366x768",
            "total_pixels": 1049088,
            "changed_pixels": 25700
        }
        defects = [
            {
                "defect_type": "visual_difference",
                "description": "Shifted navigation button",
                "x": 100,
                "y": 200,
                "width": 150,
                "height": 45,
                "severity": "HIGH"
            }
        ]

        res = JiraService.create_visual_bug(test_data=test_data, defects=defects)
        self.assertTrue(res["success"])
        self.assertEqual(res["issue_key"], "VRF-40")
        self.assertEqual(res["issue_url"], "https://07vijay.atlassian.net/browse/VRF-40")

if __name__ == "__main__":
    unittest.main()
