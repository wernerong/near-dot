# Existing-dot transport evidence

Verified 4 October 2026 on one Mac/account: real two-way messages reached the existing dot through the official private MCP route and returned to the native companion. This establishes the private connection, not full ChatGPT transcript synchronization or public distribution.

## Route and provenance

```text
Native composer / CLI → local mailbox → signed MCP event → existing dot
                                                             ↓ read_test_message
Native reply bubble  ← local mailbox ← reply_to_test_message ← answer
```

Official `tunnel-client v0.0.15` forwards MCP requests to a local Python stdio process. Setup used a private developer-mode plugin, a separately entered restricted Tunnels Read + Use key, and successful callback challenge verification. The dot explicitly subscribed to one event. No separate API assistant or browser transport carries messages.

The browser was used for initial setup and an independent origin check. The existing dot reported the matching message IDs and replies from its tool activity without being supplied those expected values in the audit prompt. `origin_attested_by_transport: false` remains intentional: a tool call does not cryptographically attest a particular ChatGPT conversation. The separate observation establishes origin for this tested setup, not a universal identity guarantee.

## Observed evidence

| Check | Result |
| --- | --- |
| Discovery and callback verification | Plugin exposed exactly two intended tools and one event; real requests and a subscription succeeded. |
| Unique CLI challenges | Two fresh reversal challenges returned exact expected answers; the second passed after a tunnel restart. |
| Conversation continuity | A third message introduced a non-sensitive codeword. A fourth asked for it without repeating its value or message ID; the actual reply recalled it. One measured reply took approximately 31 seconds, not a latency guarantee. |
| Native desktop messaging | Four additional messages received real tool replies. A post-expiry request needed the owner's extension and a refreshed dot workflow before it completed. |
| Automatic incoming bubble | After that refresh, a new composer message received a reply without another browser instruction. The OS reported the bubble visible, its accessible badge appeared, and the companion retained focus. Clicking the bubble reopened Chat. |
| Persistence and process lifecycle | Saved relay history and a locally imported PNG survived restart. The installed unsigned app reconnected on launch; Quit stopped the app and its owned client. |
| Deadline ownership | Reconnect/refresh preserve the fixed deadline. The local owner explicitly extended the initial one-hour grant to 24 hours; key permissions and independent expiration were unchanged. |
| Private records | Keys, callback secrets, private identifiers, actual text and personal screenshots remain outside public source/releases. |

Eight messages had eight real tool replies at completion. Synthetic unit fixtures and browser previews are not counted in this evidence. The image is a one-time local import, not automatic synchronization.

## Reproduce on an authorized test Mac

Follow the [private setup instructions](../experiments/dot-relay/README.md). Launch the desktop app, click the companion, send a non-sensitive message and close Chat to observe the incoming bubble. Enable snippet display in Settings only if desired. The app starts the verified client from the existing setup; do not run a second client simultaneously.

Alternatively, with the desktop app quit, run the CLI client in one terminal and message helper in another:

```sh
python3 experiments/dot-relay/connect.py run --client "$NEAR_DOT_TUNNEL_CLIENT"
python3 experiments/dot-relay/talk.py
# Resume the same pending message; do not create a duplicate:
python3 experiments/dot-relay/talk.py --resume "$NEAR_DOT_TEST_MESSAGE_ID"
```

The local mailbox is not encrypted. Keep command output private. Local `revoke` removes the subscription only; retire the external plugin/tunnel/key through official account controls, then remove local records. Restarting does not renew either deadline.

## Remaining boundaries

- The mailbox retains only exchanges passing through it. Prior ChatGPT history and unrelated replies are not synchronized. One recall test does not guarantee shared memory.
- Pending means a local message awaits a reply; it is not global dot work status or an unread count.
- Public account eligibility, per-user authorization and a reviewed public deployment route remain unresolved. No public backend or plugin submission was created.
- Windows transport and credential ACLs, iPhone chat, automatic avatar sync, voice, streaming, cancellation and unsolicited replies are unavailable or unproven.
- One subscription, no history cursor, no automatic delivery retry, no live account-revocation test, and a five-minute pause on secret rotation limit reliability. This is not complete production MCP conformance.

## Official basis

Checked during integration investigation:

- [Secure MCP Tunnels](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels): authorized private forwarding and distribution boundary.
- [MCP Events](https://developers.openai.com/plugins/build/mcp-events): dot subscriptions, signed callbacks and event lifecycle.
- [Connect and test a plugin](https://developers.openai.com/plugins/deploy/connect-chatgpt): developer-mode setup and discovery.
- [Official tunnel-client v0.0.15](https://github.com/openai/tunnel-client/releases/tag/v0.0.15): pinned tested client.
- [Message your dot](https://learn.chatgpt.com/docs/dots/channels): supported channels and separate histories.
