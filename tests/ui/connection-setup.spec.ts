import { test, expect } from "@playwright/test";

test("per-user setup uses native commands and waits for the dot subscription", async ({
  page,
}) => {
  await page.addInitScript(() => {
    const w = window as unknown as {
      isTauri: boolean;
      __TAURI_INTERNALS__: object;
    };
    w.isTauri = true;
    let state = "unconfigured";
    w.__TAURI_INTERNALS__ = {
      transformCallback: () => 1,
      invoke: async (command: string, args?: { action?: string }) => {
        if (command === "plugin:event|listen") return 1;
        if (command === "get_avatar") return { dataUrl: null, warning: null };
        if (command === "get_chat")
          return {
            connected: false,
            transportRunning: state === "awaiting-dot",
            state,
            expiresIn: null,
            messages: [],
          };
        if (command === "chat_setup") {
          sessionStorage.setItem("synthetic-setup-args", JSON.stringify(args));
          if (args?.action === "configure") state = "awaiting-dot";
          if (args?.action === "disconnect") state = "paused";
          return;
        }
        if (command === "connect_chat") {
          state = "awaiting-dot";
          return;
        }
        throw new Error("Unexpected synthetic command");
      },
    };
  });
  await page.goto("/?view=chat");
  await expect(page.locator("#send-message")).toBeDisabled();
  await page
    .getByRole("button", { name: "Connect my dot", exact: true })
    .click();
  await expect(page.locator("#connection-setup")).toBeVisible();
  await expect(page.locator("#connection-setup input")).toHaveCount(0);
  await page.locator("#setup-configure").click();
  await expect(page.locator("#setup-status")).toContainText(
    "Local connection saved",
  );
  await expect(page.locator("#connection-state")).toHaveText(
    "Waiting for your dot to connect",
  );
  await expect(page.locator("#send-message")).toBeDisabled();
  await expect
    .poll(() =>
      page.evaluate(() => sessionStorage.getItem("synthetic-setup-args")),
    )
    .toBe('{"action":"configure"}');
  await page.locator("#setup-disconnect").click();
  await expect(page.locator("#connection-state")).toHaveText(
    "Disconnected on this device",
  );
  await page.locator("#setup-close").click();
  await page.locator("#chat-reconnect").click();
  await expect(page.locator("#connection-state")).toHaveText(
    "Waiting for your dot to connect",
  );
  await expect(page.locator("#send-message")).toBeDisabled();
});
