# Dedicated ChatGPT window on Windows

The requirement is to keep the actual ChatGPT dot, use normal ChatGPT chat limits, and avoid relinking windows. A separate API assistant or subscription-backed Codex companion would use a different conversation or allowance. Neither is used here.

Near Dot opens the user's verified HTTPS dot address in **the default Chrome or Edge browser's app mode**, outside Tauri. The ordinary ChatGPT site receives messages typed by the user and stores its own history and memory. This relies on the user's existing tested address, not an invented dot API or URL scheme. Other default browsers require selecting the ordinary Default browser link mode; dedicated mode does not silently substitute Edge.

## Setup and daily use

1. In Near Dot Settings, choose **Dedicated ChatGPT window · Windows**.
2. Paste the address of the existing dot and click **Test link**.
3. Sign in to ChatGPT in the dedicated window and confirm that it opens the expected dot. Save settings.
4. Click the pet or use its global shortcut. The chat appears beside the pet with the saved always-on-top preference.

Existing Windows preferences retain their saved address, verification, artwork, size and other choices. The new `chatMode` field defaults to the app window. The advanced private relay remains selectable. Mac retains its existing launcher/private-preview routing until its app-window adapter is implemented and tested.

The open window is cached automatically. On subsequent pet clicks it is restored and focused. If the window closes, its process changes, its handle is reused, or Windows restarts, Near Dot opens the saved ChatGPT address again and registers the new window automatically. There is no window picker or relink operation. The existing Edge profile/cache stay under `.near-dot/chat-app`; Chrome has its separate private profile/cache under `.near-dot/chat-app/chrome`. Both are outside AppData virtualization. Switching browsers requires one normal sign-in in the new profile and preserves the original profile. Near Dot never copies authentication data between them.

ChatGPT can require normal sign-in or MFA after a session expires. Internet and the selected Chrome or Edge installation are required. If the user navigates to another conversation inside the open ChatGPT window, that is ChatGPT's current conversation; Near Dot does not inspect page contents or force navigation while a conversation is open. Close that window and click the pet to reopen the saved dot.

## Incoming reply bubbles

Enable and save **Incoming reply notifications beside the pet** in Settings. Reuse the computer's authorized Near Dot plugin, reconnect the receiver if necessary, refresh the plugin's tools, and ask the dot to send a Near Dot notification for its replies in this conversation. A new user must authorize their own private connection once; browser sign-in does not grant this access.

The dot's `notify_reply` tool sends only a notice with a unique retry ID and an optional preview of up to 160 characters. It does not queue a relay chat message, send an event, perform inference or retrieve ChatGPT history. The local receiver works without an event subscription. It polls the protected inbox, displays the latest notice without requesting focus and acknowledges only the observed batch after successful display. Clicking the bubble or reply badge opens the actual dedicated ChatGPT window. Notices coalesce into the latest bubble; up to 50 records are retained and only already consumed records are recycled at capacity. Unconsumed notices survive restarting or hiding Near Dot. Text previews remain off unless explicitly enabled.

This is dot-requested notification delivery, not automatic browser completion detection. The dot must invoke the tool; no guarantee is made that every reply will call it. Disabling notifications rejects incoming tool calls while retaining saved notices, keys and chat history. There is no additional inference API or Codex billing route.

## Boundaries

- Near Dot sends no inference requests and has no paid fallback. User messages use whatever ChatGPT model and plan the user selects in the ordinary ChatGPT UI.
- Each persistent, owner-only profile is separate from the user's ordinary browser profile. Chrome or Edge owns login and cookie encryption. Near Dot never reads cookie databases, authentication files or tokens.
- No ChatGPT scraping, private backend automation, injected JavaScript, browser extension or remote debugging port is used. No remote content is loaded into Tauri.
- Public Windows APIs restore, place and focus only windows belonging to the selected dedicated browser profile. CIM examines that browser's launch arguments to identify the profile; only matching process IDs leave the query. Other window titles or message contents are not read.
- Cached process creation times plus a per-window property prevent handle reuse from targeting an unrelated window. The saved ChatGPT address never appears in diagnostics or release artifacts.
- The pet does not report global dot state, unread counts or AI progress. Its brief “Opening your chat” status concerns an OS window operation only. An opt-in reply preview comes from an explicit plugin notification, never browser inspection.

## Acceptance

Automated tests cover reuse, Near Dot restart, chat closure/Windows restart, stale handle/process recovery, changed saved address, invalid addresses/geometry, slow startup retries and preserved corrupt/future cache files. UI tests cover app-mode setup, persistence, absence of relay controls and the pet action. These are synthetic contracts, not proof of a signed-in ChatGPT connection.

Prepared-bundle validation for 1.1.0-preview.1: production frontend build, 21 JavaScript tests, 18 Playwright UI tests, 23 Rust tests, and 53 Python tests (48 passed; five Windows-only cases skipped on Linux). Rust tests and Clippy with warnings denied passed in an isolated Linux container; Rust formatting and the public-source guard passed, and npm reported no dependency vulnerabilities. Windows/macOS validation must still run in the repository's desktop workflow. A review installer does not complete the signed-in device checks below.

The CI follow-up canonicalizes synthetic temporary paths on Mac without weakening the production link/reparse-point checks. A hosted Windows probe measured cold browser-profile discovery at 11.7 seconds and later queries at about 0.35 seconds; the bounded discovery timeout is now 20 seconds, with a private-data-free retry error. The native caller retains its 45-second outer deadline. A Windows regression test checks that a discovery timeout does not expose launch arguments or the profile path. These checks still use local synthetic windows, not signed-in ChatGPT conversations.

Native Windows checks required before a stable release:

- [ ] Fresh install: Test link opens the dedicated Edge window; normal ChatGPT sign-in works, including MFA/challenges.
- [ ] The verified address opens the user's existing dot and its earlier history, not a new chat.
- [ ] Send in the window; the same message appears in that dot on ChatGPT web under the same account.
- [ ] Repeated pet clicks focus one window without spawning duplicates.
- [ ] Minimize and close the window; each is restored/recreated by the next pet click without relinking.
- [ ] Restart Near Dot and Windows; the saved address/profile survive. Normal ChatGPT reauthentication may still be requested.
- [ ] Multiple monitors, negative coordinates and 100/150/200% scaling place the chat on-screen.
- [ ] Always-on-top follows the saved preference; unrelated Edge windows remain untouched.
- [ ] Windows focus restrictions produce a clear error and allow clicking the visible chat to type.
- [ ] Upgrade/uninstall preserves personal settings; a normal upgrade preserves the Edge profile.

Official context rechecked 11 October 2026: [ChatGPT dots](https://learn.chatgpt.com/docs/dots), [dot channels](https://learn.chatgpt.com/docs/dots/channels), and [desktop floating pets](https://learn.chatgpt.com/docs/pets). These do not establish a public lossless dot-history API. [Desktop chat windows](https://learn.chatgpt.com/docs/app/settings) offer another UI route, but binding a native pop-out cannot reopen a specific dot automatically after ChatGPT restarts. The external saved-address route removes that binding dependency.
