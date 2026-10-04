# Next phase: a companion for the real dot

Requirements: animate only when actual work or a new message is known; show a privacy-controlled message snippet; display the user's own dot image; offer text/voice conversation from the companion without browser navigation. The launcher alone cannot supply the first, second or fourth capability.

## Integration recheck — 4 October 2026

| Requirement                          | Evidence                                                                                                                                                                                    | Decision                                                                                             |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Open the real dot                    | A private address exposed by the visible ChatGPT browser UI reopened the same dot in a fresh signed-in tab and via the native launcher on one Mac                                           | Supported per-device after testing; this does not establish a stable public URL contract             |
| Working state and new-message events | Checked official dot documentation describes progress inside ChatGPT and connected contact methods; no public dot status/message subscription API established                               | No status polling, unread counts, fabricated activity or message snippets                            |
| Chat/voice inside Near Dot           | ChatGPT conversation/profile call controls and Slack/Teams contact methods are documented; no third-party embedded existing-dot chat/voice API established                                  | Browser remains the tested route; no website embedding or session-token access                       |
| Use the same image                   | OpenAI documents appearance customization, but the checked pages do not document a third-party avatar export/access API; the actual appearance editor inspected had no image export control | Local user-selected PNG supported; automatic image retrieval and profile synchronization unavailable |

[OpenAI messaging](https://learn.chatgpt.com/docs/dots/channels) says connected contact methods reach the same dot, while Slack/Teams show messages exchanged in that channel rather than mirroring all messages. Calls start in ChatGPT. An explicitly approved Slack/Teams adapter could be investigated, but needs account availability, public app registration, approved OAuth scopes, secure per-user credentials and a tested way to identify the connected dot. It would not establish full dot history or global working state. No channel has been connected by Near Dot.

[MCP Events](https://developers.openai.com/plugins/build/mcp-events) lets ChatGPT subscribe to events from a developer's MCP server and receives those events through callbacks. That direction does not export dot messages or task state to a desktop companion. A dot-instructed plugin relay would require separate design, authorization, service setup and evidence; this release does not implement one.

[API conversation state](https://developers.openai.com/api/docs/guides/conversation-state) describes developer-managed conversations. A separate API assistant could provide chat, voice and events for its own work, but would have its own identity, history, memory, app permissions and API usage costs. Explicit scope approval is required; calling it the user's existing dot would be misleading.

## Acceptance before live functionality

1. Establish a current documented integration that reaches the user's real dot, with permissions available to ordinary public users.
2. Verify authorized event delivery, task-state meaning, account/channel identity and behavior while signed out/offline. Do not infer that silence means idle.
3. Show snippets only after opt-in, with a hide-content option, dismissal and no focus stealing. Keep messages out of diagnostics and default persistence.
4. Verify text/voice reaches the same dot with correct permissions, cancellation, permission prompts and costs; never silently substitute an API assistant.
5. Test real Windows and Mac interaction, rendering budgets, hidden animation, keyboard/screen-reader access and genuine updates from the chosen integration.

The source preview is a launcher with local image customization. It does not claim these live features are implemented.
