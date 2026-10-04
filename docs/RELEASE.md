# Release and recovery runbook

## Approved v1.0.0 distribution

The owner explicitly requested public v1.0.0 based on 0.3.0-preview.1, then approved **unsigned installers like AI Usage Widget** on 4 October 2026. This waives the OS publisher-signing prerequisite for this release only. It does not waive updater signatures, HTTPS, private-data exclusion or OS protections. Do not purchase certificates or enroll in stores without separate authorization.

The reference project uses .NET/Avalonia, Inno Setup, native Mac PKG packaging and Velopack. Near Dot retains Tauri's smaller existing stack and NSIS/DMG packaging. Reused patterns are architecture-specific self-contained installers, version stamping, all-platform release aggregation, persistent per-user settings and an installed-updater drill. No reference-project configuration, credentials or artwork were copied. Its checksum-only update trust model was not adopted.

Near Dot's `release` GitHub environment is restricted to protected branches and requires owner review. For this single-maintainer repository, self-review is allowed so the owner can execute their explicitly approved release. The encrypted Tauri updater key and password are separate environment secrets; only the public verification key is a variable/client input. Initial provisioning used a private temporary signing directory, uploaded encrypted GitHub secret payloads and removed temporary key files. GitHub holds the persistent signing copy; arrange an owner-controlled offline backup before key rotation or infrastructure migration. Never export a key to logs, artifacts, source or a client.

The **Prepare desktop release draft** workflow pins reviewed main (or an existing ancestor tag), requires successful exact-commit candidate CI and a successful baseline installer CI run. A new final release tag is created only when all builds/drills succeed; published tags are never moved. `os_signing=unsigned` selects the approved v1.0.0 model; `signed` retains the stronger certificate/notarization checks described below. Both modes require updater signatures. Hosted runners install the prior 0.3.0 installer into a temporary directory, reject altered and truncated real release packages through Tauri, install v1.0.0, preserve synthetic preferences, reinstall the verified candidate as recovery, and remove the executable while retaining preferences. The test harness is a Cargo example, never included in shipped binaries. Its loopback HTTPS server uses an ephemeral CA trusted only by that harness; TLS/signature validation remain enabled.

That drill does not certify power loss mid-install, an OS privilege prompt, unattended login behavior, all display configurations or physical-device accessibility. Those remain labelled in acceptance evidence. Real ChatGPT two-way conversation/history sync is still unavailable; release packaging does not change the integration boundary.

After every target succeeds, the workflow aggregates packages, verifies signatures, signs paused feed files, computes checksums, publishes provenance and creates a **draft**. Review the full draft before making it public. Publish once; never replace assets or move a published tag. The draft workflow also uploads separate signed activation controls for review at the requested `activation_rollout` percentage. Download and verify those exact bytes, commit them to protected main, then publish the reviewed draft and verify public downloads. Channel/evidence-only commits run signature, version, JavaScript, dependency and secret checks without rebuilding unchanged native applications, so later rollout pauses remain practical. No workflow auto-commits or activates a channel. Use staged rollout for subsequent updates and a newer trusted recovery version if needed.

## Set up protected infrastructure after approval

1. Choose a public repository identity and final app bundle ID. Review all tracked files, artwork, screenshots, lockfiles and examples. Keep destination URLs and identities local. Run Gitleaks over files and history, `scan-public.py`, npm audit, cargo audit and third-party license checks. Do not reuse any usage-widget secrets/configuration.
2. Protect main, release tags, CODEOWNERS and `.github/workflows/*`. Require review and passing CI. Add real CODEOWNERS privately during repository setup. Enable GitHub secret scanning/push protection, private security reporting and immutable releases where available. Confirm any paid account features before enabling them.
3. Create a protected `release` environment restricted to main, with required human reviewers; use no self-review when a second maintainer is available. Signing keys must never be available to pull-request jobs. CI permissions are read-only; draft job permissions are limited to Releases and provenance.
4. Obtain Windows Authenticode signing after cost/identity approval. This workflow accepts a protected PFX; production teams may substitute a reviewed hardware/cloud sign command. Do not place the PFX or its password in the client or source. Signing does not guarantee SmartScreen reputation. For Mac public distribution, obtain Developer ID and notarization credentials separately. The desktop draft workflow now prepares both Apple Silicon and Intel builds, but has not been executed with production credentials.
5. Generate a Tauri updater key in an approved secure signing environment. Back up the encrypted private key offline with access controls. Protect `TAURI_SIGNING_PRIVATE_KEY`, its password, `WINDOWS_SIGNING_PFX_BASE64` and `WINDOWS_SIGNING_PASSWORD` as release-environment secrets. Store only `NEAR_DOT_UPDATER_PUBLIC_KEY` as the verification public-key variable. A repository token is scoped to the workflow, never embedded in the app.

The checked Tauri updater uses mandatory artifact signatures; updater signing and Windows Authenticode are independent. [Tauri updater](https://v2.tauri.app/plugin/updater/), [Windows signing](https://v2.tauri.app/distribute/sign/windows/)

## Build a reviewable candidate

Run `npm run version:set -- VERSION` to stamp `package.json`, both npm lock entries, `src-tauri/Cargo.toml`, `Cargo.lock` and `tauri.conf.json` together. `npm run version:check` runs before every frontend/package build and rejects drift. Write `docs/releases/VERSION.md`. Run CI and the acceptance matrix on actual target hardware. Create a reviewed version tag; do not silently retag it.

For a local approved signing environment:

```sh
# Set NEAR_DOT_UPDATE_REPO and NEAR_DOT_UPDATER_PUBLIC_KEY first.
# Private signing material stays in protected environment variables/files.
npm ci
npm run release:config
npm run tauri -- build --target x86_64-pc-windows-msvc --bundles nsis --config release-config.json
```

`NEAR_DOT_UPDATE_REPO` must be present during Rust compilation as well as config generation. Rust pins that repository at compile time. The generated config is ignored by Git. The workflow always refuses unsigned updater packages. In `os_signing=signed` mode it also requires Authenticode; the approved v1.0.0 unsigned mode omits that certificate requirement. Architecture-specific filenames include `windows-x86_64`; signed package identity is also bound by the signed channel file and SHA-256.

The manual **Prepare desktop release draft** workflow resolves a reviewed ancestor tag to an exact commit before any signing job. The preflight requires successful exact-commit CI checks; protected jobs build Windows x64, Mac arm64 and Mac Intel. Publisher-signed mode requires Developer ID/notarization on Mac and Authenticode on Windows. The approved unsigned mode verifies the ad-hoc Mac seal and DMG integrity. Both modes check version/architecture and mandatory updater signatures. All three platform updater packages and both DMGs must exist before aggregation. The draft job verifies every signature against the shipped public key, generates a paused 0%-rollout feed, signs it, computes checksums, attests provenance and creates a draft GitHub Release. It does not publish or activate the channel. Consult the actual v1.0.0 workflow run and acceptance evidence for execution status.

Protected Mac secrets: `APPLE_CERTIFICATE` (base64 P12), `APPLE_CERTIFICATE_PASSWORD`, `APPLE_SIGNING_IDENTITY` (Developer ID Application), `APPLE_API_ISSUER`, `APPLE_API_KEY` and `APPLE_API_PRIVATE_KEY` (P8 contents). The P8 is staged with 0600 permissions in a temporary directory and removed at job end. Tauri handles the temporary signing keychain. Signing credentials are injected only into the build step. Keep secrets masked and do not upload raw notarization logs.

Public installers use the default Cargo feature set; never add `private-relay` or merge `tauri.private.conf.json` into a release. The prepared launcher is not the requested realtime-chat product. Before claiming that capability or advertising a permanent dot connection, resolve the documented provider/account/expiry blockers and prove real ChatGPT-origin messages and history sync.

Expected artifacts: `NearDot-VERSION-windows-x86_64.exe` plus `.sig`; `NearDot-VERSION-darwin-aarch64.dmg` and `.app.tar.gz` plus `.sig`; Intel equivalents with `darwin-x86_64`; signed `preview.json` or `stable.json`; `SHA256SUMS.txt` and GitHub provenance. Users install the EXE/DMG, while the Mac updater consumes the signed `.app.tar.gz`.

## Review, publish and roll out

Verify installer publisher, Tauri signatures, SHA-256, provenance and release notes. Confirm cold/warm launch, shortcuts, destination flow, settings preservation, no private links in logs, a failed/tampered update, successful upgrade, interrupted-install recovery and clean uninstall. Attach sanitized evidence to the release review.

After user approval, publish the draft using GitHub's immutable-release flow. Once immutable, versioned assets are not a place to edit a rollout control. [GitHub immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases)

Keep mutable signed channel controls under `channels/stable.json` and `channels/preview.json` on protected main. Change `paused` and `rollout` only in the secure signing environment, sign the **exact file bytes** with the same Tauri key, and review/commit the JSON plus its `.sig` together. The app verifies the signature before reading controls. It rejects mismatched two-file deployments safely; a transient mismatch can require another check.

```sh
node scripts/make-feed.mjs release-artifacts OWNER/REPOSITORY stable 5
# Generated feeds intentionally start paused. Review and set paused=false locally.
npm run tauri -- signer sign release-artifacts/stable.json
node scripts/verify-signatures.mjs release-artifacts
node scripts/checksums.mjs release-artifacts
```

The `.sig` is Tauri CLI's base64-encoded Minisign signature, not a filename. Only signed, reviewed channel files may be activated. The repository uses public static GitHub files; there is no new backend. The local 0–99 cohort is never transmitted. Raise rollout 5 → 25 → 100 after each acceptance window. Preview and stable have separate controls. To pause, sign/publish `paused:true`; installs refresh eligibility before download. A running installer cannot be recalled by a later pause.

## Update behavior

Checks start after 30 seconds and repeat every six hours. Users can check manually, disable automatic checks, defer, skip or request installation. Errors do not install anything. Metadata URLs and redirects must use HTTPS and trusted GitHub hosts. Tauri verifies package signatures and requires a signed version matching the announced version; the signed feed additionally binds artifact checksum, architecture, channel and newer version. No downgrade comparator is installed.

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

Lost updater key prevents the installed trust chain from accepting a new key. Recover through a manually installed independently verified release authenticated through an independent trusted channel, or a planned key transition while the old key is available; do not disable verification. Keep an offline trusted recovery artifact and documented hashes for emergency support.
