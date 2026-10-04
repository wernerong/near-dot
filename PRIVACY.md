# Privacy

The launcher stores preferences, your destination and an optional companion image on the current device. It does not collect telemetry, capture screens/audio or record keystrokes. Public installers contain no private relay scripts and do not start Python/tunnel helpers. The explicitly enabled private development build additionally stores its own messages and replies locally and uses a separately authorized OpenAI MCP connection, as described below. It does not poll ChatGPT conversations or global dot activity.

Choosing a local PNG uses a native file picker. Rust reads only the selected file, enforces file/pixel limits, strips metadata by decoding and re-encoding pixels, and saves `avatar.png` in the per-user app configuration directory. The renderer receives only that normalized image; it receives no source file path. There are no image uploads, external image URLs or ChatGPT profile requests. Restoring the default preserves the previous image in that private directory. Treat both image and backup as private and remove them during complete local data removal.

The global shortcut registers a single combination with the OS; it is not a keyboard recorder. Files are under the OS per-user application configuration directory, not the source tree. Your private URL is visible only in your local settings. Treat the preferences file and its preserved reset backup as private; OS account permissions protect them. They are not encrypted by this app.

Opening your destination contacts ChatGPT in the default browser under that browser's existing session and policies. The launcher cannot see whether you are signed in, offline or using the right workspace. Account behavior and costs remain with your existing ChatGPT product.

Configured release builds check public GitHub channel metadata after 30 seconds and every six hours. GitHub receives normal network metadata such as IP address and user agent. No destination, local rollout bucket or conversation content is included. Disable automatic checks in Settings. A manual check also contacts GitHub; downloads occur only after installation is requested.

Diagnostic strings are generic and contain no destination or raw network URL. There is no automatic crash/diagnostic upload. Public support requests should include app version, platform and generic failure category only. Remove personal links, names, tokens and screenshots from reports.

Reset local settings disables startup and preserves the old private file locally. For complete removal, follow the uninstall guide and remove that preserved file too.

## Optional private chat preview

On a configured Mac, the companion reads the explicitly connected local relay mailbox. Sending a message queues its text locally, delivers a signed MCP event, and lets the existing subscribed dot read that message and write a reply through two narrow tools. Messages therefore reach OpenAI under the authorized connection. The renderer receives mailbox text only; it cannot access the runtime key, subscription callback or signing secret. Text is rendered literally, with no remote content or executable markup.

The mailbox, callback secret, runtime key file, private connection metadata and verified tunnel client live outside the repository in the per-user `Library/Application Support/Near Dot/transport-proof` directory. Directory/file permissions are 0700/0600 (the executable is 0700); they are not encrypted by this preview. The relay stores exchanges until the owner removes its local data. The panel displays up to the latest 50 exchanges. This history covers only the relay, not all ChatGPT history. Avoid sensitive messages in this development preview.

Desktop reply text is off by default and can be enabled in Settings. Enabling it exposes snippets to anyone viewing your screen. Hidden companions do not display incoming bubbles. Opening Chat dismisses the bubble; dismissing a bubble does not delete the saved reply. A pending indicator means a submitted relay message is waiting for its reply, not that the dot is globally busy.

The initial proof grants one hour. The local owner may explicitly extend the fixed window up to 24 hours using the local CLI. Refresh/restart cannot extend it automatically, and the runtime key has a separate expiration. No renderer or MCP operation can extend the window. The desktop may restart only the checksum-verified official client with the already authorized private configuration; it does not create credentials or enable login startup. Retire the connection in the official account controls and remove its private local files for complete removal.

Personal artwork never belongs in public source, bundled assets or release screenshots. Avatar import is a local, one-time choice; automatic synchronization is unavailable.
