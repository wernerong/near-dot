# Troubleshooting and uninstall

**My click opens the wrong place.** The launcher can request a browser open but cannot inspect your dot. Edit/test the destination locally. Confirm the default browser's account and workspace. Use the private conversation address, not a share URL. If no usable private URL exists, exact access remains unsupported; open ChatGPT through its normal app UI.

**The link is rejected.** HTTPS on `chatgpt.com` is the only accepted destination. Remove credentials, query strings, fragments, nonstandard ports and share/login/API routes. Encoded path characters are conservatively rejected. Do not weaken validation to accept a token-bearing URL; keep the destination unconfigured until a safe supported link is available.

**Signed out or offline.** Settings, animation and tray work locally. Destination navigation requires the service/network and existing authentication. Login and account switching happen only in the official app/browser. Updates fail with a generic retryable error; there is no cached fake dot status.

**Shortcut conflict.** Choose another combination in Settings or leave blank to disable it. A failed registration keeps the old shortcut active. Startup registration failure appears as a warning; save a different shortcut. This utility registers combinations, not raw keystrokes.

**Companion missing.** Use tray/menu bar → Hide / show or Reset position. Reset places it within a monitor's work area. Recovery clamps disconnected-monitor positions every 15 seconds. Settings remains keyboard accessible without the companion. Close Settings hides it; Quit ends the launcher.

**Settings are corrupt/newer.** The file is preserved and writes are blocked. Reset local settings creates a preserved backup and returns to defaults, with startup disabled. Keep backups private. For a future-schema error, first try a newer signed recovery release.

**Update unavailable.** Development builds have no production verification key/feed; public release builds embed the verification public key. A configured release may be staged, paused, skipped, offline or lack an artifact for your architecture. Use Check for updates to retry. Signature/checksum failure must never be worked around by disabling security. Use the release runbook's signed recovery path.

**SmartScreen/Gatekeeper.** Version 1.0.0 has no verified Windows publisher or Mac Developer ID/notarization. Verify its GitHub release source and checksums. OS warnings or blocking are expected on some devices. Do not turn off OS protections. If OS policy blocks the app, stop and have the publisher resolve trusted distribution.

## Local data locations

Windows: `%APPDATA%\org.neardot.companion\preferences.json`. Mac: `~/Library/Application Support/org.neardot.companion/preferences.json`. Tauri's OS directory resolution is authoritative if a managed system redirects these locations. Reset backup: `preferences.preserved.json` in the same directory.

The app's destination remains in those private local files, never in installer examples. Upgrades preserve them. Reset removes active values but preserves the previous file, so it is not a privacy wipe.

## Uninstall

Windows: disable Start at login in Near Dot Settings, save, then Quit. Use Settings → Installed apps → Near Dot → Uninstall. The NSIS hook removes this app's per-user startup registration/override on uninstall and preserves it in updater mode; actual installer behavior still needs Windows verification. To remove all local data, use the uninstaller's app-data option if offered or delete the app-specific configuration directory and preserved backup after deciding whether you need them. Until the release test passes, explicitly disable startup first.

Mac: disable Start at login and save, then Quit. Remove Near Dot.app using Finder's normal Trash flow. Remove only this app's preferences/backups if desired. Check System Settings → General → Login Items for any remaining Near Dot entry. Do not remove another app's files. A direct-distribution app uninstall does not automatically erase user preferences.

iPhone: delete the Home Screen Shortcut icon, remove its Shortcuts widget and delete the Open ChatGPT shortcut in Shortcuts. The official ChatGPT app/account is independent of this recipe.

## Private Mac chat preview

**Clicking the icon now opens a panel.** Type a message and press Enter; Shift+Enter inserts a newline. Open ChatGPT remains an explicit button in the panel/tray. The reply button on the icon or Show latest reply in the tray opens the most recent saved relay reply.

**No message text in the bubble.** Enable Show message text in desktop reply bubbles in Settings and save. Preview text is off by default for privacy. The companion must be shown; hidden companions suppress incoming bubbles.

**Connection unavailable.** Choose Reconnect. On the configured test Mac the app starts the checksum-verified client with its existing private setup. It cannot create or renew credentials. A running client alone does not prove the dot subscription is active. Check the fixed relay deadline, runtime-key expiration and the existing dot's saved workflow. The owner-approved deadline must be verifiable through the connection check; an old one-hour stop condition in the dot workflow must be updated when the owner explicitly extends it.

**Delivered but no answer.** A successful event delivery is not a reply. Wait for the real reply; after three minutes the panel says it is taking longer. Avoid submitting the same message again. Undelivered messages have Retry delivery, which keeps the same message/event ID. Closing the panel does not cancel a delivered request.

**Different image after changing it in ChatGPT.** The companion uses a private local PNG. Click its avatar in Chat to choose an updated copy. Automatic image sync is not supported.

**Complete removal of the private preview.** Quit the app, remove its app bundle and optional preferences/avatar data, then retire the plugin/tunnel/key in their official controls. Separately remove `~/Library/Application Support/Near Dot/transport-proof` only after deciding whether to retain its message history. That private directory contains the diagnostic mailbox, credentials and verified client and is not removed by resetting launcher preferences. Never upload it to a public issue.
