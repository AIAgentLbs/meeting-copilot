"""Source gates for the distributed brand; required legal credits stay intact."""
from pathlib import Path
import plistlib
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReleaseBrandingTests(unittest.TestCase):
    def test_native_display_identity_and_permission_prompts(self):
        info = plistlib.loads((ROOT / 'capture/Packaging/MeetingCopilot-Info.plist').read_bytes())
        for key in ('CFBundleName', 'CFBundleDisplayName'):
            self.assertEqual(info[key], 'MeetOnTrack')
        for key in ('NSMicrophoneUsageDescription', 'NSAudioCaptureUsageDescription'):
            self.assertIn('MeetOnTrack', info[key])
        self.assertFalse(info['SUEnableAutomaticChecks'])
        self.assertNotIn('SUFeedURL', info, 'Never inherit an upstream update feed')

    def test_native_and_web_ui_have_no_upstream_product_name(self):
        files = list((ROOT / 'capture/Sources/meetingcopilot/UI').glob('*.swift'))
        files += [ROOT / 'copilot/web' / name for name in
                  ('index.html', 'app.js', 'getting-started.js')]
        forbidden = re.compile(r'\b(?:amanu|amana|аману|амана)\b', re.I)
        for path in files:
            with self.subTest(file=str(path.relative_to(ROOT))):
                self.assertIsNone(forbidden.search(path.read_text()))
        self.assertFalse((ROOT / 'capture/Sources/meetingcopilot/UI/FeatherIcon.swift').exists())

    def test_attribution_and_generated_icon(self):
        html = (ROOT / 'copilot/web/index.html').read_text()
        self.assertIn('https://aiagentlbs.com/', html)
        assembly = (ROOT / 'scripts/assemble-arm64-app.sh').read_text()
        self.assertIn('make -C "$CAPTURE" icon', assembly)
        self.assertTrue((ROOT / 'capture/THIRD-PARTY-NOTICES.md').is_file())


if __name__ == '__main__':
    unittest.main()
