# Install and set up Near Dot

These instructions describe the prepared 0.3.0-preview.1 installer flow. Signed public installers have **not** been published or certified. Use only a reviewed release with the signing and acceptance gates in [RELEASE.md](RELEASE.md) completed.

## Windows

1. Download `NearDot-VERSION-windows-x86_64.exe` from the reviewed GitHub Release. Phase 1 targets Windows 10/11 x64; ARM Windows is not certified.
2. Check the release checksum and publisher. Run the installer for your Windows user. WebView2 setup is included; it needs the internet if the runtime is absent. Keep Windows protections enabled; a new signed app may still have a reputation warning.
3. Launch Near Dot from Start. Follow its first-run setup. No Node, Rust, terminal, API key or new Near Dot account is required.

## Mac

1. Choose `NearDot-VERSION-darwin-aarch64.dmg` for Apple Silicon, or `NearDot-VERSION-darwin-x86_64.dmg` for Intel. The candidate minimum is macOS 12; actual-device certification is pending for each claimed OS/architecture.
2. Open the Developer ID signed, notarized DMG. Drag **Near Dot** to **Applications**, eject the DMG, and launch it from Applications. Running from Applications also lets its updater replace the installed copy.
3. Follow first-run setup. Keep Gatekeeper enabled. If normal opening fails, verify the release/publisher and follow [troubleshooting](TROUBLESHOOTING.md); do not bypass OS security.

## One-time setup on each device

1. **Test your link.** Sign in to your own ChatGPT account in your default browser, open your existing dot, and copy its HTTPS address if available. Paste it into Near Dot. Select Test link and confirm it actually reopened the same dot. A launch request alone cannot prove this. Do not create a Share link. If the URL cannot reliably reopen your dot, setup cannot establish exact-dot access.
2. **Make it yours.** Choose a local PNG or import an owned pet sprite sheet, or keep the original artwork. Set size, opacity and shortcut. Always on top defaults on; start at login defaults off. A conflicting shortcut produces a readable error; choose another or leave it blank.
3. **Updates and finish.** Automatic checks default on; Preview is selected for prerelease installations. Installation/restart requires your action unless you explicitly choose the one-time unattended option. Select Finish setup.

Your preferences and image stay on this device and survive upgrades. Setup is skipped on subsequent launches. The tray/menu bar provides Settings and updates, hide/show, pause, position reset and Quit. Click the companion or use its shortcut to open the saved destination. A changed browser login, expired ChatGPT session, access change or broken link can require attention in ChatGPT or editing/testing the link again; a perpetual authenticated connection is not promised.

## What this preview can support

Public installers are browser launchers. They do **not** provide desktop two-way chat, ChatGPT-origin reply bubbles, global task status or shared ChatGPT history. The expiring private Mac proof is excluded from public builds; it is not a consumer setup flow. See the [documented connection blocker](ROADMAP.md#live-chatgpt-conversation-sync-blocked). No separate assistant is substituted.

## Update, recovery and removal

Use Settings and updates to see the installed version, check manually, defer or skip an offer, then install/restart when ready. Update checks and downloads use HTTPS; both feed and packages must pass cryptographic verification. If a download fails, your current app/settings remain. Interrupted native installation and recovery still need the signed device drills before release.

For recovery, quit Near Dot and install a **newer** verified, OS-signed recovery release using the normal installer/DMG flow. Never replace the verification key or disable signature checks to force an older package.

On Windows, Quit then uninstall from Installed apps. On Mac, turn off Start at login in Near Dot, Quit, then remove Near Dot from Applications. Preferences, personal image and preserved backups remain unless you explicitly remove them using [complete data-removal instructions](TROUBLESHOOTING.md). Clean uninstall is a required device test, not yet certified.
