# Install and set up Near Dot

Choose the reviewed installer from the [official project releases](https://github.com/wernerong/near-dot/releases). Version 1.0.1 adds the Windows startup repair and bundled live-connection runtime; v1.0.0 predates them. This independent project uses unsigned Windows installers and ad-hoc Mac bundles; publisher signing/notarization is not included. Tauri updater signatures are mandatory and independent of OS signing.

## Windows

1. Download `NearDot-VERSION-windows-x86_64.exe` from the reviewed GitHub Release. Phase 1 targets Windows 10/11 x64; ARM Windows is not certified.
2. Check the release source and checksum. Windows will not display a verified publisher. Run the installer for your Windows user. WebView2 setup is included; it needs the internet if the runtime is absent. Keep Windows protections enabled; SmartScreen or your organization’s policy may warn or block this unsigned app.
3. Launch Near Dot from Start. Follow its first-run setup. No Node, Rust, terminal, API key or new Near Dot account is required.

## Mac

1. Choose `NearDot-VERSION-darwin-aarch64.dmg` for Apple Silicon, or `NearDot-VERSION-darwin-x86_64.dmg` for Intel. The candidate minimum is macOS 12; actual-device certification is pending for each claimed OS/architecture.
2. Open the DMG. This release is not Developer ID signed or notarized, so Gatekeeper may block first launch. Drag **Near Dot** to **Applications**, eject the DMG, and launch it from Applications. Running from Applications also lets its updater replace the installed copy.
3. Follow first-run setup. Keep Gatekeeper enabled. If normal opening fails, verify the release source and follow [troubleshooting](TROUBLESHOOTING.md); do not bypass OS security.

## One-time setup on each device

1. **Test your link.** Sign in to your own ChatGPT account in your default browser, open your existing dot, and copy its HTTPS address if available. Paste it into Near Dot. Select Test link and confirm it actually reopened the same dot. A launch request alone cannot prove this. Do not create a Share link. If the URL cannot reliably reopen your dot, setup cannot establish exact-dot access.
2. **Make it yours.** Choose a local PNG or import an owned pet sprite sheet, or keep the original artwork. Set size, opacity and shortcut. Always on top defaults on; start at login defaults off. A conflicting shortcut produces a readable error; choose another or leave it blank.
3. **Updates and finish.** Automatic checks default on; Preview is selected for prerelease installations. Installation/restart requires your action unless you explicitly choose the one-time unattended option. Select Finish setup.

Your preferences and image stay on this device and survive upgrades. Setup is skipped on subsequent launches. The tray/menu bar provides Settings and updates, hide/show, pause, position reset and Quit. In current Windows builds, click the companion or use its shortcut to open Chat, then select Open ChatGPT for the saved destination. The published v1.0.0 and other public builds open the saved destination directly. A changed browser login, expired ChatGPT session, access change or broken link can require attention in ChatGPT or editing/testing the link again; a perpetual authenticated connection is not promised.

## Windows live connection in v1.0.1

The Windows v1.0.1 installer includes the chat interface and bundled local runtime. Choose **Chat → Connect my dot** to authorize your own tunnel, runtime key, MCP plugin and dot subscription in the guided flow. Enter credentials only in the native prompt. Each computer needs its own connection; do not copy another user's/Mac's key. Your linked workspace must allow custom MCP plugins and dots. The installer cannot grant these permissions from browser sign-in. Send remains disabled while setup or the dot subscription is incomplete. Disconnect pauses the connection; Reconnect resumes it. Only messages sent through this relay appear here; full ChatGPT history and global task status remain unavailable. A real automatic Windows reply, notification and relaunch check passed on one authorized setup; other users must verify their own connection. Public Mac installers retain the launcher, and the private Mac proof and its fixed deadline remain separate.

## Update, recovery and removal

Use Settings and updates to see the installed version, check manually, defer or skip an offer, then install/restart when ready. Update checks and downloads use HTTPS; both feed and packages must pass cryptographic verification. If a download fails, your current app/settings remain. Hosted release checks exercise rejected/truncated downloads, an actual Tauri upgrade, preference preservation and a manual reinstall. A power loss during native installation and physical OS security prompts remain untested.

For recovery, quit Near Dot and install a **newer** verified recovery release using the normal installer/DMG flow. Never replace the verification key or disable signature checks to force an older package.

On Windows, Quit then uninstall from Installed apps. On Mac, turn off Start at login in Near Dot, Quit, then remove Near Dot from Applications. Preferences, personal image and preserved backups remain unless you explicitly remove them using [complete data-removal instructions](TROUBLESHOOTING.md). Hosted tests check executable removal and retention of preferences; login-item and Start-menu cleanup on a physical device remain untested.

If OS policy blocks installation, stop and consult your administrator or wait for a publisher-signed release. Never disable Gatekeeper, SmartScreen, Defender or signature checking.
