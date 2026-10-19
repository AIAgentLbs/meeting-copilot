import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("deploy_delivery", Path(__file__).with_name("deploy-delivery-fix.py"))
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


class DeployTests(unittest.TestCase):
    def scenario(self, fail=False, active=False):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            source = home / "source/copilot/web"
            installed = home / ".local/share/meeting-copilot/web"
            vendor = home / "vendor"
            for path, content in [(source/"existing.py", "new"), (source/"new.py", "new module"),
                                  (installed/"existing.py", "old"), (installed/"_vendor/old.txt", "old vendor"),
                                  (vendor/"google_auth_oauthlib/flow.py", "flow"), (vendor/"telethon/__init__.py", "telethon")]:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            with patch.object(deploy, "ROOT", home/"source"), patch.object(deploy, "FILES", ("existing.py", "new.py")), \
                 patch.object(deploy.Path, "home", return_value=home), patch.object(deploy, "ready", return_value=not active), \
                 patch.object(deploy, "state", return_value={"transcript": {}}), \
                 patch("sys.argv", ["deploy", "--vendor", str(vendor)]), \
                 patch.object(deploy.subprocess, "run", side_effect=[RuntimeError("restart failed"), None] if fail else None) as run:
                if active:
                    with self.assertRaises(SystemExit): deploy.main()
                elif fail:
                    with self.assertRaisesRegex(RuntimeError, "restart failed"): deploy.main()
                else:
                    deploy.main()
            self.assertEqual((installed/"existing.py").read_text(), "old" if fail or active else "new")
            self.assertEqual((installed/"new.py").exists(), not (fail or active))
            self.assertEqual((installed/"_vendor/old.txt").exists(), fail or active)
            if active:
                run.assert_not_called()
            if fail:
                self.assertEqual(run.call_count, 2)
                self.assertEqual(len(list((installed.parent/"backups").glob("*/failed-new-new.py"))), 1)

    def test_success(self): self.scenario()
    def test_rollback_restores_existing_and_recovers_new_files(self): self.scenario(fail=True)
    def test_active_capture_blocks_changes(self): self.scenario(active=True)


if __name__ == "__main__": unittest.main()
