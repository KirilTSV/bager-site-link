"""Static contract for the five participant views; not a substitute for browser tests."""
from pathlib import Path
import re
import unittest

TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "app.html"

class ParticipantTemplateContractTests(unittest.TestCase):
    def test_five_role_views_are_present_exactly_once(self):
        html = TEMPLATE.read_text(encoding="utf-8")
        expected = ("dispatcherView", "driverView", "operatorView", "managerView", "clientView")
        for view in expected:
            with self.subTest(view=view):
                self.assertEqual(len(re.findall(r'id="' + view + r'"', html)), 1)
                self.assertRegex(html, r'<section\b[^>]*\bid="' + view + r'"')

    def test_role_views_share_accessible_branded_header(self):
        html = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn('data-role="{{ participant.role }}"', html)
        self.assertIn('class="brand-logo small"', html)
        self.assertIn('alt="BAGER SITE LINK"', html)

if __name__ == "__main__":
    unittest.main()
