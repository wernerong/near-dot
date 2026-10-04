# Architecture

Tauri 2 / Rust owns OS operations; vanilla TypeScript/Vite owns a small packaged UI. Four local webviews provide the transparent companion, Settings, Chat and reply bubble. None loads remote HTML. The launcher needs no account or backend; the optional private Mac chat uses the separately authorized local MCP relay.

| Module                                | Responsibility                                                                                    |
| ------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `src/main.ts`, `style.css`            | Semantic settings, original companion animation, click/drag distinction, update controls          |
| `src/chat.ts`, `src-tauri/src/chat.rs`, `experiments/dot-relay/` | Local composer/bubble, bounded Rust helper/client lifecycle and private MCP mailbox |
| `src/platform.ts`                     | Narrow IPC adapter; inert browser preview                                                         |
| `src/validation.ts`                   | Immediate setup feedback; Rust is authoritative                                                   |
| `src-tauri/src/destination.rs`        | Canonical HTTPS host/scheme/path checks; no credentials or share links                            |
| `preferences.rs`                      | Versioned local preferences, defaults/migration, atomic replace; preserves corrupt/future data    |
| `avatar.rs`                           | Bounded still-PNG decode, metadata removal, atomic local image storage and preserved reset backup |
| `geometry.rs`                         | Work-area clamping for negative monitors, scaling and disconnection                               |
| `lib.rs`                              | Tray, native drag, OS opener, shortcut, startup, window settings and recovery                     |
| `startup.rs`, `windows-uninstall.nsh` | Windows per-user Run entry and uninstall cleanup; Mac launch-agent adapter                        |
| `updates.rs`                          | Signed channel controls, Tauri updater, package binding, eligibility and progress                 |

Renderer capabilities grant only event listen/unlisten. Custom commands check the caller's window; preferences, test-link and update installation are restricted to Settings. Arbitrary filesystem, shell, network, opener-plugin or updater-plugin commands are not exposed to JavaScript. Explicit browser opening always uses the validated saved destination; testing an arbitrary destination requires Settings and the same Rust validation.

Image import is available to Settings and Chat; reset remains Settings-only. Both are serialized in Rust. Import opens a native file picker; the renderer cannot supply a filesystem path. PNG input is bounded to 4 MiB, 1024 × 1024 pixels and a decoder allocation limit; animated PNGs are rejected. Re-encoding removes text/EXIF/ICC metadata. Only the normalized local PNG is sent as an image data URL to these local windows. There is no remote image access or new filesystem capability. The image is independent of preferences schema 1 and survives application replacement.

CSP allows packaged resources and local IPC. It blocks frames, object content and forms. Development CSP additionally permits the local Vite connection. CSS inline styles are allowed for local opacity only; scripts are not. Release notes use `textContent`, never HTML. URLs are passed as data to the maintained OS opener, never interpolated into command strings.

Coordinates are stored in physical pixels. Logical window size is converted by the OS at each monitor scale. Work areas exclude taskbars/menu areas. Recovery runs at startup, after size/scale changes, and every 15 seconds for disconnected-display cases, without bringing the app into focus. Position reset is available through tray and Settings. The tray and settings window provide entry paths without the companion.

Idle movement is a CSS transform, with no rendering polling loop. Hidden, paused and reduced-motion states pause/remove it. Update checks are native and run every six hours, with no ChatGPT message-content polling. A native worker wakes every second to debounce position persistence after movement; the monitor recovery check runs every 15 seconds. Neither renders UI.

Settings use a tempfile in the same directory followed by sync and atomic replacement. Schema 1 upgrades add defaults without overwriting private data. Invalid/newer schemas are preserved and block writes. Explicit Reset local settings backs the original file up and disables autostart. Public installers must not delete preferences during upgrades.

The updater pins a build-time public repository and Tauri public key. The same verification key signs package artifacts and channel metadata. A channel file includes pause/rollout/architecture, package URL, signature and SHA-256. Metadata is verified before parsing and compared to Tauri's subsequent response. HTTPS redirects are restricted to GitHub release hosts. A signed package plus a signed metadata hash prevents artifact substitution. Versions must be strictly newer; stable excludes prereleases. Preview/stable are selected locally. Rollout buckets remain local and are never sent.

Limitations: release-channel files are mutable to allow pause/rollout, and signed metadata can be replayed within the strictly-newer-version rule; no trusted timestamp service is used. A pause cannot revoke an already-downloaded package or stop an installer already running. A signed key compromise requires incident response, not a client preference bypass. Native transactional upgrade/recovery behavior is platform-dependent and must pass real installer testing before release.

Mac transparent windows use Tauri's macOS private API feature. This distribution is a directly distributed desktop utility, not a Mac App Store submission. A later store build needs a separate API/entitlement review.

## Experimental private Mac chat

Clicking the companion opens the local Chat window. Rust owns a bounded, persistent Python helper exposing snapshot/send/retry, plus the checksum-verified official tunnel client. Packaged relay scripts are fixed local resources; the renderer cannot choose executables, paths, callback URLs or credentials. Replies are literal text. Incoming bubbles do not request focus; snippet display is opt-in.

The worker checks only its local mailbox every two seconds while Chat is visible or a reply is pending, otherwise every ten seconds. It never polls ChatGPT. Messages and connection credentials stay in private per-user storage, separate from launcher preferences. The initial one-hour grant may be explicitly extended by the local owner up to 24 hours; a runtime key has its own independent expiry. Quit stops owned helpers. Windows chat is unavailable until credential ACLs and transport lifecycle are implemented and tested.

See [transport evidence](TRANSPORT-PROOF.md) for the documented MCP route and its limits. This route does not provide full ChatGPT history, global task status or avatar synchronization.
