# Acceptance evidence and release gate

Recorded 4 October 2026 for the 0.2.0-preview.1 source preview. **Public binary release remains blocked.** The signed-release workflow and production update feed have not been activated.

## Automated validation

| Check | Evidence and scope |
| --- | --- |
| TypeScript production build | `npm run build`; packaged UI. |
| TypeScript tests | 15 tests: destination validation, drag threshold and release configuration using synthetic inputs. |
| Rust tests | 12 tests: validation, atomic preferences, corrupt/future preservation, geometry, update policy, image rules and bounded chat input. |
| Cryptographic tamper rejection | Ephemeral Minisign key: original accepted; altered bytes and wrong key rejected. This is not an installer upgrade test. |
| Private relay tests | 24 Python tests: protocol, callback validation/signatures, SSRF defenses, expiry, local-only extension, persistence, idempotent replies, retry, key handling, redacted health and desktop adapter. |
| Browser UI/accessibility | 7 Playwright tests including axe WCAG A/AA, keyboard, reduced motion, link confirmation, inert offline Chat and bubble actions. Not NVDA/VoiceOver certification. |
| Formatting/lint | Rust fmt and Clippy with warnings denied. |
| Secret scans | Public-source guard and checksum-pinned Gitleaks 8.30.1 over source and Git history. Generated/private files excluded. |
| Dependency audits | npm: zero reported vulnerabilities. Cargo: no blocking vulnerability; Linux-only warnings below. |

Public screenshots are [Settings](settings-preview.png) and [companion](companion-preview.png) browser previews with original artwork and no personal link. Personal native evidence is ignored locally.

Cargo warnings: `RUSTSEC-2024-0370` (`proc-macro-error`, unmaintained) and `RUSTSEC-2024-0429` (`glib`, unsound iterator). Neither dependency was found in the Mac target path; the Windows glib path was also empty. Linux is unsupported. Recheck target-specific paths and advisories for release; do not suppress them globally.

## Native Mac observations

- Unsigned arm64 `.app` built and ran. Native labelled controls, transparent companion and original/local artwork were inspected. Settings rejected a lookalike destination and invalid shortcut while preserving previous registration.
- One signed-in account's private destination reopened the same existing dot through a fresh browser tab, native Test link and the earlier launch action. This does not establish browser-cold, signed-out or cross-device behavior.
- The private chat build completed eight real relay exchanges, four from the native composer. After an explicit owner extension and workflow refresh, a fresh message produced an automatic incoming bubble without another browser instruction. Clicking the bubble reopened Chat. See [transport evidence](TRANSPORT-PROOF.md).
- Settings, relay history and a local PNG survived app replacement/restart. This is not a signed version upgrade or automatic avatar sync.
- The installed copy matched the tested bundle. Launch started the verified client without a terminal. Native Quit left no app or owned client process. Hide/show, position reset and single-instance behavior were exercised.
- Reconnect/status cleanup and the prerelease version bump are covered by local build/checks; the earlier native exchange remains the live transport evidence, not a new end-to-end test of every source revision.

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
