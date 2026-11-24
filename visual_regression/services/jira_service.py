import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests
from requests.auth import HTTPBasicAuth
from visual_regression.config import Config

logger = logging.getLogger("JiraService")

class JiraService:
    """
    Atlassian Jira Cloud Integration Service for Visual Regression Testing Framework.
    
    Provides capabilities to:
    - Verify connectivity & credentials against Atlassian Cloud REST API v3
    - Automatically create Bug issues when visual divergence exceeds threshold
    - Upload difference overlay and heatmap screenshots as attachments
    - Format rich Atlassian Document Format (ADF) descriptions containing metrics & defect breakdowns
    """

    @classmethod
    def get_auth(cls) -> Optional[HTTPBasicAuth]:
        email = Config.JIRA_EMAIL
        token = Config.JIRA_API_TOKEN
        if not email or not token:
            return None
        return HTTPBasicAuth(email, token)

    @classmethod
    def is_configured(cls) -> bool:
        return bool(Config.JIRA_URL and Config.JIRA_EMAIL and Config.JIRA_API_TOKEN and Config.JIRA_PROJECT_KEY)

    @classmethod
    def test_connection(cls) -> Dict[str, Any]:
        """Validates credentials and checks if the configured Jira project is accessible."""
        if not cls.is_configured():
            return {
                "success": False,
                "error": "Jira credentials or project key not fully configured."
            }

        auth = cls.get_auth()
        url = Config.JIRA_URL.rstrip('/')
        headers = {"Accept": "application/json"}

        try:
            # 1. Verify user authentication
            user_res = requests.get(f"{url}/rest/api/3/myself", auth=auth, headers=headers, timeout=10)
            if user_res.status_code != 200:
                return {
                    "success": False,
                    "error": f"Jira authentication failed (HTTP {user_res.status_code}): {user_res.text}"
                }
            user_data = user_res.json()

            # 2. Verify project accessibility
            proj_res = requests.get(f"{url}/rest/api/3/project/{Config.JIRA_PROJECT_KEY}", auth=auth, headers=headers, timeout=10)
            if proj_res.status_code != 200:
                return {
                    "success": False,
                    "error": f"Connected as '{user_data.get('displayName')}', but project '{Config.JIRA_PROJECT_KEY}' not found or inaccessible (HTTP {proj_res.status_code})."
                }
            proj_data = proj_res.json()

            return {
                "success": True,
                "user": user_data.get("displayName"),
                "email": user_data.get("emailAddress"),
                "project_key": proj_data.get("key"),
                "project_name": proj_data.get("name"),
                "jira_url": url
            }
        except Exception as e:
            logger.error("Jira connection test failed: %s", str(e))
            return {"success": False, "error": str(e)}

    @classmethod
    def create_visual_bug(
        cls,
        test_data: Dict[str, Any],
        defects: Optional[List[Dict[str, Any]]] = None,
        diff_image_path: Optional[str] = None,
        heatmap_image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates a Bug issue in Jira Cloud v3 with detailed metrics and attaches evidence images.
        """
        if not cls.is_configured():
            return {"success": False, "error": "Jira is not configured."}

        auth = cls.get_auth()
        url = Config.JIRA_URL.rstrip('/')
        project_key = Config.JIRA_PROJECT_KEY

        app_name = test_data.get("application_name", "Web Application")
        test_url = test_data.get("test_url", "")
        test_id = test_data.get("id") or test_data.get("test_id", "N/A")
        diff_pct = test_data.get("difference_percentage", 0.0)
        threshold = test_data.get("threshold", 0.5)
        ssim = test_data.get("ssim_score", 1.0)
        viewport = test_data.get("viewport", "1366x768")
        total_pixels = test_data.get("total_pixels", 0)
        changed_pixels = test_data.get("changed_pixels", 0)
        executed_at = test_data.get("executed_at", "Just now")

        summary = f"[Visual Regression] Divergence Detected in {app_name} ({diff_pct}% diff > {threshold}% threshold)"

        # Build Atlassian Document Format (ADF) description
        content_blocks = [
            {
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": "Visual Regression Defect Report"}]
            },
            {
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": "Automated visual testing detected that the target screen has diverged from the approved baseline beyond the acceptable quality tolerance threshold.", "marks": [{"type": "strong"}]}
                ]
            },
            {
                "type": "heading",
                "attrs": {"level": 3},
                "content": [{"type": "text", "text": "Execution & Metrics Summary"}]
            },
            {
                "type": "bulletList",
                "content": [
                    {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": f"Test Execution ID: #{test_id}"}]}]},
                    {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": f"Application: {app_name}"}]}]},
                    {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": f"Tested URL: {test_url}"}]}]},
                    {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": f"Viewport Resolution: {viewport}"}]}]},
                    {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": f"Measured Difference: {diff_pct}% (Allowed Threshold: {threshold}%)", "marks": [{"type": "em"}]}]}]},
                    {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": f"SSIM Structural Index: {ssim}"}]}]},
                    {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": f"Changed Pixels: {changed_pixels:,} of {total_pixels:,}"}]}]},
                    {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": f"Executed At: {executed_at}"}]}]}
                ]
            }
        ]

        # Add detected defects section
        if defects and len(defects) > 0:
            content_blocks.append({
                "type": "heading",
                "attrs": {"level": 3},
                "content": [{"type": "text", "text": f"Detected Defect Regions ({len(defects)})"}]
            })
            defect_items = []
            for d in defects[:10]:  # limit to top 10 in description to keep ticket readable
                d_type = d.get("defect_type", "visual_difference")
                d_desc = d.get("description", "Pixel variance")
                d_sev = d.get("severity", "MEDIUM")
                d_x = d.get("x", 0)
                d_y = d.get("y", 0)
                d_w = d.get("width", 0)
                d_h = d.get("height", 0)
                defect_items.append({
                    "type": "listItem",
                    "content": [{
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": f"[{d_sev}] {d_desc} - at (X: {d_x}, Y: {d_y}), dimensions: {d_w}x{d_h} px"}
                        ]
                    }]
                })
            content_blocks.append({"type": "bulletList", "content": defect_items})

        # Add Next Steps / Action Items
        content_blocks.append({
            "type": "heading",
            "attrs": {"level": 3},
            "content": [{"type": "text", "text": "Recommended Action"}]
        })
        content_blocks.append({
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "1. Review the attached visual difference overlay and intensity heatmap.\n2. Verify whether layout changes are intended modifications or regressions.\n3. If intended, navigate to the Visual Regression Dashboard to accept and update the approved baseline."}
            ]
        })

        issue_payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary[:250],
                "issuetype": {"name": "Bug"},
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": content_blocks
                },
                "labels": ["visual-regression", "automated-test", "qa-automation"]
            }
        }

        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        try:
            resp = requests.post(f"{url}/rest/api/3/issue", auth=auth, headers=headers, json=issue_payload, timeout=15)
            if resp.status_code not in (200, 201):
                logger.error("Failed to create Jira issue: %d - %s", resp.status_code, resp.text)
                return {
                    "success": False,
                    "error": f"Jira issue creation failed (HTTP {resp.status_code}): {resp.text}"
                }

            issue_data = resp.json()
            issue_key = issue_data.get("key")
            issue_id = issue_data.get("id")
            issue_url = f"{url}/browse/{issue_key}"
            logger.info("Successfully created Jira issue %s: %s", issue_key, issue_url)

            # Upload evidence attachments
            uploaded_attachments = []
            files_to_attach = []
            if diff_image_path and os.path.exists(diff_image_path):
                files_to_attach.append(diff_image_path)
            if heatmap_image_path and os.path.exists(heatmap_image_path):
                files_to_attach.append(heatmap_image_path)

            for file_path in files_to_attach:
                att_res = cls.upload_attachment(issue_key, file_path)
                if att_res.get("success"):
                    uploaded_attachments.append(att_res.get("filename"))

            return {
                "success": True,
                "issue_key": issue_key,
                "issue_id": issue_id,
                "issue_url": issue_url,
                "attachments": uploaded_attachments
            }
        except Exception as e:
            logger.error("Exception during Jira issue creation: %s", str(e))
            return {"success": False, "error": str(e)}

    @classmethod
    def upload_attachment(cls, issue_key: str, file_path: str) -> Dict[str, Any]:
        """Uploads a file to a Jira issue via multipart/form-data."""
        auth = cls.get_auth()
        url = Config.JIRA_URL.rstrip('/')
        filename = os.path.basename(file_path)

        headers = {"X-Atlassian-Token": "no-check"}
        try:
            with open(file_path, "rb") as f:
                files = {"file": (filename, f, "image/png")}
                res = requests.post(
                    f"{url}/rest/api/3/issue/{issue_key}/attachments",
                    auth=auth,
                    headers=headers,
                    files=files,
                    timeout=30
                )
            if res.status_code in (200, 201):
                return {"success": True, "filename": filename}
            else:
                logger.warning("Failed to upload attachment %s to %s: HTTP %d", filename, issue_key, res.status_code)
                return {"success": False, "error": res.text, "status_code": res.status_code}
        except Exception as e:
            logger.error("Exception uploading attachment %s: %s", filename, str(e))
            return {"success": False, "error": str(e)}
