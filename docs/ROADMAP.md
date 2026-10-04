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

The tested route is local message → signed subscribed event → existing dot read tool → existing dot reply tool → local reply. The browser was used for setup and independent verification, not to carry test messages. An acknowledged webhook was never counted as a reply. The original dot independently reported the first two exact message IDs and replies from its tool activity without being given those values in the audit prompt.

The relay can store and retrieve its own exchanges. One successful recall demonstrates continuity in the tested setup; it does not establish reliable access to every previous ChatGPT message or full shared memory. Keep those claims separate.

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
