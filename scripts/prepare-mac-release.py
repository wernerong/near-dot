"""Build and verify Mac distribution using protected CI signing secrets only."""
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile

target = sys.argv[1] if len(sys.argv) == 2 else ""
targets = {"aarch64-apple-darwin": ("arm64", "darwin-aarch64"), "x86_64-apple-darwin": ("x86_64", "darwin-x86_64")}
if target not in targets or sys.platform != "darwin":
    raise SystemExit("Choose a supported Mac target on its matching Mac runner.")
required = ["APPLE_CERTIFICATE", "APPLE_CERTIFICATE_PASSWORD", "APPLE_SIGNING_IDENTITY", "APPLE_API_ISSUER", "APPLE_API_KEY", "APPLE_API_PRIVATE_KEY", "TAURI_SIGNING_PRIVATE_KEY"]
if any(not os.environ.get(key) for key in required):
    raise SystemExit("Protected Apple signing, notarization and updater secrets are required.")
if not os.environ["APPLE_SIGNING_IDENTITY"].startswith("Developer ID Application:"):
    raise SystemExit("Public Mac distribution requires a Developer ID Application identity.")

def verify(args, stdout_only=False):
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode:
        raise SystemExit(f"Release verification failed: {args[0]} (private diagnostics suppressed).")
    return result.stdout if stdout_only else result.stdout + result.stderr

version = json.loads(Path("package.json").read_text())["version"]
arch, platform = targets[target]
base = Path("src-tauri/target") / target / "release/bundle"
with tempfile.TemporaryDirectory(prefix="near-dot-signing-", dir=os.environ.get("RUNNER_TEMP")) as temp:
    key = Path(temp) / "notarization.p8"
    fd = os.open(key, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as file:
        file.write(os.environ["APPLE_API_PRIVATE_KEY"])
    env = {**os.environ, "APPLE_API_KEY_PATH": str(key)}
    subprocess.run(["npm", "run", "tauri", "--", "build", "--ci", "--target", target, "--bundles", "app,dmg", "--config", "release-config.json"], env=env, check=True)
    app = base / "macos/Near Dot.app"
    with (app / "Contents/Info.plist").open("rb") as file:
        info = plistlib.load(file)
    if info["CFBundleShortVersionString"] != version:
        raise SystemExit("Mac bundle version does not match the reviewed release.")
    binary = app / "Contents/MacOS" / info["CFBundleExecutable"]
    if verify(["lipo", "-archs", str(binary)]).strip() != arch:
        raise SystemExit("Mac executable architecture does not match its artifact.")
    verify(["codesign", "--verify", "--deep", "--strict", str(app)])
    signature = verify(["codesign", "--display", "--verbose=4", str(app)])
    if "Authority=Developer ID Application:" not in signature or "(runtime)" not in signature:
        raise SystemExit("Mac app needs Developer ID signing and hardened runtime.")
    verify(["xcrun", "stapler", "validate", str(app)])
    verify(["spctl", "--assess", "--type", "execute", str(app)])
    dmgs = list((base / "dmg").glob("*.dmg"))
    if len(dmgs) != 1:
        raise SystemExit("Expected exactly one Mac installer.")
    dmg = dmgs[0]
    # Tauri signed the DMG before cleaning up its temporary CI keychain.
    verify(["codesign", "--verify", "--strict", str(dmg)])
    if "Authority=Developer ID Application:" not in verify(["codesign", "--display", "--verbose=4", str(dmg)]):
        raise SystemExit("Mac installer needs Developer ID signing.")
    submitted = json.loads(verify(["xcrun", "notarytool", "submit", str(dmg), "--key", str(key), "--key-id", os.environ["APPLE_API_KEY"], "--issuer", os.environ["APPLE_API_ISSUER"], "--wait", "--output-format", "json"], stdout_only=True))
    if submitted.get("status") != "Accepted":
        raise SystemExit("Mac installer notarization was not accepted; release blocked.")
    verify(["xcrun", "stapler", "staple", str(dmg)])
    verify(["xcrun", "stapler", "validate", str(dmg)])
    verify(["codesign", "--verify", "--strict", str(dmg)])
    artifacts = Path("release-artifacts")
    artifacts.mkdir(exist_ok=True)
    shutil.copyfile(dmg, artifacts / f"NearDot-{version}-{platform}.dmg")
    archive = base / "macos/Near Dot.app.tar.gz"
    shutil.copyfile(archive, artifacts / f"NearDot-{version}-{platform}.app.tar.gz")
    shutil.copyfile(str(archive) + ".sig", artifacts / f"NearDot-{version}-{platform}.app.tar.gz.sig")
print("Mac installer and updater verified and staged for draft review.")
