"""Local operator deployment of the icon/UI fix, never a product auto-updater.

Requires an idle recorder and a prebuilt, verified app. Preserves the old bundle
outside Applications for rollback; never changes configuration or recordings.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
APP = Path('/Applications/Meeting Copilot Capture.app')
FILES = ('index.html', 'updates.js')


def state():
    with urlopen('http://127.0.0.1:43121/api/state', timeout=8) as response:
        return json.load(response)


def require_idle():
    data = state()
    if (data.get('transcript', {}).get('status') not in ('idle', 'finished') or
            data.get('recording_health', {}).get('capture', {}).get('audio_recording') is not False):
        raise RuntimeError('Recorder active or state unknown; deployment refused')
    with urlopen('http://127.0.0.1:43121/api/delivery/job', timeout=5) as response:
        if json.load(response).get('job', {}).get('state') not in ('idle', 'complete', 'failed'):
            raise RuntimeError('Delivery busy; deployment refused')


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', type=Path, required=True)
    args = parser.parse_args()
    candidate = args.app.resolve()
    run('codesign', '--verify', '--strict', str(candidate))
    assert (candidate / 'Contents/Resources/MeetOnTrack.icns').is_file()
    require_idle()
    share = Path.home() / '.local/share/meeting-copilot'
    web = share / 'web'
    backup = share / 'backups' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-brand-refresh')
    backup.mkdir(mode=0o700)
    stage = backup / 'new.app'
    shutil.copytree(candidate, stage, symlinks=True)
    run('codesign', '--verify', '--strict', str(stage))
    for name in FILES:
        shutil.copy2(web / name, backup / name)
    config = Path.home() / '.config/meeting-copilot/config.json'
    digest = hashlib.sha256(config.read_bytes()).hexdigest()
    require_idle()
    # SIGTERM targets only this installed executable; native shutdown finalizes
    # safely. Do not kill unrelated apps or reset any privacy permissions.
    process = subprocess.run(['pgrep', '-f', '^' + str(APP) + '/Contents/MacOS/MeetingCopilotCapture$'],
                             capture_output=True, text=True)
    pids = [int(pid) for pid in process.stdout.split()]
    for pid in pids:
        os.kill(pid, 15)
    for attempt in range(30):
        alive = []
        for pid in pids:
            try:
                os.kill(pid, 0)
                alive.append(pid)
            except ProcessLookupError:
                pass
        if not alive:
            break
        time.sleep(1)
    else:
        raise RuntimeError('Capture did not exit; bundle unchanged')
    previous = backup / 'previous.app'
    os.rename(APP, previous)
    try:
        shutil.copytree(stage, APP, symlinks=True)
        run('codesign', '--verify', '--strict', str(APP))
        for name in FILES:
            target = web / name
            shutil.copy2(ROOT / 'copilot/web' / name, target.with_suffix(target.suffix + '.new'))
            os.replace(target.with_suffix(target.suffix + '.new'), target)
        run('/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister', '-f', str(APP))
        run('open', str(APP))
        time.sleep(4)
        run('pgrep', '-f', '^' + str(APP) + '/Contents/MacOS/MeetingCopilotCapture$')
        assert hashlib.sha256(config.read_bytes()).hexdigest() == digest, 'Configuration changed unexpectedly'
        for name in FILES:
            assert (web / name).read_bytes() == (ROOT / 'copilot/web' / name).read_bytes()
        state()
    except Exception:
        # Keep the rejected bundle recoverable, and restore the old installation.
        subprocess.run(['pkill', '-TERM', '-f', '^' + str(APP) + '/Contents/MacOS/MeetingCopilotCapture$'])
        time.sleep(2)
        if APP.exists():
            os.rename(APP, backup / 'failed.app')
        os.rename(previous, APP)
        for name in FILES:
            shutil.copy2(backup / name, web / name)
        run('open', str(APP))
        raise
    print(json.dumps({'app_running': True, 'web_healthy': True, 'config_unchanged': True,
                      'backup': str(backup), 'automatic_installer': False}))


if __name__ == '__main__':
    main()
