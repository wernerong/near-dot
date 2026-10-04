# Security policy

Near Dot is in development. No production signed release is supported yet. Please report security findings privately through the repository's private vulnerability-reporting feature once it is enabled. Do not include a personal conversation URL in a public issue. No support email or personal identity is included in this template.

Threat boundaries: untrusted pasted URLs, compromised renderer/remote content, altered feeds/packages, accidental private data release, shortcut conflicts and corrupt local settings. Inputs are validated in Rust. Renderer capabilities are limited to local events; no remote content or website embedding. URL launch goes through an OS opener with a data argument.

The Tauri updater requires cryptographic package verification. This project also signs channel metadata and binds the package checksum, architecture, channel and version. HTTPS and signature checks cannot be disabled in the UI. Private signing keys and GitHub tokens belong only in protected release infrastructure. Only verification public keys and the public repository identifier are built into the client.

Authenticode on Windows, Developer ID/notarization on Mac, and Tauri updater signatures are separate controls. Never disable Defender, SmartScreen, Gatekeeper, certificate checks or OS approval to resolve a failure. Signing a new Windows artifact does not guarantee it avoids reputation warnings.

Before public release: protect main and version tags, require workflow/CODEOWNERS review, protect the `release` environment with human approval, enable secret scanning/push protection/private reporting where available, run dependency and secret scans, audit third-party licenses and verify package provenance/checksums. The provided workflow prepares a **draft**; publishing remains a separate human-reviewed action.

If updater signing is compromised, pause channels with the uncompromised control key if available, stop release signing, revoke affected OS certificates and publish an incident notice. Do not silently turn off signature verification. Prefer a newer signed recovery build. See the release runbook for key backup and recovery constraints.
