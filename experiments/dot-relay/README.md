# Existing-dot transport proof

This is a single-user macOS experiment used by the private desktop preview and a headless CLI. **A real two-way exchange with the existing dot was demonstrated on 4 October 2026, and repeated after restarting the tunnel.** The dot independently confirmed both message IDs and replies from its event-run tool activity. No separate assistant or model call was used. This is a private transport proof, not a production backend. See the [live evidence and remaining limits](../../docs/TRANSPORT-PROOF.md). Synthetic unit fixtures are separate from that live evidence.

## What the CLI investigation established

Checked 4 October 2026:

- Installed `codex-cli 0.146.0`: command help and its generated, non-experimental App Server JSON schemas describe Codex agent threads, not the existing dot. No dot method was found. `codex exec resume` does not establish access to a ChatGPT dot.
- Official `tunnel-client v0.0.15` macOS arm64 binary downloaded and run locally. ZIP SHA-256 verified against the official release asset digest: `b2cae3aa9df45b4c2fe9b1d700ebacce39f9feb6a6b46b86e6499f9a51bf72ff`. Inspected `--help`, `help quickstart`, `help oauth`, `admin --help` and `doctor --help`.
- After the user's review, a private test tunnel was associated with the account's available ChatGPT workspace. The user entered a restricted Tunnels Read + Use runtime key with a one-day expiration through a hidden local prompt. The official client forwarded discovery and real dot tool calls successfully. Identifiers, key, callback secret and test messages remain outside the repository.
- Secure MCP Tunnel supports private developer-mode connections. It needs a tunnel ID, a separate runtime API key, appropriate Platform permissions and a ChatGPT workspace association. It does not use an extracted ChatGPT login/session token. Public plugin distribution still needs a reviewed public HTTPS service/proxy.
- MCP Events explicitly supports dots. This account's existing dot successfully subscribed, read two unique CLI challenges and returned the exact expected replies through the reply tool. The second exchange passed after a tunnel restart. This establishes the narrow relay on this account; it does not establish public account eligibility or access to all ChatGPT history.

## Tested real route

```text
local CLI queue → signed MCP event → existing dot
                                        ↓ calls read_test_message
local CLI read  ← reply_to_test_message ← actual dot response
```

Only the two listed tools and one event are exposed. The process offers no shell, filesystem browsing, account lookup, conversation export or model invocation. The event contains a mailbox/message ID; the read tool returns that specific test message. The reply tool can only answer an existing message and rejects conflicting duplicate replies. An acknowledged webhook is not counted as a reply or proof of dot identity.

The user approved the private connection test: a private tunnel associated with their account's workspace, a least-privilege runtime key and a developer-mode MCP connection to this stdio process. No public port, paid service, Responses API call or public plugin submission is proposed. Tunnel/account costs have not been established; stop if setup requires a charge or plan change. Never paste a key into chat or source. Key creation/entry stays with the user; the tunnel client supports a private secret file reference.

## Local verification commands

Python standard library only; no package installation is required. On this Mac:

```sh
python3 -m unittest discover -s experiments/dot-relay -p 'test_*.py' -v

NEAR_DOT_PROOF_STATE="$HOME/Library/Application Support/Near Dot/transport-proof"
python3 experiments/dot-relay/relay.py --state "$NEAR_DOT_PROOF_STATE" status
```

The explicit state directory is outside the repository. It is mode 0700, with a mode 0600 SQLite file. It stores only test messages/replies and the event subscription including its signing secret. This is an opt-in diagnostic mailbox, not production conversation storage. It is not encrypted at rest; use only non-sensitive test messages and remove the private proof state after disconnecting. The relay database never stores the runtime key. The connection helper stores it in a separate mode 0600 `runtime.key` file in the same private directory; only the official client reads it through a file reference. The current Windows relay has a separate per-user connection directory with owner-only ACL protection. Its installer bundles the pinned Python/tunnel runtime; setup and security tests run on Windows. Actual Windows dot exchange acceptance remains separate from these synthetic tests.

## Reproduce the approved private setup

For a new approved Mac test, create a restricted, short-lived runtime key in the official OpenAI form, then run this command in your own project terminal.

```sh
python3 experiments/dot-relay/connect.py key
```

Paste the key only at the hidden prompt. The helper refuses echoed/non-interactive input, creates a mode 0600 file outside the repository, and never prints or overwrites a key. Tell the operator only that the key is ready. `python3 experiments/dot-relay/connect.py status` reports presence flags without reading the key. The same wrapper supports `doctor` and `run` with `--client` pointing to the verified official binary; raw vendor diagnostics are suppressed. It reads private `connection.json` metadata containing a `tunnel_id`, prepared during setup. The `health` command reports only operational counters. Readiness alone does not prove successful discovery; observed requests and a real reply do.

Use the verified official tunnel client; do not reuse a Codex/ChatGPT token. The user provides the tunnel ID and runtime key **locally**, outside the repository. `NEAR_DOT_TUNNEL_KEY_FILE` refers to the user-created private key file, not its contents. Keep raw HTTP logging off and do not publish tunnel logs, profiles or support exports.

```sh
# Set NEAR_DOT_TUNNEL_ID and NEAR_DOT_TUNNEL_KEY_FILE locally; never in source.
# Set NEAR_DOT_TUNNEL_CLIENT to the verified official executable.
"$NEAR_DOT_TUNNEL_CLIENT" doctor \
  --control-plane.tunnel-id "$NEAR_DOT_TUNNEL_ID" \
  --control-plane.api-key "file:$NEAR_DOT_TUNNEL_KEY_FILE" \
  --mcp.command "python3 \"$PWD/experiments/dot-relay/relay.py\" --state \"$NEAR_DOT_PROOF_STATE\" serve" \
  --explain

"$NEAR_DOT_TUNNEL_CLIENT" run \
  --control-plane.tunnel-id "$NEAR_DOT_TUNNEL_ID" \
  --control-plane.api-key "file:$NEAR_DOT_TUNNEL_KEY_FILE" \
  --mcp.command "python3 \"$PWD/experiments/dot-relay/relay.py\" --state \"$NEAR_DOT_PROOF_STATE\" serve" \
  --health.listen-addr 127.0.0.1:0 --log.level warn --log.format json \
  --log.file "" --log.http-raw-unsafe=false
```

Connect this tunnel in ChatGPT Plugins after reviewing its discovered two tools and event. Attach it to the **existing dot**, then explicitly instruct the dot:

> First call `read_test_message` with `message_id` set to `connection-check` to verify access; it returns readiness only and creates no message. For this transport test, subscribe to `near_dot.message_created` with mailbox `near-dot-proof`. When it arrives, use `read_test_message` for its message ID, answer that non-sensitive test message, and return your answer using `reply_to_test_message` with the same ID. Do not include unrelated conversation history, credentials or account details. Use the connection deadline returned by `connection-check`. The initial grant is one hour; only the local owner can explicitly extend it. Refreshes and restarts cannot extend it. Stop after this test when I ask.

Once connected and subscribed, send a message and wait for its actual reply with one command:

```sh
python3 experiments/dot-relay/talk.py
```

The prompt accepts one non-sensitive message of up to 1,024 characters. The CLI prints the actual reply, or reports a pending request after 180 seconds. It sends only the selected message, leaving other queued drafts alone. To resume a pending request without creating another message:

```sh
python3 experiments/dot-relay/talk.py --resume "$NEAR_DOT_TEST_MESSAGE_ID"
```

A saved reply can be read offline. Interrupting the wait does not cancel an already delivered dot request. Keep CLI output private. The initial proof expires after one hour unless its owner explicitly extends it; restarts and subscription refreshes cannot extend it. The client process can remain running, but the relay refuses further message tool calls and subscriptions after the deadline.

For individual transport steps, queue a fresh non-sensitive challenge using stdin, not a command-line argument. Save the returned ID locally. Deliver only after status reports an active subscription:

```sh
python3 experiments/dot-relay/relay.py --state "$NEAR_DOT_PROOF_STATE" queue
# Type the unique test challenge, then Ctrl-D.
python3 experiments/dot-relay/relay.py --state "$NEAR_DOT_PROOF_STATE" deliver
python3 experiments/dot-relay/relay.py --state "$NEAR_DOT_PROOF_STATE" status
python3 experiments/dot-relay/relay.py --state "$NEAR_DOT_PROOF_STATE" read --message-id "$NEAR_DOT_TEST_MESSAGE_ID"
```

`read` prints the actual reply and is intentionally not a diagnostic log. Keep it private. Independently verify the existing dot received the same challenge and invoked the reply tool; a tool call alone does not prove which ChatGPT conversation called it. Repeat after restarting the relay/tunnel. Ask the dot to stop monitoring, verify unsubscribe, revoke the connection/key/tunnel, and remove local test state. Local `revoke` immediately removes the subscription but does not revoke the external key or tunnel.

## Limits and acceptance

- Twenty-four headless unit tests cover discovery, callback verification failure, exact-byte signatures, redirect handling, private-address rejection, expiry/unsubscribe, duplicate replies, persistence, offline retry IDs, targeted delivery, private key handling, redacted health output and offline reply retrieval.
- Callback URLs allow only HTTPS on port 443 under `openai.com` or `chatgpt.com`. Unknown callback hosts fail closed pending official verification. DNS is validated on every connection; the connection uses that IP with original TLS hostname verification. No redirects, private IPs or HTTP proxies.
- Single-user proof only: the tunnel's workspace/key permissions are its authentication boundary. Do not associate shared workspaces or expose stdio over a public unauthenticated server. A public product requires per-user authorization and a separate security review.
- One subscription, an initial one-hour owner-controlled deadline, no history replay cursor, no automatic retry loop. Secret rotation pauses delivery for five minutes; this experiment does not claim complete production MCP conformance. Manual retries preserve event IDs. Expired/revoked subscriptions block delivery. The CLI does not automatically delete message history.
- Live-tested on one Mac/account: tunnel forwarding/discovery, callback verification, real dot subscription, event-to-tool round trip, exact correlation, independent confirmation in the existing dot, and a second exchange after reconnect. Account revocation, event batching, other accounts, Windows and iPhone remain untested.
- This relay could synchronize only messages passing through it. It does not export prior ChatGPT history, unrelated dot replies, global task status, avatar or voice. Full conversation synchronization remains unresolved.
- The real exchange gate has passed for this private setup. The local development build now includes a private Mac conversation panel and reply bubble; no public distribution has been added. Public authentication, account availability and a reviewed deployment path remain separate gates.

## Official references

- [Codex App Server](https://learn.chatgpt.com/docs/app-server): Codex-thread semantics.
- [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels): private transport, permissions, credentials and public distribution boundary.
- [Official tunnel-client release](https://github.com/openai/tunnel-client/releases/tag/v0.0.15): checked binary.
- [Connect and test a plugin](https://developers.openai.com/plugins/deploy/connect-chatgpt): ChatGPT developer-mode tunnel setup.
- [MCP Events](https://developers.openai.com/plugins/build/mcp-events): dots, callback verification and subscription lifecycle.
- [Message your dot](https://learn.chatgpt.com/docs/dots/channels): supported channels and their separate histories.
- [Sign in with ChatGPT](https://developers.openai.com/siwc/quickstart): does not grant conversation access.

## Private desktop preview and explicit extension

The Tauri prerelease packages `desktop.py`, `relay.py` and `connect.py` as local resources. Rust starts a persistent isolated Python helper and exposes only snapshot/send/retry to the chat UI, with bounded input/output and redacted failures. It starts only the checksum-verified official tunnel client from the approved private setup. The desktop neither reads nor accepts runtime-key contents in its renderer. Windows source/review installers now provide guided per-user private setup through a native credential prompt, a bundled verified runtime, explicit disconnect and connection replacement. The Mac proof remains separate. Account authorization, dot subscription and Windows end-to-end acceptance are required; zero-authorization/public-plugin distribution remains outside this private flow.

The initial one-hour cap is a proof safeguard, not an OpenAI requirement. Only after an explicit local-owner request, extend the fixed window with:

```sh
python3 experiments/dot-relay/relay.py --state "$NEAR_DOT_PROOF_STATE" extend --hours 24
```

The value is bounded to 1–24 hours. This local operation does not change the key, its expiration, workspace association or permissions. No MCP method or renderer operation can call it. Subscribe/refresh/restart cannot extend the deadline themselves. The fixed-hour tests above still cover the initial default grant; the additional extension test verifies it is local-only.
