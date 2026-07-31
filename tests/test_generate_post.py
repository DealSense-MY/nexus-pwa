import io
import pathlib
import sys
import unittest
from unittest.mock import patch
import urllib.error

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import generate_post  # noqa: E402


VALID_POST = """BAHAGIAN 1\nBAHAGIAN 2\nBAHAGIAN 3\n
Employer: Contoh Sdn Bhd
Job title: Accounts Executive
Location: Ipoh, Perak
Direct vacancy URL: https://my.jobstreet.com/job/accounts-executive-123456
Checked date: 2026-08-01
""" + ("x" * 250)


class GeneratePostSafetyTests(unittest.TestCase):
    def test_401_is_fail_fast_without_retry(self):
        error = urllib.error.HTTPError("https://api.anthropic.com", 401, "Unauthorized", None, io.BytesIO(b"invalid"))
        with patch.object(generate_post, "call_claude", side_effect=error) as call, patch.object(generate_post.time, "sleep") as sleep:
            with self.assertRaises(generate_post.ConfigurationError):
                generate_post.call_claude_with_retry("test")
        self.assertEqual(call.call_count, 1)
        sleep.assert_not_called()

    def test_complete_direct_vacancy_evidence_passes(self):
        result = generate_post.validate_vacancy_evidence(VALID_POST)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["vacancies"][0]["employer"], "Contoh Sdn Bhd")

    def test_generic_or_incomplete_vacancy_is_unverified(self):
        result = generate_post.validate_vacancy_evidence("""BAHAGIAN 3
Employer: UNVERIFIED
Job title: Clerk
Location: Ipoh
Direct vacancy URL: https://my.jobstreet.com/jobs/in-Ipoh-Perak
Checked date: today
""")
        self.assertEqual(result["status"], "UNVERIFIED")
        self.assertIn("direct_vacancy_url is not a trusted direct listing", result["vacancies"][0]["reasons"])

    def test_workflow_gate_skips_api_steps_when_flag_is_not_true(self):
        workflow = (ROOT / ".github/workflows/generate-post.yml").read_text(encoding="utf-8")
        self.assertIn('PERAK_DAILY_POST_ENABLED: ${{ secrets.PERAK_DAILY_POST_ENABLED }}', workflow)
        self.assertEqual(workflow.count("if: ${{ env.PERAK_DAILY_POST_ENABLED == 'true' }}"), 3)


if __name__ == "__main__":
    unittest.main()
