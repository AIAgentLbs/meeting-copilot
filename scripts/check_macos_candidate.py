"""Verify exact release bytes and install twice into disposable user directories.

No Capture process or LaunchAgent is started. This does not claim hardware or
Gatekeeper acceptance. The only subprocess fakes are platform/process probes,
download transport (already verified archive), and launch guards.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import subprocess
import zipfile

from test_installer import InstallerTests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    archive_path = args.archive.resolve(strict=True)
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    with zipfile.ZipFile(archive_path) as archive:
        manifest = json.loads(archive.read('release.json'))
        names = {entry.filename for entry in archive.infolist() if not entry.is_dir()}
        assert names == set(manifest['sha256']) | {'release.json'}, 'Unmanifested files'
        for name, expected in manifest['sha256'].items():
            assert not Path(name).is_absolute() and '..' not in Path(name).parts
            data = archive.read(name)
            # zip -y stores symlink targets, also hashed in the manifest.
            mode = archive.getinfo(name).external_attr >> 16
            if mode & 0o170000 == 0o120000:
                target = data.decode()
                assert not os.path.isabs(target) and '..' not in Path(target).parts
            assert hashlib.sha256(data).hexdigest() == expected, f'Checksum mismatch: {name}'
        info = plistlib.loads(archive.read('Meeting Copilot Capture.app/Contents/Info.plist'))
        assert info['CFBundleDisplayName'] == 'MeetOnTrack'
        assert info['CFBundleShortVersionString'] == manifest['version']

    fixture = InstallerTests()
    fixture.setUp()
    try:
        fixture.env['FIXTURE_PACKAGE'] = str(archive_path)
        fixture.env['MEETING_COPILOT_ASSET_SHA256'] = digest
        result = fixture.run_install()
        assert result.returncode == 0, result.stderr + result.stdout
        share = Path(fixture.env['MEETING_COPILOT_SHARE_ROOT'])
        config = Path(fixture.env['MEETING_COPILOT_CONFIG_ROOT'])
        app = Path(fixture.env['MEETING_COPILOT_APP_ROOT']) / 'Meeting Copilot Capture.app'
        assert json.loads((config / 'active-repos.json').read_text())['repositories'] == []
        subprocess.run(['codesign', '--verify', '--strict', str(app)], check=True)
        for helper in ('zoom-window-finder', 'zoom-frame-inspector', 'detect-speech-language'):
            subprocess.run(['codesign', '--verify', '--strict', str(share / 'bin' / helper)], check=True)
        recording = share / 'recordings' / 'synthetic-keep.txt'
        recording.parent.mkdir()
        recording.write_text('synthetic recording preservation check')
        settings = config / 'delivery.json'
        settings.write_text('{"synthetic_preserve":true}')
        result = fixture.run_install()
        assert result.returncode == 0, result.stderr + result.stdout
        assert recording.read_text() == 'synthetic recording preservation check'
        assert json.loads(settings.read_text()) == {'synthetic_preserve': True}
        assert not (fixture.root / 'unexpected-launch').exists()
        assert not (fixture.root / 'compiled').exists()
        print(json.dumps({'version': manifest['version'], 'source_revision': manifest['source_revision'],
                          'sha256': digest, 'manifest_files': len(manifest['sha256']),
                          'fresh_install': 'passed', 'reinstall_preserves_data': 'passed',
                          'signatures': 'ad-hoc valid', 'hardware_test': 'not performed'}, indent=2))
    finally:
        fixture.doCleanups()


if __name__ == '__main__':
    main()
