# Feasibility, rechecked 4 October 2026

This page records the initial launcher assessment. The later authorized MCP investigation established private two-way chat on one Mac; see the [current capability findings](ROADMAP.md) and [live transport evidence](TRANSPORT-PROOF.md). The initial matrix below is historical, not the current private-preview capability claim.

## Initial verdict

A local Windows/Mac launcher is feasible now. One-action access to a specific existing dot is conditional on a user's private HTTPS destination passing a local device test. The checked official documentation did not establish a public dot conversation API, third-party OAuth access to an existing dot, or a stable exact-dot app-link/URL-scheme contract. This is an evidence boundary, not a claim that no such integration could ever exist.

Use the official desktop or desktop-web surface for setup. The messaging guide says the mobile app requires its supporting update and explicitly excludes mobile web. There is no Safari dot fallback in this project. [OpenAI messaging](https://learn.chatgpt.com/docs/dots/channels)

## Initial launcher capability matrix

| Capability                                | Windows                                                                                       | Mac                       | iPhone                                                                                     | V1 decision                                                                                                      |
| ----------------------------------------- | --------------------------------------------------------------------------------------------- | ------------------------- | ------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------- |
| Exact existing dot conversation           | Official desktop/web surface exists; third-party exact launch not documented in checked pages | Same integration boundary | Supported mobile app conditional on update; exact third-party link routing not established | Desktop accepts only user-supplied, locally tested HTTPS link. iPhone exact link requires separate device proof. |
| Open ChatGPT                              | HTTPS desktop site can be opened using OS default browser                                     | Same                      | Shortcuts Open App action selects installed ChatGPT                                        | iPhone fallback label: Open ChatGPT; choose dot inside app                                                       |
| Embedded chat reaching real dot           | No public integration established                                                             | Same                      | No public integration established                                                          | Excluded                                                                                                         |
| Message/status notifications in companion | Official contact channels exist; no public launcher notification API established              | Same                      | Use official app/contact channels; no companion polling                                    | No unread count, task status or fake activity                                                                    |
| Authentication                            | User's existing ChatGPT/browser session                                                       | Same                      | Existing installed-app session                                                             | No launcher login, session/token access or account database                                                      |
| Account availability                      | OpenAI rollout/eligibility and workspace policy determine access                              | Same                      | Same account eligibility plus supported mobile update                                      | Launcher cannot grant access or diagnose eligibility from APIs                                                   |

OpenAI describes phased access and workspace controls. Current access includes eligible Pro tiers with age/region restrictions, Business Premium rollout, and administrator-enabled Enterprise rollout. Recheck the live access section before release; the launcher never treats a link as proof of eligibility. [Meet dots](https://learn.chatgpt.com/docs/dots)

The OpenAI Conversations/Responses API describes developer-managed API conversation state. It does not establish access to someone's existing ChatGPT dot, its history or its permissions. [API conversation state](https://developers.openai.com/api/docs/guides/conversation-state)

An embedded separate API assistant would have separate identity, history, memory, app permissions and API costs. That would change product scope and requires explicit user approval before implementation.

The later recheck for live animation, snippets, personal appearance and direct text/voice is recorded in [next-phase requirements](ROADMAP.md). Official MCP Events delivers events into ChatGPT rather than exporting dot activity. Local image customization does not establish a profile integration.

## Workspace and reusable patterns

The starting workspace was empty and not a Git repository; no applicable AGENTS.md was found in its parent chain. Two local usage-widget checkouts were available. The more recent one uses .NET 10, Avalonia 11.3.22 and Velopack 1.2.158, locked NuGet dependencies and Windows/Mac packaging scripts. The older checkout used zip distribution without Velopack. Read only source project metadata, platform helper code and workflow files; no credentials, private settings, personal screenshots or assets were copied.

Reusable ideas: desktop tray access, per-platform opening helpers, startup handling around updates, architecture-specific artifacts and an update acceptance script. The companion uses Tauri's maintained updater rather than transplanting the widget's .NET runtime or private integrations.

## Architecture and phases

1. **Windows/Mac launcher:** Tauri 2 with small TypeScript UI and Rust adapters. Original SVG art. Local preferences and destination validation. Windows x64 is the first public installer target. Mac implementation/build is included in phase 1; release claims depend on its test checklist.
2. **Signed updater/release preparation:** locked dependencies, pinned Actions, protected signing environment, draft Releases, signed packages and feed, checksums/provenance, stable/preview rollout controls. Public feed and production keys remain unconfigured until final review.
3. **iPhone recipe:** Open App → ChatGPT, Home Screen and Shortcuts widget. Upgrade to a private verified URL only if tested in the installed app. No fabricated schemes.
4. **Optional native iOS later:** SwiftUI/WidgetKit only if utility justifies signing, distribution and review costs. A widget launches its containing app; onward launch must be tested. No floating system-wide overlay, continuous widget animation or invented background state.

Real blockers for signed installers: actual Windows test hardware/VM; supported iPhone with account access; per-device dot-link verification; signing identity and protected updater key; a reviewed public feed; upgrade/recovery and uninstall evidence. One actual Mac link passed its signed-in browser test. Mac Intel remains untested. Public source publication is authorized; paid signing/store enrollment remains unauthorized.

## Official source ledger

All links below were opened/rechecked during this task on 4 October 2026. The WidgetKit web rendering exposed only a JavaScript shell, so its full text was not available through the research tool; native iOS routing remains a future verification item.

1. [OpenAI: Meet dots](https://learn.chatgpt.com/docs/dots) — existing-dot surfaces and account access.
2. [OpenAI: Message your dot](https://learn.chatgpt.com/docs/dots/channels) — desktop/mobile boundary and contact channels.
3. [OpenAI: API conversation state](https://developers.openai.com/api/docs/guides/conversation-state) — developer API conversations, not ChatGPT-dot access.
4. [Apple: URL schemes in Shortcuts](https://support.apple.com/en-asia/guide/shortcuts/apd621a1ad7a/ios) — app-specific schemes require an actual contract.
5. [Apple: Widget links](https://developer.apple.com/documentation/widgetkit/linking-to-specific-app-scenes-from-your-widget-or-live-activity) — later-phase containing-app routing; full page text unavailable here.
6. [Apple: App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/) — 2.5 platform rules and 4.2 minimum-functionality risk for a thin launcher.
7. [Tauri: Updater](https://v2.tauri.app/plugin/updater/) — package signature verification and update distribution.
8. [Tauri: Windows signing](https://v2.tauri.app/distribute/sign/windows/) — Authenticode separate from updater signing.
9. [Microsoft: SmartScreen reputation](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation) — signing does not guarantee no warning.
10. [GitHub: Immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases) — freeze versioned release assets after draft review.
11. [Apple: Home Screen shortcut](https://support.apple.com/guide/shortcuts/apd735880972/ios) and [Shortcuts widget](https://support.apple.com/guide/shortcuts/apd029b36d05/ios) — practical iPhone entry points.
12. [OpenAI: MCP Events](https://developers.openai.com/plugins/build/mcp-events) — events supplied to ChatGPT, not an export of dot messages/activity.
13. [OpenAI: Get started with your dot](https://learn.chatgpt.com/docs/dots/getting-started) — appearance customization; no documented third-party avatar export in the checked page.
