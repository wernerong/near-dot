import { test, expect } from "@playwright/test";

for (const connected of [true, false]) {
  test(`stalled chat recovery preserves the saved message, connected=${connected}`, async ({
    page,
  }) => {
    await page.addInitScript((connected) => {
      const w = window as unknown as {
        isTauri: boolean;
        __TAURI_INTERNALS__: object;
      };
      w.isTauri = true;
      const snapshot = {
        connected,
        state: connected ? "connected" : "disconnected",
        expiresIn: null,
        messages: [
          {
            id: "synthetic-stalled-message",
            text: "Synthetic saved question",
            reply: null,
            delivered: 1,
            created: Date.now() / 1000 - 600,
            lastAttempt: 0,
          },
        ],
      };
      w.__TAURI_INTERNALS__ = {
        transformCallback: () => 1,
        invoke: async (command: string, args?: { messageId?: string }) => {
          if (command === "plugin:event|listen") return 1;
          if (command === "get_avatar") return { dataUrl: null, warning: null };
          if (command === "get_chat") return snapshot;
          if (command === "retry_chat") {
            sessionStorage.setItem(
              "synthetic-retried-id",
              args?.messageId || "",
            );
            snapshot.messages[0].lastAttempt = Date.now() / 1000;
            return snapshot;
          }
          throw new Error("Unexpected synthetic operation");
        },
      };
    }, connected);
    await page.goto("/?view=chat");
    await expect(page.locator(".message-delivery")).toContainText(
      "ChatGPT accepted delivery, but no reply arrived.",
    );
    const retry = page.getByRole("button", { name: "Request reply again" });
    await expect(retry).toBeVisible();
    if (!connected) {
      await expect(retry).toBeDisabled();
      return;
    }
    await retry.focus();
    await retry.press("Enter");
    await expect(retry).toHaveCount(0);
    expect(
      await page.evaluate(() => sessionStorage.getItem("synthetic-retried-id")),
    ).toBe("synthetic-stalled-message");
    await expect(page.locator(".chat-message.outgoing")).toHaveCount(1);
    await expect(page.locator(".message-delivery")).toHaveText(
      "Delivered to ChatGPT · waiting for a reply…",
    );
    await expect(page.locator("#connection-state")).toHaveText(
      "Relay connected",
    );
  });
}
