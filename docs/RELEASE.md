# Release and recovery runbook

Status: source preview authorized; signed installers remain in preparation. Do not publish later releases, enable another public service, enroll in paid signing or submit to a store without the user's final review. A local unsigned Mac development bundle is not a production recovery build.

The user has explicitly authorized a public repository and initial release. Version 0.1.0 is a **source-only development prerelease** with clear limits and no executable assets, updater feed or signing key. That publication does not waive any installer acceptance gate below, authorize paid services or enable production updates. Never attach the local development app, private preferences or personal avatar. Version 0.2.0-preview.1 prepares the private Mac chat source changes and release notes; it does not publish a binary or activate updates. Later binary workflows continue to prepare drafts for review.

## Set up protected infrastructure after approval

1. Choose a public repository identity and final app bundle ID. Review all tracked files, artwork, screenshots, lockfiles and examples. Keep destination URLs and identities local. Run Gitleaks over files and history, `scan-public.py`, npm audit, cargo audit and third-party license checks. Do not reuse any usage-widget secrets/configuration.
2. Protect main, release tags, CODEOWNERS and `.github/workflows/*`. Require review and passing CI. Add real CODEOWNERS privately during repository setup. Enable GitHub secret scanning/push protection, private security reporting and immutable releases where available. Confirm any paid account features before enabling them.
3. Create a protected `release` environment restricted to main, with required human reviewers and no self-review. Signing keys must never be available to pull-request jobs. CI permissions are read-only; draft job permissions are limited to Releases and provenance.
4. Obtain Windows Authenticode signing after cost/identity approval. This workflow accepts a protected PFX; production teams may substitute a reviewed hardware/cloud sign command. Do not place the PFX or its password in the client or source. Signing does not guarantee SmartScreen reputation. For Mac public distribution, obtain Developer ID and notarization credentials separately; Mac publication is not configured in the initial Windows draft workflow.
5. Generate a Tauri updater key in an approved secure signing environment. Back up the encrypted private key offline with access controls. Protect `TAURI_SIGNING_PRIVATE_KEY`, its password, `WINDOWS_SIGNING_PFX_BASE64` and `WINDOWS_SIGNING_PASSWORD` as release-environment secrets. Store only `NEAR_DOT_UPDATER_PUBLIC_KEY` as the verification public-key variable. A repository token is scoped to the workflow, never embedded in the app.

The checked Tauri updater uses mandatory artifact signatures; updater signing and Windows Authenticode are independent. [Tauri updater](https://v2.tauri.app/plugin/updater/), [Windows signing](https://v2.tauri.app/distribute/sign/windows/)

## Build a reviewable candidate

Keep `package.json`, `src-tauri/Cargo.toml` and `tauri.conf.json` versions in sync. Write `docs/releases/VERSION.md`. Run CI and the acceptance matrix on actual target hardware. Create a reviewed version tag; do not silently retag it.

For a local approved signing environment:

```sh
# Set NEAR_DOT_UPDATE_REPO and NEAR_DOT_UPDATER_PUBLIC_KEY first.
# Private signing material stays in protected environment variables/files.
npm ci
npm run release:config
npm run tauri -- build --target x86_64-pc-windows-msvc --bundles nsis --config release-config.json
```

`NEAR_DOT_UPDATE_REPO` must be present during Rust compilation as well as config generation. Rust pins that repository at compile time. The generated config is ignored by Git. The workflow refuses unsigned release builds and verifies Authenticode on the installer. Architecture-specific filenames include `windows-x86_64`; signed package identity is also bound by the signed channel file and SHA-256.

The manual **Prepare signed Windows draft** workflow builds a reviewed ancestor tag, runs checks, signs the executable/installer, generates a paused 0%-rollout feed, signs that feed, computes checksums, attests provenance and creates a draft GitHub Release. It does not publish or activate the channel. It has not been executed in this task.

## Review, publish and roll out

Verify installer publisher, Tauri signatures, SHA-256, provenance and release notes. Confirm cold/warm launch, shortcuts, destination flow, settings preservation, no private links in logs, a failed/tampered update, successful upgrade, interrupted-install recovery and clean uninstall. Attach sanitized evidence to the release review.

After user approval, publish the draft using GitHub's immutable-release flow. Once immutable, versioned assets are not a place to edit a rollout control. [GitHub immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases)

Keep mutable signed channel controls under `channels/stable.json` and `channels/preview.json` on protected main. Change `paused` and `rollout` only in the secure signing environment, sign the **exact file bytes** with the same Tauri key, and review/commit the JSON plus its `.sig` together. The app verifies the signature before reading controls. It rejects mismatched two-file deployments safely; a transient mismatch can require another check.

```sh
node scripts/make-feed.mjs release-artifacts OWNER/REPOSITORY stable 5
# Generated feeds intentionally start paused. Review and set paused=false locally.
npm run tauri -- signer sign release-artifacts/stable.json
node scripts/checksums.mjs release-artifacts
```

The `.sig` is Tauri CLI's base64-encoded Minisign signature, not a filename. Only signed, reviewed channel files may be activated. The repository uses public static GitHub files; there is no new backend. The local 0–99 cohort is never transmitted. Raise rollout 5 → 25 → 100 after each acceptance window. Preview and stable have separate controls. To pause, sign/publish `paused:true`; installs refresh eligibility before download. A running installer cannot be recalled by a later pause.

## Update behavior

Checks start after 30 seconds and repeat every six hours. Users can check manually, disable automatic checks, defer, skip or request installation. Errors do not install anything. Metadata URLs and redirects must use HTTPS and trusted GitHub hosts. Tauri verifies package signatures; the signed feed additionally binds artifact checksum, architecture, channel and newer version. No downgrade comparator is installed.

Unattended mode is an explicit one-time opt-in for the next **manual app launch**, before showing the companion. Login startup and an already-running companion never install automatically. The opt-in clears before the attempt so restart cannot loop. OS approval is not bypassed. `--no-unattended` bypasses it for that launch; uncheck the option in Settings to cancel permanently. This behavior must be verified with signed installers before publication.

On Windows, the maintained updater may close the app and invoke a passive installer after user-approved installation. It must not restart/close unrelated applications. On Mac, users normally select Restart after installation. Signing and OS protections remain in force.

## Recovery release drill — required before release

This drill is **not yet certified**. A successful unit test of a signature is not an installation/recovery test.

1. Install signed version A on a disposable Windows x64 machine. Configure a synthetic local destination and nondefault preferences; never publish a real dot URL.
2. Offer signed version B on a preview test channel and upgrade. Verify exact settings survive, hotkey/tray work and the new executable version is running.
3. Alter a copy of B's package bytes while retaining its signature. Offer it through a separately signed test feed with the altered checksum. Verify Tauri rejects the package before installation, A still launches and preferences survive.
4. Offer a wrong-architecture artifact and a version older than the running version. Verify both fail eligibility. Pause rollout after an offer but before installation; verify refreshed controls block installation.
5. Interrupt download, then installation at documented safe test points. Confirm either the original or upgraded version launches; inspect installer logs privately. If native installer recovery is inadequate, block release and change packaging before claiming support.
6. Build **C > B** using the trusted key and known-good code. Verify Authenticode, Tauri signature, checksum/provenance. Download C from the immutable versioned Release, quit the launcher, run C's signed installer via normal OS approval. Verify recovery and settings. Use a newer recovery release rather than an uncontrolled downgrade.
7. Uninstall using Windows Installed apps. Verify executable, tray, shortcut and opt-in startup registration are removed. Remove local preferences/backups only when requested; prove full removal on this test device.

For Mac, repeat with a Developer ID signed and notarized app, the actual updater `.app.tar.gz`, and both supported architectures before advertising them. Stop app and install the newer trusted notarized recovery bundle through normal OS flows. Test Gatekeeper and uninstall/login-item cleanup explicitly.

Lost updater key prevents the installed trust chain from accepting a new key. Recover through a manually installed independently verified OS-signed release, or a planned key transition while the old key is available; do not disable verification. Keep an offline trusted recovery artifact and documented hashes for emergency support.
