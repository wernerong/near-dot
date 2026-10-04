# Privacy

Near Dot stores preferences, your destination and an optional companion image on the current device. It does not collect telemetry, retain conversations, authenticate to OpenAI, capture screens/audio, record keystrokes or poll message content.

Choosing a local PNG uses a native file picker. Rust reads only the selected file, enforces file/pixel limits, strips metadata by decoding and re-encoding pixels, and saves `avatar.png` in the per-user app configuration directory. The renderer receives only that normalized image; it receives no source file path. There are no image uploads, external image URLs or ChatGPT profile requests. Restoring the default preserves the previous image in that private directory. Treat both image and backup as private and remove them during complete local data removal.

The global shortcut registers a single combination with the OS; it is not a keyboard recorder. Files are under the OS per-user application configuration directory, not the source tree. Your private URL is visible only in your local settings. Treat the preferences file and its preserved reset backup as private; OS account permissions protect them. They are not encrypted by this app.

Opening your destination contacts ChatGPT in the default browser under that browser's existing session and policies. The launcher cannot see whether you are signed in, offline or using the right workspace. Account behavior and costs remain with your existing ChatGPT product.

Configured release builds check public GitHub channel metadata after 30 seconds and every six hours. GitHub receives normal network metadata such as IP address and user agent. No destination, local rollout bucket or conversation content is included. Disable automatic checks in Settings. A manual check also contacts GitHub; downloads occur only after installation is requested.

Diagnostic strings are generic and contain no destination or raw network URL. There is no automatic crash/diagnostic upload. Public support requests should include app version, platform and generic failure category only. Remove personal links, names, tokens and screenshots from reports.

Reset local settings disables startup and preserves the old private file locally. For complete removal, follow the uninstall guide and remove that preserved file too.
