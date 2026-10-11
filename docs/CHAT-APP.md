# Dedicated ChatGPT window on Windows

The requirement is to keep the actual ChatGPT dot, use normal ChatGPT chat limits, and avoid relinking windows. A separate API assistant or subscription-backed Codex companion would use a different conversation or allowance. Neither is used here.

Near Dot opens the user's verified HTTPS dot address in **Microsoft Edge app mode**, outside Tauri. The ordinary ChatGPT site receives messages typed by the user and stores its own history and memory. There is no second transcript to synchronize. This relies on the user's existing tested address, not an invented dot API or URL scheme.

## Setup and daily use

1. In Near Dot Settings, choose **Dedicated ChatGPT window · Windows**.
2. Paste the address of the existing dot and click **Test link**.
3. Sign in to ChatGPT in the dedicated window and confirm that it opens the expected dot. Save settings.
4. Click the pet or use its global shortcut. The chat appears beside the pet with the saved always-on-top preference.

Existing Windows preferences retain their saved address, verification, artwork, size and other choices. The new `chatMode` field defaults to the app window. The advanced private relay remains selectable. Mac retains its existing launcher/private-preview routing until its app-window adapter is implemented and tested.

The open window is cached automatically. On subsequent pet clicks it is restored and focused. If the window closes, its process changes, its handle is reused, or Windows restarts, Near Dot opens the saved ChatGPT address again and registers the new window automatically. There is no window picker or relink operation. The Edge profile stays under the same non-virtualized `.near-dot/chat-app` settings directory across Near Dot upgrades and Windows launches.

ChatGPT can require normal sign-in or MFA after a session expires. Internet and Microsoft Edge are required. If the user navigates to another conversation inside the open ChatGPT window, that is ChatGPT's current conversation; Near Dot does not inspect page contents or force navigation while a conversation is open. Close that window and click the pet to reopen the saved dot.

## Boundaries

- Near Dot sends no inference requests and has no paid fallback. User messages use whatever ChatGPT model and plan the user selects in the ordinary ChatGPT UI.
- The persistent, owner-only Edge profile is separate from the default browser profile. Edge owns login and cookie encryption. Near Dot never reads cookie databases, authentication files or tokens.
- No ChatGPT scraping, private backend automation, injected JavaScript, browser extension or remote debugging port is used. No remote content is loaded into Tauri.
- Public Windows APIs restore, place and focus only windows belonging to Near Dot's dedicated Edge profile. CIM examines Edge launch arguments to identify that profile; only matching process IDs leave the query. Other window titles or message contents are not read.
- Cached process creation times plus a per-window property prevent handle reuse from targeting an unrelated window. The saved ChatGPT address never appears in diagnostics or release artifacts.
- The pet does not report global dot state, unread counts, reply snippets or AI progress. Its brief “Opening your chat” status concerns an OS window operation only.

## Acceptance

Automated tests cover reuse, Near Dot restart, chat closure/Windows restart, stale handle/process recovery, changed saved address, invalid addresses/geometry, slow startup retries and preserved corrupt/future cache files. UI tests cover app-mode setup, persistence, absence of relay controls and the pet action. These are synthetic contracts, not proof of a signed-in ChatGPT connection.

Local validation for 1.1.0-preview.1: production frontend build, 21 JavaScript tests, 18 Playwright UI tests, 23 Rust tests, and 53 Python tests (48 passed; five Windows-only cases skipped on Linux). Rust tests and Clippy with warnings denied passed in an isolated Linux container; Rust formatting and the public-source guard passed, and npm reported no dependency vulnerabilities. Windows/macOS validation must still run in the repository's desktop workflow. A review installer does not complete the signed-in device checks below.

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
