"""Compose a Windows candidate from verified CI and previously released runtimes.

Cross-platform packaging only; Windows execution/installer acceptance is separate.
Never reuse an upstream application executable, UI resources or update feed.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
DONOR_SHA256 = '74b2c0deb0374eac4df854188f5744a1f5971b60fb0cd52b3413265335f2c828'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def unpack(source, destination, select):
    with zipfile.ZipFile(source) as archive:
        for entry in archive.infolist():
            name = entry.filename.replace('\\', '/')
            path = PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or ':' in name:
                raise ValueError('Unsafe archive entry')
            if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('Windows package must not contain symlinks')
            target = select(name)
            if target is None or entry.is_dir():
                continue
            output = destination / target
            output.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as stream, output.open('wb') as handle:
                shutil.copyfileobj(stream, handle)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--donor', type=Path, required=True)
    parser.add_argument('--managed', type=Path, required=True)
    parser.add_argument('--managed-sha256', required=True)
    parser.add_argument('--capture-revision', required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert re.fullmatch(r'\d+\.\d+\.\d+', args.version)
    assert re.fullmatch(r'[0-9a-f]{40}', args.capture_revision)
    assert digest(args.donor) == DONOR_SHA256, 'Runtime donor checksum mismatch'
    assert digest(args.managed) == args.managed_sha256, 'CI artifact checksum mismatch'
    installer = args.output.with_suffix('.install.ps1')
    assert not args.output.exists() and not installer.exists(), 'Refuse to overwrite a candidate'
    revision = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    with tempfile.TemporaryDirectory(prefix='meetontrack-windows-package-') as directory:
        stage = Path(directory)
        allowed = ('python/', 'capture/local-runtime/', 'capture/live-runtime/', 'capture/Licenses/')
        unpack(args.donor, stage, lambda name: name if name.startswith(allowed) else None)
        unpack(args.managed, stage, lambda name: 'capture/' + name)
        shutil.copytree(ROOT / 'copilot/web', stage / 'web', ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.log'))
        subprocess.run([sys.executable, str(ROOT / 'scripts/vendor-delivery.py'),
                        str(stage / 'web/_vendor')], check=True)
        for name in ('meeting-copilot.ps1', 'refresh-repos.py'):
            shutil.copy2(ROOT / 'scripts/windows' / name, stage / name)
        shutil.copy2(ROOT / 'copilot/config/SESSION.md', stage / 'SESSION.md')
        shutil.copy2(ROOT / 'LICENSE', stage / 'LICENSE')
        # Preserve the exact mandatory upstream credit from the verified donor.
        unpack(args.donor, stage, lambda name: name if name == 'capture/AMANU-LICENSE' else None)
        for required in ('capture/MeetingCopilotCapture.exe', 'python/python.exe', 'python/python313._pth',
                         'capture/local-runtime/transcribe.dll', 'capture/live-runtime/transcribe.dll',
                         'capture/AMANU-LICENSE', 'web/server.py'):
            assert (stage / required).is_file(), f'Missing component: {required}'
        files = {}
        forbidden = {'repos.json', 'active-repos.json', 'config.json', 'report.json', 'meeting.json',
                     'delivery.json', 'storage.dek', 'credentials.json', 'auth.json'}
        for path in sorted(stage.rglob('*')):
            if not path.is_file():
                continue
            assert path.name not in forbidden and path.suffix not in {'.wav', '.caf', '.log', '.gguf'}
            files[path.relative_to(stage).as_posix()] = digest(path)
        manifest = {'version': args.version + '-windows-beta.1', 'architecture': 'x64',
                    'channel': 'technical-beta', 'signed': False, 'source_revision': revision,
                    'capture_revision': args.capture_revision, 'runtime_donor_sha256': DONOR_SHA256,
                    'managed_artifact_sha256': args.managed_sha256, 'sha256': files}
        (stage / 'release.json').write_text(json.dumps(manifest, indent=2) + '\n')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(args.output, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path in sorted(stage.rglob('*')):
                if path.is_file():
                    archive.write(path, path.relative_to(stage).as_posix())
    checksum = digest(args.output)
    content = (ROOT / 'scripts/windows/install.ps1').read_text()
    content, count = re.subn(r"\[string\]\$ExpectedSha256 = '[0-9a-f]+'", f"[string]$ExpectedSha256 = '{checksum}'", content, count=1)
    assert count == 1
    content = re.sub(r"(?m)^\$version='[^']+'$", f"$version='{manifest['version']}'", content)
    url = f'https://github.com/AIAgentLbs/meeting-copilot/releases/download/windows-v{args.version}/{args.output.name}'
    content = re.sub(r"(?m)^\$url='[^']+'$", f"$url='{url}'", content)
    installer.write_text(content, encoding='utf-8')
    print(json.dumps({'archive': str(args.output), 'installer': str(installer), 'sha256': checksum,
                      'source_revision': revision, 'capture_revision': args.capture_revision,
                      'files': len(files), 'windows_execution': 'not performed by packager'}, indent=2))


if __name__ == '__main__':
    main()
