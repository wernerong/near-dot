# Near Dot

An independent, local desktop companion for your existing dot, with a browser launcher. An explicit development build retains the experimental private Mac chat connection. Phase 1 targets **Windows x64 and Mac**; the iPhone companion is an Apple Shortcuts recipe.

**Candidate: 0.3.0-preview.1 — prepared locally, not published or cleared for public binary release.** The initial public release contains source and a checksum, with no signed installers or configured update feed. No paid signing service, launcher account, backend or OpenAI API billing has been created. See [acceptance evidence](docs/ACCEPTANCE.md) before treating any platform as supported.

![Settings browser preview, without personal links](docs/settings-preview.png)

## What it does

- Original transparent seed companion, gentle animation and hover feedback.
- Custom local PNG icon or pet sprite-sheet import, preserving the original idle frame with metadata stripped and no upload or profile scraping.
- One click or configurable global shortcut opens your tested destination in the default browser. Public installers do not expose an unavailable chat composer or run Python/tunnel helpers.
- Tray/menu bar access, hide/show, pause, size, opacity, always-on-top, position reset and settings.
- Opt-in login startup. Keyboard access through the settings window and tray; reduced-motion support.
- Guided first-run setup: test your destination, choose appearance and controls, review updates, then finish. Choices persist across relaunch and upgrade; existing verified installations skip the wizard.
- Signed update adapter with progress, errors, defer/skip, stable/preview channels and staged/paused rollout.

The public v0.1.0 release is a launcher. The public 0.3.0 preview candidate remains a launcher. The private MCP proof is behind an explicit development feature and is excluded from public installer resources. It does not export ChatGPT conversations, track global dot activity, synchronize all memory or sign in for you. A successful browser launch is **not proof that ChatGPT opened your dot**. Your device's Test link step establishes that. Keep the actual private conversation link out of source, screenshots, issues and releases; never use a public share link.

The official integration recheck on 4 October 2026 did not establish a public dot conversation API or stable third-party deep-link contract. General API conversation state does not grant access to an existing ChatGPT dot. Desktop ChatGPT/web and a supported mobile app are the official surfaces; mobile web is unsupported. Read the [capability matrix and sources](docs/FEASIBILITY.md).

## Run and build

Install Node **22.22.2**, Rust **1.95.0** and the [Tauri platform prerequisites](https://v2.tauri.app/start/prerequisites/). Windows needs Visual Studio C++ build tools and WebView2. Mac needs Xcode command-line tools. The launcher needs no API key. The optional private macOS chat preview needs the separately reviewed tunnel setup, its restricted runtime key and system Python 3.

```sh
npm ci
npm run tauri -- dev
```

Desktop release build, unsigned development packaging:

```sh
# Windows x64, in PowerShell
npm run tauri -- build --target x86_64-pc-windows-msvc --bundles nsis

# Apple Silicon Mac
CI=true npm run tauri -- build --target aarch64-apple-darwin --bundles app,dmg

# Intel Mac, on an Intel build machine
CI=true npm run tauri -- build --target x86_64-apple-darwin --bundles app,dmg

# Mac executable without installer packaging
npm run tauri -- build --no-bundle
```

The unsigned Mac `.app` lives in `src-tauri/target/TARGET/release/bundle/macos/Near Dot.app`; the Windows installer is under `src-tauri/target/x86_64-pc-windows-msvc/release/bundle/nsis/`. Do not distribute these unsigned development outputs as public releases or disable OS security to run them.

Browser-only visual preview (OS actions are deliberately unavailable):

```sh
npm run dev
# Open http://127.0.0.1:1420
# Companion preview: http://127.0.0.1:1420/?view=companion
```

Validation:

```sh
npm run check
npx playwright install chromium
npm run test:ui
cargo clippy --manifest-path src-tauri/Cargo.toml --locked -- -D warnings
cargo fmt --manifest-path src-tauri/Cargo.toml --check
npm audit --audit-level=moderate
cargo install cargo-audit --version 0.22.2 --locked
cargo audit --file src-tauri/Cargo.lock
# Private relay tests (macOS/POSIX only)
python3 -m unittest discover -s experiments/dot-relay -p 'test_*.py' -v
python3 scripts/scan-public.py
python3 scripts/run-gitleaks.py
```

If Node cannot find a locally trusted issuer, configure `NODE_EXTRA_CA_CERTS` with your machine's verified CA bundle. Keep certificate verification enabled. This is environment setup, not a client setting.

## Set up your link

1. In a desktop browser, open your existing dot in ChatGPT, signed into the correct account/workspace. If it exposes a distinct HTTPS address, copy the browser address bar, then open that address in a fresh tab and confirm it returns to the same dot. Do not use Share or create a public link. The official guidance does not document a dedicated private-link procedure; if no address reliably reopens your dot, leave the destination unconfigured.
2. Paste it in Settings. Near Dot displays it locally, accepts only `https://chatgpt.com` and rejects credentials, query/fragment tokens, nonstandard ports, share and API paths.
3. Select **Test link**. Confirm the default browser opens your existing dot. If it opens a different conversation, a login screen or an unavailable page, leave it unconfirmed and fix access in ChatGPT.
4. Tick the test confirmation, select **Continue**, choose appearance and controls, review automatic updates, then **Finish setup**. Clicking the companion or using the shortcut opens your saved dot link. Later, use the tray/menu bar’s Settings and updates to edit or test it again.

A released Windows installer installs for the current user and handles WebView2 setup (an internet connection is needed if WebView2 is missing). On Mac, open the matching architecture’s DMG, drag Near Dot to Applications, eject the DMG, then launch Near Dot from Applications. No terminal, API key or new login is needed for the public launcher. Detailed [installation and first-run instructions](docs/INSTALL.md) include recovery and removal.

Choose **Settings → Choose local image** for any still PNG up to 1024 × 1024 pixels and 4 MiB. Or choose **Import pet sprite sheet** for a downloaded PNG pet sheet up to 20 MiB: 1536 × 1872 or 1536 × 2288 pixels (192 × 208 cells). Near Dot extracts the first idle cell without regenerating or altering its pixels. Click the avatar in Chat to open the same appearance choices, including Restore default. Unsupported sheets and animated PNGs are rejected before replacing your image.

For an existing ChatGPT pet, use the download option in **Settings → Personalization → Pet** where available ([official pet documentation](https://learn.chatgpt.com/docs/pets)). Desktop custom pets may be stored only on the computer where they were created; use an exported PNG from that device. WebP exports must be saved as PNG first. This is a local import, with no account access or automatic avatar synchronization.

Only use art you have permission to use. Images are decoded and metadata is stripped; only the resulting still PNG is saved in your per-user app directory. It changes the companion and chat avatar, not the installed application or tray icon. Changing or restoring your image preserves the previous PNG locally.

**Always on top** defaults to enabled for new installations. Existing preferences are retained; enable it in Settings and save if it was previously off. The companion stays above ordinary app windows without focusing itself, and follows Mac Spaces while enabled. The chat and reply windows use the same setting. OS security screens and exclusive full-screen applications can override window stacking; full-screen coverage has not been established.

No desktop app scheme is enabled because the checked sources did not document an exact-dot launch contract. Links are per user and per device. Do not assume a desktop link works on an iPhone.

## Live messages and direct conversation

The explicitly enabled private Mac development build connects the [verified MCP relay](experiments/dot-relay/README.md) to a desktop chat panel and real incoming reply bubbles on the configured test Mac. Click the companion or use the shortcut, type a message, and press Enter. Shift+Enter inserts a newline. The window retains relay history across restarts, reports disconnected/expired states, and offers Reconnect using the already authorized private setup. A failed delivery retains its local message ID for retry. Closing Chat keeps the companion available for incoming bubbles. The companion’s small reply button or tray’s Show latest reply also opens the saved reply for keyboard access.

Enable **Settings → Show message text in desktop reply bubbles** to display snippets; this is off by default. Replies do not request focus. Choose your own PNG using the avatar button in Chat or Settings; there is no automatic profile/image sync. Voice, full ChatGPT history sync and global work status remain unavailable. No separate API assistant is used.

This private preview uses official Secure MCP Tunnel and MCP Events, a separately configured restricted runtime key, a dot subscription, the verified macOS arm64 tunnel client and system Python 3. It is not a public consumer connection flow. The initial one-hour proof window can be extended explicitly by its local owner up to 24 hours; runtime-key expiration remains independent. See [live evidence](docs/TRANSPORT-PROOF.md), [privacy](PRIVACY.md) and [remaining gates](docs/ROADMAP.md). The public v0.1.0 release remains the earlier launcher. Build the existing private proof only on its configured Mac with:

```sh
npm run tauri -- dev --features private-relay --config src-tauri/tauri.private.conf.json
# Packaged private development build, never attach it to a public release:
npm run tauri -- build --features private-relay --config src-tauri/tauri.private.conf.json --bundles app
```

The requested seamless live ChatGPT chat, incoming ChatGPT-origin replies and shared history remain a blocker. Installer preparation does not complete that goal. See [documented integration findings](docs/ROADMAP.md#live-chatgpt-conversation-sync-blocked).

## Updates and release readiness

The Settings footer and tray/menu bar stamp the running version; native app metadata and versioned installer filenames stamp the packaged version. `npm run version:check` checks all manifests and lockfiles; maintainers use `npm run version:set -- VERSION` to update them together. Prereleases default fresh installations to the Preview channel.

The manual **Prepare signed desktop draft** workflow prepares Windows x64, Mac arm64 and Mac Intel installers plus updater artifacts. It requires protected Authenticode, Developer ID/notarization and Tauri updater keys, verifies every signature against the shipped public key, and creates only a draft with a paused 0% feed. No release or channel is activated by this work.

Automatic checks occur after 30 seconds and every six hours; disable them in Settings. A release build needs a pinned verification public key and reviewed public GitHub repository. Development builds report that updates are unconfigured. No placeholder server or key is trusted.

Package installation normally requires user action. Windows installers may close this companion and require OS approval. Mac exposes a restart action after installation. Defer hides the offer until a subsequent check; skipping suppresses that version for automatic checks, while a manual check can offer it again. Optional unattended installation is a one-time opt-in for the next manual launch, before the companion appears; login startup and a running companion never install automatically. This mode still requires signed-installer acceptance testing before public release.

See [candidate notes](docs/releases/0.3.0-preview.1.md), [release runbook](docs/RELEASE.md), [security policy](SECURITY.md), [privacy](PRIVACY.md), [architecture](docs/ARCHITECTURE.md) and [troubleshooting/uninstall](docs/TROUBLESHOOTING.md).

## iPhone

Follow the [documented Shortcut recipe](docs/IPHONE.md). The default label is **Open ChatGPT**, with the remaining step of selecting your dot inside the supported app. Exact dot links are conditional on actual-device verification. No iPhone tests or simulator tests were run here.

## License and support

MIT is recommended and included for code and original art. Third-party packages retain their own licenses; review the locked dependency inventory before release. Near Dot is independent and is not affiliated with or endorsed by OpenAI or Apple. Support covers the companion's local controls and experimental relay, not ChatGPT account eligibility, service availability or dot behavior. Do not submit private conversation links or screenshots to a public issue.
