"""Release guard: the approved original brand asset must be committed."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class LogoAssetTests(unittest.TestCase):
    def test_approved_logo_exists_and_is_jpeg(self):
        asset = ROOT / 'static' / 'bager-site-link-logo.jpg'
        self.assertTrue(asset.is_file(), 'Approved logo JPEG missing: static/bager-site-link-logo.jpg')
        data = asset.read_bytes()
        self.assertGreater(len(data), 1024, 'Logo file is suspiciously small')
        self.assertTrue(data.startswith(bytes.fromhex('ffd8ff')), 'Logo is not a JPEG')
        self.assertTrue(data.endswith(bytes.fromhex('ffd9')), 'JPEG appears truncated')

    def test_branding_is_present_on_all_entry_templates(self):
        logo_url = '/static/bager-site-link-logo.jpg'
        for name in ('app.html', 'login.html', 'join.html'):
            with self.subTest(template=name):
                template = (ROOT / 'templates' / name).read_text(encoding='utf-8')
                self.assertIn(logo_url, template, f'{name} does not reference the approved logo')
                self.assertIn('alt="BAGER SITE LINK"', template, f'{name} has no accessible logo alt text')

    def test_participant_header_uses_shared_template(self):
        template = (ROOT / 'templates' / 'app.html').read_text(encoding='utf-8')
        self.assertIn('class="brand-logo small"', template)
        self.assertIn('data-role="{{ participant.role }}"', template)

if __name__ == '__main__':
    unittest.main()
