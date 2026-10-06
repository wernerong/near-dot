import "./style.css";
import { chatUI, bubbleUI } from "./chat";
import { call, on, preview } from "./platform";
import { destinationError, shouldDrag } from "./validation";
import type {
  Avatar,
  Companion,
  Preferences,
  Snapshot,
  UpdateStatus,
} from "./types";

const root = document.querySelector<HTMLElement>("#app")!;
const companion =
  new URLSearchParams(location.search).get("view") === "companion";
const element = <T extends HTMLElement = HTMLElement>(id: string) =>
  document.getElementById(id) as T;
const errorText = (error: unknown) =>
  typeof error === "string"
    ? error
    : error instanceof Error
      ? error.message
      : "The action could not complete.";

async function bindAvatar(id: string) {
  const apply = (avatar: Avatar) => {
    const image = element<HTMLImageElement>(id);
    image.src = avatar.dataUrl || "/companion.svg";
    image.alt = avatar.dataUrl
      ? "Your local companion image"
      : "Original green seed companion";
    const notice = document.getElementById("avatar-status");
    if (notice)
      notice.textContent =
        avatar.warning ||
        (avatar.dataUrl
          ? "Your image stays on this device. It is not synced with ChatGPT."
          : "Default artwork. Choose your own dot image to personalize this device.");
  };
  apply(await call<Avatar>("get_avatar"));
  await on<Avatar>("avatar-changed", apply);
  return apply;
}

async function companionUI() {
  document.body.className = "companion-window";
  root.innerHTML = `<section class="companion" aria-label="Near Dot companion">
    <button id="drag" class="drag-grip" aria-label="Drag companion" title="Drag to move">⠿</button>
    <button id="pet" class="pet" aria-label="Chat with my dot" title="Chat with my dot"><img id="companion-image" src="/companion.svg" alt="" draggable="false"></button>
    <button id="open-label" class="open-label">Chat with my dot <span aria-hidden="true">↗</span></button>
    <button id="pet-reply" class="pet-reply" aria-label="Show latest reply" title="Show latest reply">···</button><button id="pet-settings" class="pet-settings" aria-label="Open settings" title="Settings">⚙</button>
    <span id="floating-status" class="sr-only" role="status"></span>
    <p id="pet-error" class="pet-error" role="status"></p>
  </section>`;
  let config: Companion;
  const apply = (p: Companion) => {
    config = p;
    element("floating-status").textContent = p.alwaysOnTop
      ? "Always on top enabled"
      : "Always on top disabled";
    root.style.opacity = String(p.opacity);
    root.classList.toggle("paused", p.paused || p.hidden || document.hidden);
    const action = p.chatEnabled ? "Chat with my dot" : "Open my dot";
    element("open-label").firstChild!.textContent = `${action} `;
    element("pet").setAttribute("aria-label", action);
    element("pet").title = action;
    element("pet-reply").hidden = !p.chatEnabled;
  };
  apply(await call<Companion>("get_companion"));
  await bindAvatar("companion-image");
  await on<Companion>("companion-config", apply);
  await on<boolean>("reply-available", (available) => {
    const button = element("pet-reply");
    button.textContent = available ? "●" : "···";
    button.setAttribute(
      "aria-label",
      available ? "Read new reply" : "Show latest reply",
    );
    button.title = available ? "Read new reply" : "Show latest reply";
    button.classList.toggle("has-reply", available);
  });
  await on<{ pending: boolean; connected: boolean }>(
    "chat-indicator",
    (status) => {
      root.classList.toggle("awaiting-reply", status.pending);
      element("pet").title = status.pending
        ? "Waiting for your dot’s reply"
        : config.chatEnabled
          ? "Chat with my dot"
          : "Open my dot";
    },
  );
  document.addEventListener("visibilitychange", () => apply(config));
  const open = async () => {
    try {
      await call("companion_action", { action: "activate" });
    } catch (e) {
      element("pet-error").textContent = errorText(e);
    }
  };
  let origin: [number, number] | null = null,
    dragged = false;
  const pet = element("pet");
  pet.addEventListener("pointerdown", (e) => {
    if (e.button === 0) {
      origin = [e.clientX, e.clientY];
      dragged = false;
    }
  });
  pet.addEventListener("pointermove", async (e) => {
    if (origin && e.buttons & 1 && shouldDrag(origin, [e.clientX, e.clientY])) {
      origin = null;
      dragged = true;
      try {
        await call("companion_action", { action: "drag" });
        await call("companion_action", { action: "drag-finished" });
      } catch (e) {
        element("pet-error").textContent = errorText(e);
      }
    }
  });
  pet.addEventListener("click", () => {
    origin = null;
    if (!dragged) void open();
    dragged = false;
  });
  element("open-label").addEventListener("click", () => void open());
  element("drag").addEventListener("pointerdown", async (e) => {
    if (e.button !== 0) return;
    try {
      await call("companion_action", { action: "drag" });
      await call("companion_action", { action: "drag-finished" });
    } catch (err) {
      element("pet-error").textContent = errorText(err);
    }
  });
  element("pet-settings").addEventListener(
    "click",
    () => void call("companion_action", { action: "settings" }),
  );
  element("pet-reply").addEventListener(
    "click",
    () => void call("companion_action", { action: "latest-reply" }),
  );
  root.addEventListener("contextmenu", (e) => {
    e.preventDefault();
    void call("companion_action", { action: "settings" });
  });
}

async function settingsUI() {
  root.innerHTML = `<div class="settings-shell">
    <header><a class="wordmark" href="#app"><span class="brand-mark" aria-hidden="true">◒</span> near dot</a><span class="pill">LOCAL LAUNCHER</span></header>
    <div id="preview-note" class="preview-note" hidden>Browser preview • OS launching and updates are unavailable.</div>
    <section class="hero"><div><p class="eyebrow">A LITTLE CLOSER</p><h1>Your dot.<br>One click away.</h1><p class="intro">A quiet companion that opens the dot<br>you already know.</p></div><div class="hero-art"><img id="hero-image" src="/companion.svg" alt="Original green seed companion"><span class="art-caption">Meet your little shortcut.</span></div></section>
    <p id="warning" class="warning" role="alert" hidden></p>
    <section id="setup-guide" class="setup-guide" aria-label="First-run setup" hidden>
      <h2 id="setup-title" tabindex="-1">Welcome to Near Dot</h2><p>Set up this device once. Your choices survive restarts and upgrades.</p>
      <ol class="setup-steps"><li id="step-link">1 · Test your link</li><li id="step-look">2 · Make it yours</li><li id="step-updates">3 · Updates &amp; finish</li></ol>
    </section>
    <p class="scope-notice">This public preview opens your existing dot in your browser. Desktop chat, live ChatGPT replies and shared conversation history are not available.</p>
    <form id="preferences" novalidate>
      <section class="card" id="setup-link"><div class="section-heading"><span class="step">01</span><div><h2>Where should we take you?</h2><p>Open your dot in ChatGPT on the web and copy its address bar. Use a link that reopens the same dot, not a public Share link. Sign in to your own ChatGPT account if prompted.</p></div></div>
        <label for="destination">Your destination</label><div class="link-row"><input id="destination" type="url" spellcheck="false" autocomplete="off" placeholder="Paste your own HTTPS conversation link" aria-describedby="destination-help"><button type="button" id="test-link" class="secondary">Test link ↗</button></div>
        <p id="destination-help" class="help">Only chatgpt.com HTTPS links. A copied link is not a guaranteed dot integration.</p>
        <label class="check"><input id="verified" type="checkbox"><span>I tested this link on this device and it opened my existing dot.</span></label>
        <div class="card-footer"><span>No new account. No API billing.</span><button type="button" id="open" class="text-button">Open my dot ↗</button></div>
      </section>
      <section class="card" id="setup-look"><div class="section-heading"><span class="step">02</span><div><h2>Make yourself comfortable</h2><p>A small presence. Your preferred way in.</p></div></div>
        <div id="private-controls" hidden><div class="update-buttons"><button type="button" id="open-chat" class="secondary">Chat with my dot</button></div><label class="check"><input type="checkbox" id="replyPreview"><span>Show message text in desktop reply bubbles</span></label><p id="chat-controls-help" class="help">Private development build. This connection expires and keeps its own exchanges; it does not sync ChatGPT history. Anyone looking at your screen can see enabled previews.</p></div><div class="avatar-controls"><h3>Your companion image</h3><p class="help">Use your existing pet or a different icon. Choose a still PNG up to 1024 × 1024 and 4 MiB, or import a downloaded PNG pet sheet up to 20 MiB. Only use artwork you have permission to use.</p><div class="update-buttons"><button type="button" id="choose-avatar" class="secondary">Choose local image</button><button type="button" id="import-pet" class="secondary">Import pet sprite sheet</button><button type="button" id="reset-avatar" class="text-button">Restore default image</button></div><p class="help">Download your pet in ChatGPT → Settings → Personalization → Pet. Import extracts the original first idle frame from 1536 × 1872 or 1536 × 2288 sheets; no account connection or automatic sync.</p><p id="avatar-status" class="help" role="status"></p><p class="help">Idle movement is decorative. A waiting indicator refers only to a message sent through this companion, not all dot activity.</p></div>
        <div class="two-col"><div><label for="shortcut">Global shortcut</label><input id="shortcut" type="text" spellcheck="false" aria-describedby="shortcut-help"><p id="shortcut-help" class="help">CommandOrControl+Shift+D · leave blank to disable.</p></div><div class="ranges"><label for="size">Size <output id="size-value"></output></label><input id="size" type="range" min="120" max="240" step="4"><label for="opacity">Opacity <output id="opacity-value"></output></label><input id="opacity" type="range" min="0.35" max="1" step="0.05"></div></div>
        <div class="checks-grid"><label class="check"><input type="checkbox" id="alwaysOnTop"><span>Always on top</span></label><label class="check"><input type="checkbox" id="paused"><span>Pause animation</span></label><label class="check"><input type="checkbox" id="startup"><span>Start at login</span></label><span class="help">Always on top keeps the companion above other app windows and follows Mac Spaces. Login startup is optional.</span></div>
        <div class="card-footer"><button type="button" id="toggle" class="text-button">Hide / show companion</button><button type="button" id="recover" class="text-button">Reset position</button></div>
      </section>
      <section class="card" id="setup-updates"><div class="section-heading"><span class="step">03</span><div><h2>Stay up to date</h2><p>Signed updates. You decide when to install.</p></div></div>
        <div class="two-col update-controls"><label class="check"><input type="checkbox" id="autoCheck"><span>Check automatically every 6 hours</span></label><div><label class="channel-label" for="channel">Channel</label><select id="channel"><option value="stable">Stable</option><option value="preview">Preview</option></select></div></div>
        <p id="update-status" class="help" role="status">Checking release configuration…</p><pre id="release-notes" hidden></pre><progress id="update-progress" max="100" hidden aria-label="Update download progress"></progress>
        <div class="update-buttons"><button id="check-update" type="button" class="secondary">Check for updates</button><button id="install-update" type="button" hidden>Install update</button><button id="restart" type="button" hidden>Restart companion</button><button id="defer" type="button" class="text-button" hidden>Later</button><button id="skip" type="button" class="text-button" hidden>Skip this version</button></div>
        <p class="help">Installation may close this companion and ask for OS approval. Save your settings first.</p>
        <label class="check"><input type="checkbox" id="unattendedNextLaunch"><span>Install an eligible update at my next manual launch, then restart the companion.</span></label><p class="help">One-time opt-in: checks and installs before the companion appears. Never installs during login startup or while the companion is running. OS approval may still be required. Launch with --no-unattended to bypass this attempt. Installer behavior still requires release testing.</p>
      </section>
      <div class="save-bar"><p id="status" role="status" aria-live="polite">Your link and preferences stay on this device.</p><div class="setup-navigation"><button id="setup-back" type="button" class="secondary" hidden>Back</button><button id="setup-next" type="button" hidden>Continue →</button><button type="submit" id="save">Save settings <span aria-hidden="true">→</span></button></div></div>
    </form>
    <details class="iphone"><summary>Take the shortcut to your iPhone <span aria-hidden="true">↗</span></summary><p>In Apple Shortcuts, create a shortcut with <strong>Open App → ChatGPT</strong>. Name it <strong>Open ChatGPT</strong>, then add it to your Home Screen or a Shortcuts widget. Open your dot inside the app.</p><p>Use an exact URL only after it opens your dot in the installed, supported ChatGPT app on your actual iPhone. Mobile Safari does not support dots. This path is untested on iPhone here.</p></details>
    <footer><p>Independent project. Not affiliated with or endorsed by OpenAI.<br>No telemetry or global dot status tracking. Private chat preview keeps its own exchanges locally.</p><div><span id="version"></span><button id="reset-settings" class="text-button">Reset local settings</button><button id="quit" class="text-button">Quit</button></div></footer>
  </div>`;
  element("preview-note").hidden = !preview;
  const snapshot = await call<Snapshot>("get_preferences");
  let saved = snapshot.preferences;
  let guided = snapshot.setupRequired;
  let setupStep = 0;
  let update: UpdateStatus | null = null;
  let testedLink = saved.verified ? saved.destination : "";
  const input = (id: string) => element<HTMLInputElement>(id);
  const status = (text: string, error = false) => {
    element("status").textContent = text;
    element("status").classList.toggle("error", error);
  };
  const applyAvatar = await bindAvatar("hero-image");
  element("private-controls").hidden = !snapshot.chatEnabled;
  if (snapshot.chatEnabled && !snapshot.chatTransportEnabled) {
    root.querySelector(".scope-notice")!.textContent =
      "The desktop chat interface is available. Live messaging is not connected on this device; use Open ChatGPT to send messages.";
    element("chat-controls-help").textContent =
      "Live messaging is not connected on this device. Reply bubbles need a connected relay; ChatGPT history is not synced.";
    input("replyPreview").disabled = true;
  } else if (snapshot.chatEnabled)
    root.querySelector(".scope-notice")!.textContent =
      "Private development build: connected relay exchanges stay local. ChatGPT history sync is unavailable and the connection expires.";
  function guide(focus = false) {
    element("setup-guide").hidden = !guided;
    element("setup-title").textContent = [
      "Welcome to Near Dot",
      "Make your companion yours",
      "Updates and you’re ready",
    ][setupStep];
    ["link", "look", "updates"].forEach((name, i) => {
      element(`setup-${name}`).hidden = guided && setupStep !== i;
      element(`step-${name}`).setAttribute(
        "aria-current",
        setupStep === i ? "step" : "false",
      );
    });
    element("setup-back").hidden = !guided || setupStep === 0;
    element("setup-next").hidden = !guided || setupStep === 2;
    element("save").hidden = guided && setupStep !== 2;
    element("save").textContent = guided ? "Finish setup →" : "Save settings →";
    if (focus) element("setup-title").focus();
  }
  guide();
  element("open-chat").addEventListener(
    "click",
    () =>
      void call("companion_action", { action: "chat" }).catch((e) =>
        status(errorText(e), true),
      ),
  );
  for (const [id, command] of [
    ["choose-avatar", "import_avatar"],
    ["import-pet", "import_avatar"],
    ["reset-avatar", "reset_avatar"],
  ]) {
    element(id).addEventListener("click", async () => {
      for (const button of ["choose-avatar", "import-pet", "reset-avatar"])
        element<HTMLButtonElement>(button).disabled = true;
      try {
        applyAvatar(
          await call<Avatar>(
            command,
            command === "import_avatar"
              ? { kind: id === "import-pet" ? "pet" : "image" }
              : undefined,
          ),
        );
        status(
          command === "reset_avatar"
            ? "Default image restored. Your previous image is preserved locally."
            : "Image selection complete. Your image stays on this device.",
        );
      } catch (e) {
        status(errorText(e), true);
      } finally {
        for (const button of ["choose-avatar", "import-pet", "reset-avatar"])
          element<HTMLButtonElement>(button).disabled = false;
      }
    });
  }
  const fields = [
    "alwaysOnTop",
    "paused",
    "replyPreview",
    "startup",
    "autoCheck",
    "verified",
    "unattendedNextLaunch",
  ] as const;
  function fill(p: Preferences) {
    input("destination").value = p.destination;
    input("shortcut").value = p.shortcut;
    input("size").value = String(p.size);
    input("opacity").value = String(p.opacity);
    element<HTMLSelectElement>("channel").value = p.channel;
    for (const id of fields) input(id).checked = p[id];
    labels();
  }
  function labels() {
    element("size-value").textContent = `${input("size").value}px`;
    element("opacity-value").textContent =
      `${Math.round(Number(input("opacity").value) * 100)}%`;
  }
  function collect(): Preferences {
    return {
      ...saved,
      destination: input("destination").value.trim(),
      shortcut: input("shortcut").value.trim(),
      size: Number(input("size").value),
      opacity: Number(input("opacity").value),
      channel: element<HTMLSelectElement>("channel").value,
      ...Object.fromEntries(fields.map((id) => [id, input(id).checked])),
      setupCompleted: saved.setupCompleted && input("verified").checked,
    };
  }
  fill(saved);
  element("warning").hidden = !snapshot.warning;
  element("warning").textContent = snapshot.warning;
  element("version").textContent = `v${snapshot.version}`;
  element("update-status").textContent = snapshot.updatesConfigured
    ? "Automatic checks start after 30 seconds. You control installation."
    : "Development build: updates await release signing and a reviewed public feed.";
  input("size").addEventListener("input", labels);
  input("opacity").addEventListener("input", labels);
  input("destination").addEventListener("input", () => {
    input("verified").checked = false;
    testedLink = "";
  });
  input("verified").addEventListener("change", () => {
    if (
      input("verified").checked &&
      testedLink !== input("destination").value.trim()
    ) {
      input("verified").checked = false;
      status("Use Test link, then confirm it opened your dot.", true);
    }
  });
  element("test-link").addEventListener("click", async () => {
    const url = input("destination").value.trim(),
      error = destinationError(url);
    if (error) return status(error, true);
    try {
      await call("test_destination", { url });
      testedLink = url;
      status(
        "Browser launch requested. If it opened your dot, tick the confirmation box.",
      );
    } catch (e) {
      status(errorText(e), true);
    }
  });
  async function save(p = collect()) {
    if (p.setupCompleted && (!p.verified || !p.destination))
      throw new Error(
        "Test and confirm your destination before finishing setup.",
      );
    if (p.destination) {
      const error = destinationError(p.destination);
      if (error) throw new Error(error);
    }
    if (p.verified && p.destination !== testedLink)
      throw new Error(
        "Test this destination on this device before confirming.",
      );
    await call("save_preferences", { preferences: p });
    saved = (await call<Snapshot>("get_preferences")).preferences;
    if (saved.verified) testedLink = saved.destination;
    fill(saved);
    status("Saved on this device.");
  }
  element("setup-next").addEventListener("click", async () => {
    try {
      const p = collect();
      if (!p.verified || !p.destination)
        throw new Error(
          "Test your link and confirm it opened your dot before continuing.",
        );
      await save(p);
      setupStep++;
      guide(true);
      status(
        setupStep === 1
          ? "Choose an image and your preferred controls, or keep the defaults."
          : "Automatic checks are on. Review update and restart preferences, then finish setup.",
      );
    } catch (e) {
      status(errorText(e), true);
    }
  });
  element("setup-back").addEventListener("click", () => {
    setupStep--;
    guide(true);
  });
  element("preferences").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await save(guided ? { ...collect(), setupCompleted: true } : collect());
      if (guided) {
        guided = false;
        guide();
        status(
          "Setup complete. Click your companion or use your shortcut to open your saved dot. You can change these choices here anytime.",
        );
      }
    } catch (err) {
      status(errorText(err), true);
    }
  });
  element("open").addEventListener("click", async () => {
    try {
      await call("open_destination");
      status("Browser launch requested for your saved destination.");
    } catch (e) {
      status(errorText(e), true);
    }
  });
  for (const [id, action] of [
    ["toggle", "toggle"],
    ["recover", "recover"],
    ["quit", "quit"],
  ])
    element(id).addEventListener("click", async () => {
      try {
        await call("companion_action", { action });
      } catch (e) {
        status(errorText(e), true);
      }
    });
  element("reset-settings").addEventListener("click", async () => {
    if (
      !confirm(
        "Reset local preferences and disable login startup? The original settings file is preserved locally.",
      )
    )
      return;
    try {
      await call("repair_preferences");
      const s = await call<Snapshot>("get_preferences");
      saved = s.preferences;
      guided = s.setupRequired;
      setupStep = 0;
      guide();
      fill(saved);
      testedLink = "";
      element("warning").hidden = true;
      status("Local settings reset. The previous file is preserved.");
    } catch (e) {
      status(errorText(e), true);
    }
  });
  function updateUI(s: UpdateStatus) {
    update = s;
    const messages: Record<string, string> = {
      current: s.notes || "No eligible update.",
      available: `Version ${s.version} is available.`,
      downloading: `Downloading${s.progress === null ? "…" : ` ${s.progress}%`}`,
      installing: s.notes,
      installed: "Update installed. Restart when you are ready.",
      deferred: "Update deferred until your next check.",
      skipped: "This version is skipped for automatic checks.",
      error: s.notes,
    };
    element("update-status").textContent = messages[s.state] || s.state;
    element("release-notes").textContent = s.notes;
    element("release-notes").hidden = s.state !== "available" || !s.notes;
    element("install-update").hidden = s.state !== "available";
    element("defer").hidden = s.state !== "available";
    element("skip").hidden = s.state !== "available";
    element("restart").hidden = s.state !== "installed";
    element<HTMLButtonElement>("check-update").disabled = [
      "downloading",
      "installing",
    ].includes(s.state);
    const progress = element<HTMLProgressElement>("update-progress");
    progress.hidden = s.state !== "downloading";
    if (s.progress === null) progress.removeAttribute("value");
    else progress.value = s.progress;
  }
  element("check-update").addEventListener("click", async () => {
    element<HTMLButtonElement>("check-update").disabled = true;
    element("update-status").textContent = "Checking signed release metadata…";
    try {
      updateUI(await call<UpdateStatus>("check_update"));
    } catch (e) {
      updateUI({
        state: "error",
        notes: errorText(e),
        version: "",
        progress: null,
      });
    }
    element<HTMLButtonElement>("check-update").disabled = false;
  });
  element("install-update").addEventListener("click", async () => {
    if (
      !confirm(
        "Install this signed update now? Save your settings first. The companion may close and OS approval may appear. Other apps remain open.",
      )
    )
      return;
    updateUI({
      state: "downloading",
      notes: "",
      version: update?.version || "",
      progress: null,
    });
    try {
      await call("install_update");
      updateUI({ state: "installed", notes: "", version: "", progress: null });
    } catch (e) {
      updateUI({
        state: "error",
        notes: errorText(e),
        version: "",
        progress: null,
      });
    }
  });
  element("restart").addEventListener("click", async () => {
    try {
      await call("restart_after_update");
    } catch (e) {
      status(errorText(e), true);
    }
  });
  element("defer").addEventListener("click", () =>
    updateUI({ state: "deferred", version: "", notes: "", progress: null }),
  );
  element("skip").addEventListener("click", async () => {
    try {
      if (update?.version) {
        await save({ ...collect(), skippedVersion: update.version });
        updateUI({ state: "skipped", version: "", notes: "", progress: null });
      }
    } catch (e) {
      status(errorText(e), true);
    }
  });
  await on<UpdateStatus>("update-status", updateUI);
  if (snapshot.updateStatus) updateUI(snapshot.updateStatus);
  await on<string>("app-error", (e) => status(e, true));
  await on("preferences-changed", async () => {
    const s = await call<Snapshot>("get_preferences");
    saved = s.preferences;
    fill(saved);
  });
}
const view = new URLSearchParams(location.search).get("view");
void (
  companion
    ? companionUI()
    : view === "chat"
      ? chatUI()
      : view === "bubble"
        ? bubbleUI()
        : settingsUI()
).catch((e) => {
  root.textContent = errorText(e);
});
