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

    def test_header_references_logo_for_all_roles(self):
        template = (ROOT / 'templates' / 'app.html').read_text(encoding='utf-8')
        self.assertIn('/static/bager-site-link-logo.jpg', template)
        self.assertIn('class="brand-logo small"', template)

if __name__ == '__main__':
    unittest.main()
