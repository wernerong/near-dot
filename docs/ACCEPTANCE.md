# Acceptance evidence and release gate

Historical evidence below was recorded 4 October 2026. Later sections track 0.3.0 preparation and the v1.0.0 release. Older blocked/pending entries describe that earlier revision, not a certification of current installers.

## Automated validation

| Check | Evidence and scope |
| --- | --- |
| TypeScript production build | `npm run build`; packaged UI. |
| TypeScript tests | 15 tests: destination validation, drag threshold and release configuration using synthetic inputs. |
| Rust tests | 14 tests: validation, atomic preferences, corrupt/future preservation, geometry, update policy, image rules and bounded chat input. |
| Cryptographic tamper rejection | Ephemeral Minisign key: original accepted; altered bytes and wrong key rejected. This is not an installer upgrade test. |
| Private relay tests | 24 Python tests: protocol, callback validation/signatures, SSRF defenses, expiry, local-only extension, persistence, idempotent replies, retry, key handling, redacted health and desktop adapter. |
| Browser UI/accessibility | 9 Playwright tests including axe WCAG A/AA, keyboard, reduced motion, link confirmation, inert offline Chat and bubble actions. Not NVDA/VoiceOver certification. |
| Formatting/lint | Rust fmt and Clippy with warnings denied. |
| Secret scans | Public-source guard and checksum-pinned Gitleaks 8.30.1 over source and Git history. Generated/private files excluded. |
| Dependency audits | npm: zero reported vulnerabilities. Cargo: no blocking vulnerability; Linux-only warnings below. |

Pet import tests verify exact first-cell pixels and transparency for both supported PNG layouts, metadata stripping, restart persistence, previous-image preservation and rejection without replacement. Appearance choices pass browser keyboard/modal-focus and automated accessibility checks. New-install floating defaults on; explicit existing off preferences remain off.

Public screenshots are [Appearance choices](appearance-preview.png), [Settings](settings-preview.png) and [companion](companion-preview.png) browser previews with original artwork and no personal link. Personal native evidence is ignored locally.

Cargo warnings: `RUSTSEC-2024-0370` (`proc-macro-error`, unmaintained) and `RUSTSEC-2024-0429` (`glib`, unsound iterator). Neither dependency was found in the Mac target path; the Windows glib path was also empty. Linux is unsupported. Recheck target-specific paths and advisories for release; do not suppress them globally.

## Native Mac observations

- Unsigned arm64 `.app` built and ran. Native labelled controls, transparent companion and original/local artwork were inspected. Settings rejected a lookalike destination and invalid shortcut while preserving previous registration.
- One signed-in account's private destination reopened the same existing dot through a fresh browser tab, native Test link and the earlier launch action. This does not establish browser-cold, signed-out or cross-device behavior.
- The private chat build completed eight real relay exchanges, four from the native composer. After an explicit owner extension and workflow refresh, a fresh message produced an automatic incoming bubble without another browser instruction. Clicking the bubble reopened Chat. See [transport evidence](TRANSPORT-PROOF.md).
- Settings, relay history and a local PNG survived app replacement/restart. This is not a signed version upgrade or automatic avatar sync.
- The installed copy matched the tested bundle. Launch started the verified client without a terminal. Native Quit left no app or owned client process. Hide/show, position reset and single-instance behavior were exercised.
- Reconnect/status cleanup and the prerelease version bump are covered by local build/checks; the earlier native exchange remains the live transport evidence, not a new end-to-end test of every source revision.

## Local appearance and floating-window follow-up

The same public source was continued in the new workspace; private art and credentials were not copied into it. The updated local arm64 development app was built, signed ad hoc, verified with `codesign --verify --deep --strict`, and its installed executable matched the tested bundle. This is not distribution signing or notarization.

- Native Chat avatar chooser offered pet-sheet import, custom PNG and restore-default actions.
- A real owned PNG pet sheet was imported through that chooser; the original first idle frame appeared on the companion without an external cropper. The image survived replacement/relaunch. Personal evidence remains ignored locally.
- Existing always-on-top was explicitly enabled and saved on the test device. After relaunch, the OS-reported floating-window state stayed enabled while a Chrome search control held focus. This confirms the native window level; browser screenshots do not capture other applications’ overlays.
- Mac Spaces following uses Tauri’s supported window API but has not been exercised by a physical Space switch. Full-screen/security-screen overlay behavior and Windows device behavior remain untested.
- Automated checks: 15 TypeScript, 14 Rust, 24 relay and 9 browser tests passed; Clippy/fmt, npm audit and public-source/Gitleaks scans passed. Existing Linux-only Cargo warnings remain.
- Release assets are unchanged; no new binary release was published for this follow-up.

## Performance

Phase-1 budgets: mean animated idle CPU ≤1% of one core, hidden ≤0.1%; main RSS ≤100 MiB; combined application/WebView memory ≤200 MiB; launch to first UI IPC ≤2 seconds.

| Build / mode | Sample | Main CPU | Median / peak main RSS |
| --- | --- | --- | --- |
| Earlier launcher, paused | 30 seconds | 0.033% | 76.17 / 76.23 MiB |
| Earlier launcher, animated | 30 seconds | 0.230% | 82.03 / 84.23 MiB |
| Earlier launcher, hidden | 30 seconds | 0.000% at sampler resolution | 79.45 / 79.53 MiB |
| Private chat build, visible | 20 seconds | 0.099% | 105.06 / 105.08 MiB |

The chat build exceeds the main-process memory budget. These samples exclude WebKit, Python and tunnel helpers; total footprint and current hidden-mode performance remain unmeasured. Earlier launcher starts reached first UI IPC in 392 ms and 398 ms with warm filesystem caches. Current-build startup distribution remains unmeasured. No Windows performance claim is made.

## Required device and installer checks

| Scenario | Windows x64 | Mac arm64 | iPhone |
| --- | --- | --- | --- |
| Build/run | CI recipe; native device untested | Unsigned build and launch passed | Shortcut recipe only |
| Direct existing-dot chat | Unavailable | Private setup verified above | Unavailable |
| Cold/warm exact link, signed-out/wrong account | Untested | Signed-in warm link only | Physical app verification required |
| Offline operation and reconnect failures | Untested | Local persistence and unconfigured-update error exercised; full network matrix open | Untested |
| Global shortcut conflicts | Untested | Invalid registration rejected; physical trigger/conflicts open | Not applicable |
| Drag/click and multiple/scaled/disconnected monitors | Geometry unit tests only | Reset exercised; physical drag and multi-monitor open | No floating overlay |
| Keyboard/screen reader and focus soak | Browser checks only | Native labelled controls and one non-focus-stealing bubble observed; VoiceOver/soak open | Untested |
| Login startup | Untested | Defaults off; OS login start untested | Not applicable |
| Signed upgrade/settings preservation/tampering | Unit crypto only | Same-version replacement and unit crypto only | Apple distribution only |
| Interrupted install/newer signed recovery | Untested | Untested | Native phase deferred |
| Opt-in unattended install/OS approval | Untested | Untested | Not applicable |
| Clean uninstall and data/startup cleanup | Untested | Instructions only | Recipe removal untested |

Windows remains the first planned public installer target. Mac private chat does not establish general account eligibility, key renewal, long-duration reliability, full history, global task state, voice or automatic image sync. Complete [release drills](RELEASE.md), artifact/privacy/license review and remaining device checks before a public binary release.

## 0.3.0-preview.1 release preparation

This is a locally prepared candidate, not a public binary release. The previous native private-chat observations above remain historical evidence; they do not establish the public preview’s live chat or history sync. The requested realtime ChatGPT conversation goal remains blocked.

| Candidate check | Result and boundary |
| --- | --- |
| Production frontend and version drift | Passed; package, Tauri, Cargo and both lockfiles agree on 0.3.0-preview.1. |
| TypeScript tests | 18 passed, including complete platform feed requirements and release signature/version substitution checks. |
| Rust tests | 15 passed, including fresh/incomplete/completed setup persistence and verified legacy migration. Corrupt/future files remain preserved. |
| Browser UI | 10 passed; first-run/reopen uses explicitly synthetic IPC/preferences, not a live ChatGPT or OS-launch test. Existing axe and keyboard checks passed. |
| Private relay regression | 24 passed. Explicit `private-relay` feature compiles on this Mac; no new live message exchange was claimed. |
| Rust lint/format | Clippy with warnings denied and rustfmt passed. |
| Signature compatibility | Actual pinned Tauri CLI generated an ephemeral key and version-bound signature. Release verifier accepted it and rejected altered bytes; temporary keys were removed. This is not a signed installer upgrade. |
| Workflow review | Checksum-verified actionlint 1.7.12 passed both desktop workflows, including current Intel/ARM runner labels. No production signing workflow was dispatched. |
| Secret/privacy scans | Public-source guard and Gitleaks source/history checks passed. Original-art screenshots only; personal links/images remain excluded. |
| Dependency audits | npm zero vulnerabilities using the system’s trusted CA bundle; Cargo retained the documented Linux-only warnings above. |
| Mac arm64 packaging | Public `.app` and DMG built locally in Tauri CI mode (no Finder layout scripting). Bundle metadata stamps 0.3.0-preview.1, executable reports arm64, and no private relay resources are bundled. Local sizes: app about 15.6 MiB, DMG about 6.3 MiB. Development output has no Developer ID signing/notarization; zero valid local Developer ID identities were found. |
| Windows x64 / Intel Mac installers | Workflow matrix prepared; this revision’s target builds/device execution have not been run here. Prior Windows/Mac CI applies to the earlier source only. |
| Production automatic update service | Signing/public-key/feed infrastructure not activated. Signed feeds start paused/0%; installer signatures and signed version are mandatory. |
| Fresh signed install, upgrade and recovery | Still required on Windows x64 and each supported Mac architecture, including settings preservation, tampering, interruption, restart, uninstall and OS protections. |
| Current candidate performance / accessibility certification | Budgets above retained; current native performance, total helper/WebView footprint, VoiceOver/NVDA and focus soak still unmeasured. |

The [onboarding screenshot](onboarding-preview.png) is labelled as a synthetic UI demonstration. It contains no personal URL or identity. [Installation instructions](INSTALL.md) describe the one-time per-device launcher setup and the circumstances that can require reauthentication or retesting a link. This does not promise a permanent authenticated dot connection.

Do not claim stable public support for Windows or Mac until the signed device checklists pass. Publication, update-channel activation and signing/account costs remain behind final review.

## v1.0.0 release candidate

The owner approved public v1.0.0 based on 0.3.0 and explicitly selected the reference widget's unsigned OS installer model. Windows Authenticode and Mac notarization are absent; no costs were incurred. Mandatory updater cryptographic verification remains enabled.

Local candidate checks: 21 TypeScript tests, 15 Rust tests, browser UI/accessibility checks, native compilation of the isolated updater harness, formatting/Clippy and public-source scans. Hosted Windows x64, Mac arm64 and Intel checks plus the real install/update drill must complete before publishing the draft. This paragraph records the gate, not a claimed successful run; the published workflow logs are the execution evidence.

The release drill uses the actual successful 0.3.0 installer artifacts, synthetic preferences and the real Tauri updater against HTTPS on loopback. It covers altered/truncated package rejection, upgrade to v1.0.0, preservation of preferences, recovery reinstall and executable removal. It does not prove power-loss recovery mid-install, a live desktop restart, login-item cleanup, native screen-reader behavior or new ChatGPT integration. The private installed connection is not touched by these tests.

Local Apple Silicon updater drill passed: installed the actual 0.3.0 DMG into an isolated temporary directory, then used Tauri's updater to reject both altered and truncated packages with `Minisign(InvalidSignature)`. The intact version-bound 1.0.0 archive installed successfully and its ad-hoc bundle seal verified. This run used an ephemeral test signing key and a valid local TLS certificate chain; no production private key, saved user preferences or installed private app was accessed. Hosted production-key drills remain separately required.

## v1.0.0 hosted release evidence — 5 October 2026 (Singapore)

The 0.3.0 baseline is committed and pushed as `v0.3.0-preview.1` at `800409e53e24c3a96af8c850870783bbab4cfd23`. Its [three-platform validation and installer build](https://github.com/wernerong/near-dot/actions/runs/37210862464) passed. The v1.0.0 source is `0ae5575b501469c4c0607022afdf97242982ca64`; its [exact-commit validation](https://github.com/wernerong/near-dot/actions/runs/37221267140) passed on Windows x64, Apple Silicon and Intel Mac, including native packaging, unit/UI checks, audits and secret scans.

The [protected release workflow](https://github.com/wernerong/near-dot/actions/runs/37223376923) uses the actual baseline installers and production-signed v1.0.0 packages. Each completed drill below observed two `Minisign(InvalidSignature)` rejections, successful Tauri installation of the intact package, unchanged synthetic preferences, manual recovery reinstall and removal of the installed executable. The Windows check compares the installed executable with the exact NSIS payload; Tauri intentionally restores an unpatched build-directory executable after packaging.

| Release target | Hosted installer/update drill |
| --- | --- |
| Windows x64 | [Passed](https://github.com/wernerong/near-dot/actions/runs/37223376923/job/111498031359) |
| Apple Silicon Mac | [Passed](https://github.com/wernerong/near-dot/actions/runs/37223376923/job/111498031370); ad-hoc bundle seals also verified |
| Intel Mac | [Passed](https://github.com/wernerong/near-dot/actions/runs/37223376923/job/111498031331); ad-hoc bundle seals also verified |

These results supersede the historical installer-only entries above. They do not close the physical-device, login-item cleanup, native accessibility, cold/signed-out ChatGPT, performance or power-loss-during-installation gaps. They do not establish live ChatGPT conversation sync. The unsigned OS distribution exception remains explicit; mandatory updater signature verification was not relaxed. No private installed app, personal destination, credentials, conversation or artwork was used in the hosted drills.

Final artifact review passed: all 15 downloaded release assets matched the expected inventory; all 14 checksum entries matched; all six package/feed signatures verified against the committed public key; and the shipped key and third-party notices matched source. The [GitHub-hosted provenance](https://github.com/wernerong/near-dot/attestations/52627234) records matching hashes for all 15 subjects and the reviewed release workflow. Both separately signed stable/preview activation controls were verified against those same packages at 100% rollout, unpaused.

[Public v1.0.0](https://github.com/wernerong/near-dot/releases/tag/v1.0.0) was published as a stable, immutable release. An unauthenticated check confirmed it is the latest release and all 15 HTTPS downloads are accessible with their expected sizes. First-time and unconfigured development installations should use the matching installer; the isolated baseline updater drill does not claim that every older preview already contains this release's public verification key.
