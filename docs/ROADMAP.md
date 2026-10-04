# Next phase: a companion for the real dot

Near Dot's goal is two-way chat with the user's existing dot, incoming reply bubbles and conversation synchronization. Version 0.2.0-preview.1 includes the private Mac chat experiment. **On 4 October 2026, the MCP relay and native companion passed the real-message gate on one Mac/account, including reconnect, a follow-up recall test and an incoming desktop bubble.** No separate assistant or synthetic reply was substituted. See [observed evidence](TRANSPORT-PROOF.md) and the [experiment commands](../experiments/dot-relay/README.md).

## Integration findings

| Option | Established capability | Boundary |
| --- | --- | --- |
| ChatGPT desktop/web/mobile | Official access to the existing dot. A private desktop address reopened the same dot on the tested Mac. | No stable third-party deep-link contract established. No scraping, session-token access, embedding or browser automation as product transport. Mobile web is unsupported. |
| MCP Events and reply tool | The existing dot subscribed, read CLI and desktop messages and returned eight correlated replies. Restart recovery and one cross-message recall passed. | Only this private account/setup was tested. No complete ChatGPT transcript export, global task status or arbitrary outgoing-message feed. |
| Official Secure MCP Tunnel | Official client forwarded discovery and tool calls to the private stdio server, with a separate restricted runtime key and workspace association. | Private developer-mode testing, not established public distribution. Public authentication/deployment and account eligibility remain gates. |
| Slack/Teams | Official docs describe channels reaching the same dot, with channel-local histories. | No adapter exchange tested. Needs the channel's authorized APIs and account availability; it does not mirror all ChatGPT messages. |
| Sign in with ChatGPT | Identity and separately authorized eligible Responses API usage. | Does not grant ChatGPT conversation access. |
| Conversations/Responses API | Developer-managed API conversation state. | No mapping to the existing dot established. A separate assistant is excluded from this product goal. |
| Codex CLI/App Server | Codex agent threads. Installed CLI help and generated schemas were inspected. | No existing-dot method established. The successful proof used the separate official tunnel client. |
| Enterprise-managed MCP lifecycle hooks | Official documentation supports remote MCP hooks for dots when managed policy and remote hooks are enabled. `UserPromptSubmit` and `Stop` are documented lifecycle events. | Candidate for future-message capture, not live-proven here. Personal accounts are explicitly excluded. Cloud payload fields, event coverage, replay, latency and consumer availability require verification. |
| MCP App model-context extensions | Official SDK exposes app context updates and current app context; an embedded component can send user follow-ups to its active chat. | App-state sharing is not a conversation-message feed. The SDK does not establish an external desktop transcript subscription. |

The tested route is local message → signed subscribed event → existing dot read tool → existing dot reply tool → local reply. The browser was used for setup and independent verification, not to carry test messages. An acknowledged webhook was never counted as a reply. The original dot independently reported the first two exact message IDs and replies from its tool activity without being given those values in the audit prompt.

The relay can store and retrieve its own exchanges. One successful recall demonstrates continuity in the tested setup; it does not establish reliable access to every previous ChatGPT message or full shared memory. Keep those claims separate.

## Live ChatGPT conversation sync: blocked

Rechecked 4 October 2026 after a device report of missing ChatGPT-origin messages and separate companion history. The existing-dot reply proof does **not** satisfy this requirement.

The current reply tool accepts only a reply to an already queued Near Dot message ID. The desktop adapter reads the local relay mailbox, not a ChatGPT transcript. Its two-second active / ten-second inactive local refresh adds display latency, but reducing it cannot retrieve missing ChatGPT messages. No ChatGPT-origin message listener, unsolicited-message tool, transcript cursor, or streamed reply transport is implemented.

The official sources checked establish these boundaries:

- [MCP Events](https://developers.openai.com/plugins/build/mcp-events) delivers external-server events into the subscribed ChatGPT chat. Receipt is asynchronous; this integration does not support the draft's streaming delivery. This does not establish an outgoing ChatGPT transcript feed or token stream.
- [Message your dot](https://learn.chatgpt.com/docs/dots/channels) describes the same dot across contact methods, but explicitly says Slack and Teams histories do not mirror every message from other channels. Relevant context across channels is different from identical transcripts.
- [MCP App UI](https://developers.openai.com/plugins/build/chatgpt-ui) documents host-contained components, tool results and follow-up messages. [Plugin Extensions](https://developers.openai.com/plugins/build/extensions) describes model/app context sharing. These pages do not establish an external desktop application's right to subscribe to the entire dot conversation.
- [Workspace Agent triggers](https://developers.openai.com/workspace-agents/trigger-runs) target published workspace agents; the documentation says the agent response cannot currently be retrieved through that API. No mapping to a personal existing dot was established.
- [Compliance records](https://learn.chatgpt.com/docs/enterprise/compliance-api) require administrative access and serve audit/investigation workflows. This does not establish a consumer two-way dot chat API.
- [API conversation state](https://developers.openai.com/api/docs/guides/conversation-state) manages API conversations; no mapping to an existing ChatGPT dot was established.

Unblocking the requested experience requires a documented, authorized connection to the existing dot that can receive ChatGPT-origin messages, submit messages into the same conversation, retrieve/replay history with stable IDs, and support measured live delivery. Test messages in both interfaces, reconnect and missed-event recovery, duplicate handling, and independent transcript comparison before claiming synchronization. Token streaming requires its own supported contract and evidence.

A model voluntarily copying selected messages through a new MCP tool could be a separate forwarding feature. It would not establish automatic or complete sync and must not be presented as this requirement's completion. No substitute assistant, browser scraping, session-token reuse, or private backend route is permitted.

### Strongest remaining candidate: managed lifecycle hooks

The [Hooks documentation](https://learn.chatgpt.com/docs/hooks#managed-hooks-from-requirementstoml) and [cloud local-access guide](https://learn.chatgpt.com/docs/enterprise/cloud-local-access) explicitly describe admin-managed remote MCP hooks on the cloud orchestrator for dots. They explicitly exclude personal accounts and plugin/local-directory hooks in cloud orchestration. Installing a local Codex hook cannot enable this on a personal dot.

The lifecycle documentation describes `UserPromptSubmit` with `prompt`, and `Stop` with `last_assistant_message`; `turn_id` is described as Codex-specific. These are a reason to investigate completed-message capture for an eligible dot, not proof of the cloud dot payload contract. Do not enable workspace-wide capture or assume Codex transcript files are dot history. Account/workspace eligibility has not been established for this device.

An eligible administrator-reviewed experiment must first establish:

1. A dot-scoped policy and authenticated MCP receiver that excludes unrelated chats and subagents. Do not change global policy or grant new access without review.
2. Actual cloud payloads for a non-sensitive ChatGPT-origin prompt and its completed reply. Record only private, owner-approved test evidence; stable conversation/turn identifiers must come from the supported contract.
3. A companion-origin message reaching the same dot conversation through the existing event connection, followed by hook receipt and independent comparison in both interfaces. Tool activity alone does not prove identical visible transcripts.
4. Duplicate/out-of-order handling, disconnect/reconnect, a deliberately missed event, and documented recovery. Hook delivery errors can fail without blocking work; documentation says hooks are not a complete compliance audit trail. Lossless replay cannot be assumed.
5. Measured end-to-end delay. Completed-turn hooks do not establish token streaming. Older-history backfill and rich messages need separate documented access.

If the existing dot is personal, this candidate cannot run under the checked contract. The remaining consumer integration dependency is an OpenAI-supported, per-user dot channel with scoped message send/read, stable IDs, incoming-message subscription and replay/history access. Request access to that contract through an authorized provider contact before claiming a consumer sync product. No provider message has been sent and no external service enabled.

The package `@openai/mcp-extensions` 0.1.0 was inspected without installing or executing it. Its `modelContext.getCurrent()` reads the MCP App's `openai/modelContext` host state; `update()` updates that app context. Its message API sends a user message to the active or a new conversation. These APIs do not supply the missing outgoing dot transcript feed.

## Next implementation gates

1. Establish a reviewed distribution route and ordinary-user account availability. The private tunnel proof does not authorize a public backend, paid service or broader account scopes.
2. Define per-user transport authorization and protected credential storage for Windows and Mac. Keep renderer permissions narrow and Rust authoritative for desktop OS actions and privileges. The private Mac preview now uses an isolated persistent Python helper with fixed snapshot/send/retry operations behind Rust IPC. It is not a public cross-platform transport.
3. Harden the implemented private Mac text panel and actual reply bubbles, with explicit pending/error states and reconnect recovery. Show activity only for known relay requests. Do not label silence as idle or a delivered event as a completed response.
4. Validate the implemented opt-in snippets, dismissal and no-focus behavior on both operating systems. The preview retains only its own relay exchanges locally until removal; add consumer retention controls before public distribution.
5. Verify context and history limits, revoked access, duplicate events, offline operation and interrupted requests on real devices. Do not describe mailbox history as the complete ChatGPT transcript.
6. Complete Windows x64 and Mac device checks, accessibility, rendering budgets and signed update/recovery acceptance before a supported binary release.

## Capability limits still open

- **Dot image:** no third-party avatar export/access API was established. The launcher's local user-selected PNG remains available; do not scrape the appearance editor or ship personal art.
- **Global work/new-message state:** the proof can expose replies and pending requests in its own mailbox only. No unread counts or status across all dot activity.
- **Voice:** no authorized third-party existing-dot voice transport was established. No replacement API assistant or microphone capture was added.
- **iPhone:** the Shortcut recipe remains the minimum companion. No iPhone relay, native app or cross-app floating overlay was implemented.

## Sources rechecked on 4 October 2026

- [MCP Events](https://developers.openai.com/plugins/build/mcp-events): dots, subscription lifecycle, signed callback delivery.
- [Secure MCP Tunnels](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels): private transport, runtime credentials, workspace association, public distribution limits.
- [Connect and test a plugin](https://developers.openai.com/plugins/deploy/connect-chatgpt): developer-mode tunnel setup.
- [Message your dot](https://learn.chatgpt.com/docs/dots/channels): same dot across supported channels, with separate histories.
- [Sign in with ChatGPT](https://developers.openai.com/siwc/quickstart): identity and Responses access do not grant conversation access.
- [API conversation state](https://developers.openai.com/api/docs/guides/conversation-state): developer-managed state.
- [Codex App Server](https://learn.chatgpt.com/docs/app-server): Codex-thread semantics.
