import { test, expect } from "@playwright/test";
import { defaults } from "../../src/types";

// Synthetic IPC validates the interface contract, not a live dot connection.
test("Windows opens the shared chat interface without enabling a transport", async ({
  page,
}) => {
  await page.addInitScript((preferences) => {
    const w = window as unknown as {
      isTauri: boolean;
      __TAURI_INTERNALS__: object;
    };
    w.isTauri = true;
    w.__TAURI_INTERNALS__ = {
      transformCallback: () => 1,
      invoke: async (command: string, args?: { action?: string }) => {
        if (command === "plugin:event|listen") return 1;
        if (command === "get_avatar") return { dataUrl: null, warning: null };
        if (command === "get_companion")
          return {
            ...preferences,
            hidden: false,
            configured: false,
            chatEnabled: true,
          };
        if (command === "get_preferences")
          return {
            preferences,
            warning: null,
            version: "1.0.0",
            setupRequired: false,
            chatEnabled: true,
            chatTransportEnabled: false,
            updatesConfigured: false,
            updateStatus: null,
          };
        if (command === "get_chat")
          return {
            connected: false,
            state: "interface-only",
            expiresIn: null,
            messages: [],
          };
        if (command === "companion_action" || command === "open_destination") {
          sessionStorage.setItem("synthetic-action", args?.action || command);
          return;
        }
        throw new Error("Unexpected synthetic command");
      },
    };
  }, defaults);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/?view=companion");
  await page.locator("#pet").click();
  await expect
    .poll(() => page.evaluate(() => sessionStorage.getItem("synthetic-action")))
    .toBe("activate");
  await expect(page.locator("#pet")).toHaveAttribute(
    "aria-label",
    "Chat with my dot",
  );

  await page.goto("/?view=chat");
  await expect(
    page.getByRole("heading", { name: "Your dot", exact: true }),
  ).toBeVisible();
  await expect(page.locator("#connection-state")).toHaveText(
    "Chat is not connected",
  );
  await expect(page.locator("#chat-boundary")).toContainText(
    "Live messaging is not connected",
  );
  await page
    .getByLabel("Message your dot", { exact: true })
    .fill("Synthetic unsent draft");
  await expect(page.locator("#send-message")).toBeDisabled();
  await expect(page.locator("#chat-reconnect")).toBeDisabled();
  await expect(page.locator(".chat-message")).toHaveCount(0);
  await page.locator("#chat-browser").click();
  await expect
    .poll(() => page.evaluate(() => sessionStorage.getItem("synthetic-action")))
    .toBe("open_destination");
  await page.locator("#chat-close").click();
  await expect
    .poll(() => page.evaluate(() => sessionStorage.getItem("synthetic-action")))
    .toBe("close-chat");

  await page.goto("/");
  await expect(page.locator("#open-chat")).toBeVisible();
  await expect(page.locator("#replyPreview")).toBeDisabled();
  await expect(page.locator(".scope-notice")).toContainText(
    "Live messaging is not connected",
  );
  await page.locator("#open-chat").click();
  await expect
    .poll(() => page.evaluate(() => sessionStorage.getItem("synthetic-action")))
    .toBe("chat");
});
