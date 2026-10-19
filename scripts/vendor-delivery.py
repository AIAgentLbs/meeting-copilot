"""Build-only vendoring of hash-locked, platform-independent delivery packages."""
import argparse
from pathlib import Path
import subprocess
import sys


def vendor(target):
    target = Path(target)
    if target.exists():
        raise ValueError("Use a fresh delivery dependency staging directory")
    subprocess.run(["uv", "pip", "install", "--python", sys.executable,
                    "--target", str(target), "--require-hashes", "--no-deps",
                    "--no-binary", "charset-normalizer",
                    "-r", str(Path(__file__).with_name("delivery-requirements.txt"))], check=True)
    if any(p.suffix.lower() in {".so", ".dylib", ".dll", ".pyd"} for p in target.rglob("*")):
        raise ValueError("Delivery dependencies must be platform-independent")
    subprocess.run([sys.executable, "-I", "-c",
                    "import sys; sys.path.insert(0, sys.argv[1]); import telethon; "
                    "assert telethon.__version__ == '1.43.0'; from google_auth_oauthlib.flow import Flow; "
                    "from google.oauth2.credentials import Credentials", str(target.resolve())], check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target", type=Path)
    vendor(parser.parse_args().target)
