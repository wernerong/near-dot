import { bindAppearance } from "./appearance";
import { call, on, preview } from "./platform";
import type { Avatar, ChatSnapshot } from "./types";
const el = <T extends HTMLElement = HTMLElement>(id: string) =>
  document.getElementById(id) as T;
const failure = (e: unknown) =>
  typeof e === "string"
    ? e
    : e instanceof Error
      ? e.message
      : "The connection could not complete.";

export async function chatUI() {
  document.body.className = "chat-window";
  el("app").innerHTML = `<main class="chat-shell">
    <header class="chat-header"><button id="chat-avatar-button" class="avatar-button" aria-label="Choose your dot image" title="Choose your dot image"><img id="chat-avatar" src="/companion.svg" alt="Your companion image"></button><div><h1>Your dot</h1><p id="connection-state" role="status">Connecting…</p></div><button id="chat-settings" class="text-button" aria-label="Chat settings">⚙</button><button id="chat-close" class="text-button" aria-label="Close chat">×</button></header>
    <p class="chat-boundary" id="chat-boundary">Private preview · Messages sent here stay in this relay’s history.</p>
    <div id="chat-messages" class="chat-messages" role="log" aria-label="Conversation with your dot" aria-live="polite" aria-relevant="additions text"></div>
    <p id="chat-error" class="chat-error" role="alert" hidden></p>
    <form id="chat-form" class="chat-form"><label class="sr-only" for="message">Message your dot</label><textarea id="message" rows="2" maxlength="1024" placeholder="Message your dot…" aria-describedby="composer-help"></textarea><div class="composer-footer"><span id="composer-help">Enter to send · Shift + Enter for a new line</span><button id="send-message" type="submit" disabled>Send ↑</button></div></form>
    <footer class="chat-footer"><span id="chat-expiry">Checking private connection…</span><button id="chat-setup" class="text-button">Connect my dot</button><button id="chat-reconnect" class="text-button">Reconnect</button><button id="chat-browser" class="text-button">Open ChatGPT ↗</button></footer>
    <dialog id="connection-setup"><h2>Connect this device to your dot</h2><p>Near Dot includes the local runtime. Your Mac and Windows connections are separate. Authorize this device using your own OpenAI account.</p><ol><li><button class="text-button" id="setup-tunnels">Create a private tunnel ↗</button> in your linked OpenAI workspace.</li><li><button class="text-button" id="setup-keys">Create a runtime key ↗</button> with Tunnels Read + Use permission. Enter it only in the native prompt below.</li><li><button class="text-button" id="setup-configure">Enter my connection</button>. The native prompt asks for your tunnel ID and runtime key; both stay on this computer.</li><li><button class="text-button" id="setup-plugins">Connect your MCP plugin ↗</button> using that tunnel, enable it for your dot, and ask your dot to subscribe to near_dot.message_created with mailbox near-dot-proof. On each event, read_test_message reads the message ID and reply_to_test_message returns the answer here.</li></ol><p>Your workspace must allow custom MCP plugins and dots. Sign-in alone cannot authorize this connection. Live messaging stays enabled until you disconnect or revoke the key. This keeps exchanges sent through Near Dot; it does not import ChatGPT history.</p><p id="setup-status" role="status"></p><div class="update-buttons"><button class="text-button" id="setup-guide">Official setup guide ↗</button><button class="text-button" id="setup-disconnect">Disconnect this device</button><button class="text-button" id="setup-forget">Forget connection</button><button id="setup-close">Done</button></div></dialog>
  </main>`;
  let current: ChatSnapshot = {
    connected: false,
    state: "unconfigured",
    expiresIn: null,
    messages: [],
  };
  let busy = false;
  let signature = "";
  const message = el<HTMLTextAreaElement>("message");
  const error = (text = "") => {
    el("chat-error").textContent = text;
    el("chat-error").hidden = !text;
  };
  const availability = () => {
    el<HTMLButtonElement>("send-message").disabled =
      busy || !current.connected || !message.value.trim();
  };
  const apply = (snapshot: ChatSnapshot) => {
    current = snapshot;
    const interfaceOnly = snapshot.state === "interface-only";
    el("connection-state").textContent = snapshot.connected
      ? "Connected to your dot"
      : interfaceOnly
        ? "Chat is not connected"
        : snapshot.state === "expired"
          ? "Connection expired"
          : "Connection unavailable";
    el("connection-state").classList.toggle("is-connected", snapshot.connected);
    el("chat-boundary").textContent = interfaceOnly
      ? "Chat interface · Live messaging is not connected on this device."
      : "Private preview · Messages sent here stay in this relay’s history.";
    el<HTMLButtonElement>("chat-reconnect").disabled = interfaceOnly;
    el<HTMLButtonElement>("chat-setup").hidden = interfaceOnly;
    el("chat-reconnect").hidden = snapshot.state === "unconfigured";
    if (snapshot.state === "awaiting-dot")
      el("connection-state").textContent = "Waiting for your dot to connect";
    if (snapshot.state === "paused")
      el("connection-state").textContent = "Disconnected on this device";
    el("chat-expiry").textContent = preview
      ? "Browser preview · sending unavailable"
      : interfaceOnly
        ? "Open ChatGPT to message your dot"
        : snapshot.expiresIn
          ? `Private session · ${Math.ceil(snapshot.expiresIn / 60)} min left`
          : snapshot.connected
            ? "Live connection on this device"
            : "Connect this device to send";
    // Connection changes enable retry controls; crossing the wait threshold updates
    // status without repainting the live region on every poll.
    const next = JSON.stringify([
      snapshot.connected,
      snapshot.state,
      snapshot.messages,
      snapshot.messages.map(
        (item) => item.reply === null && Date.now() / 1000 - item.created > 180,
      ),
    ]);
    if (next !== signature) {
      signature = next;
      const list = el("chat-messages");
      const nearBottom =
        list.scrollHeight - list.scrollTop - list.clientHeight < 80;
      list.replaceChildren();
      if (!snapshot.messages.length) {
        const empty = document.createElement("div");
        empty.className = "chat-empty";
        const heading = document.createElement("h2");
        heading.textContent = "A little closer.";
        const note = document.createElement("p");
        note.textContent = snapshot.connected
          ? "Send a message to the dot you already know."
          : interfaceOnly
            ? "Your chat space is ready. Use Open ChatGPT to send messages until a connection is configured on this device."
            : "Your private connection needs to be running before you can send. Saved replies remain available.";
        empty.append(heading, note);
        list.append(empty);
      }
      for (const item of snapshot.messages) {
        const outgoing = document.createElement("p");
        outgoing.className = "chat-message outgoing";
        outgoing.textContent = item.text;
        outgoing.setAttribute("aria-label", `You: ${item.text}`);
        list.append(outgoing);
        if (item.reply !== null) {
          const incoming = document.createElement("p");
          incoming.className = "chat-message incoming";
          incoming.textContent = item.reply;
          incoming.setAttribute("aria-label", `Your dot: ${item.reply}`);
          list.append(incoming);
        } else {
          const status = document.createElement("div");
          status.className = "message-delivery";
          status.textContent =
            item.delivered === 2
              ? "Delivery rejected."
              : item.delivered === 0
                ? "Saved locally · not delivered"
                : Date.now() / 1000 - item.created > 180
                  ? "Taking longer than usual. Still waiting for a reply."
                  : "Waiting for your dot’s reply…";
          if (item.delivered === 0) {
            const retry = document.createElement("button");
            retry.type = "button";
            retry.className = "text-button";
            retry.textContent = "Retry delivery";
            retry.disabled = !snapshot.connected;
            retry.onclick = async () => {
              retry.disabled = true;
              try {
                apply(
                  await call<ChatSnapshot>("retry_chat", {
                    messageId: item.id,
                  }),
                );
                error();
              } catch (e) {
                error(failure(e));
                retry.disabled = !current.connected;
              }
            };
            status.append(retry);
          }
          list.append(status);
        }
      }
      if (nearBottom) list.scrollTop = list.scrollHeight;
    }
    availability();
  };
  const avatar = (value: Avatar) => {
    el<HTMLImageElement>("chat-avatar").src = value.dataUrl || "/companion.svg";
  };
  avatar(await call<Avatar>("get_avatar"));
  await on<Avatar>("avatar-changed", avatar);
  await on<ChatSnapshot>("chat-state", apply);
  apply(await call<ChatSnapshot>("get_chat"));
  el("chat-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (busy || !current.connected || !message.value.trim()) return;
    const text = message.value;
    busy = true;
    availability();
    error();
    try {
      const snapshot = await call<ChatSnapshot>("send_chat", { text });
      if (message.value === text) message.value = "";
      apply(snapshot);
      el("chat-messages").scrollTop = el("chat-messages").scrollHeight;
    } catch (e) {
      error(failure(e));
    } finally {
      busy = false;
      availability();
      message.focus();
    }
  });
  message.addEventListener("input", availability);
  message.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      el<HTMLFormElement>("chat-form").requestSubmit();
    }
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !document.querySelector("dialog[open]"))
      void call("companion_action", { action: "close-chat" }).catch((e) =>
        error(failure(e)),
      );
  });
  await on("chat-focus", () => message.focus());
  for (const [id, action] of [
    ["chat-settings", "settings"],
    ["chat-close", "close-chat"],
  ])
    el(id).onclick = () =>
      void call("companion_action", { action }).catch((e) => error(failure(e)));
  el("chat-reconnect").onclick = async () => {
    const reconnect = el<HTMLButtonElement>("chat-reconnect");
    reconnect.disabled = true;
    error();
    el("connection-state").textContent = "Reconnecting…";
    try {
      await call("connect_chat");
      apply(await call<ChatSnapshot>("get_chat"));
    } catch (e) {
      apply(current);
      error(failure(e));
    } finally {
      reconnect.disabled = false;
    }
  };
  el("chat-browser").onclick = () =>
    void call("open_destination").catch((e) => error(failure(e)));
  const setup = el<HTMLDialogElement>("connection-setup");
  el("chat-setup").onclick = () => setup.showModal();
  el("setup-close").onclick = () => setup.close();
  for (const action of [
    "tunnels",
    "keys",
    "configure",
    "plugins",
    "guide",
    "disconnect",
    "forget",
  ]) {
    el(`setup-${action}`).onclick = async () => {
      const button = el<HTMLButtonElement>(`setup-${action}`);
      button.disabled = true;
      el("setup-status").textContent =
        action === "configure"
          ? "Enter your connection in the native prompt…"
          : "";
      try {
        await call("chat_setup", { action });
        apply(await call<ChatSnapshot>("get_chat"));
        if (action === "configure")
          el("setup-status").textContent =
            "Local connection saved. Connect the plugin and subscription in step 4.";
        if (action === "forget")
          el("setup-status").textContent =
            "Connection credentials removed. Saved messages remain here. Revoke the old key in OpenAI settings, then enter a new connection.";
        if (action === "disconnect")
          el("setup-status").textContent =
            "Disconnected. Saved messages remain on this device. Reconnect resumes your connection.";
      } catch (e) {
        el("setup-status").textContent = failure(e);
      } finally {
        button.disabled = false;
      }
    };
  }
  bindAppearance(el("chat-avatar-button"), avatar);
}

export async function bubbleUI() {
  document.body.className = "bubble-window";
  el("app").innerHTML =
    `<aside class="reply-bubble" aria-label="Reply from your dot"><button id="bubble-open" class="bubble-open"><strong>Your dot replied</strong><span id="bubble-text">Click to read and respond.</span></button><button id="bubble-dismiss" class="bubble-dismiss" aria-label="Dismiss reply">×</button></aside>`;
  await on<{ text: string }>("reply-preview", (value) => {
    el("bubble-text").textContent = value.text;
  });
  el("bubble-open").onclick = () =>
    void call("companion_action", { action: "chat" });
  el("bubble-dismiss").onclick = () =>
    void call("companion_action", { action: "dismiss-reply" });
}
