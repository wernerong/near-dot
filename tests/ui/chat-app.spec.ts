import { test, expect } from "@playwright/test";
import { defaults } from "../../src/types";

// IPC contract only. No ChatGPT account, browser login, or native Edge launch.
test("Windows setup uses the saved dot address without a window picker or API setup", async ({
  page,
}) => {
  await page.addInitScript((defaults) => {
    const w = window as unknown as {
      isTauri: boolean;
      __TAURI_INTERNALS__: object;
    };
    w.isTauri = true;
    w.__TAURI_INTERNALS__ = {
      transformCallback: () => 1,
      invoke: async (
        command: string,
        args?: { url?: string; mode?: string; preferences?: typeof defaults },
      ) => {
        const raw = sessionStorage.getItem("synthetic-app-settings");
        const preferences = raw
          ? JSON.parse(raw)
          : { ...defaults, chatMode: "app" };
        if (command === "plugin:event|listen") return 1;
        if (command === "get_avatar") return { dataUrl: null, warning: null };
        if (command === "get_preferences")
          return {
            preferences,
            version: "1.0.3",
            warning: null,
            setupRequired: !preferences.setupCompleted,
            desktopChatSupported: true,
            chatEnabled: true,
            chatTransportEnabled: true,
            updatesConfigured: false,
            updateStatus: null,
          };
        if (command === "test_destination") {
          sessionStorage.setItem("synthetic-app-test", JSON.stringify(args));
          return;
        }
        if (command === "save_preferences") {
          sessionStorage.setItem(
            "synthetic-app-settings",
            JSON.stringify(args?.preferences),
          );
          return;
        }
        throw new Error(`Unexpected command: ${command}`);
      },
    };
  }, defaults);
  await page.goto("/");
  await expect(page.getByLabel("Chat connection")).toHaveValue("app");
  await expect(page.locator("#chat-mode-help")).toContainText(
    "No window selection or relinking",
  );
  await expect(page.locator(".scope-notice")).toContainText(
    "no Codex allowance",
  );
  await page
    .getByLabel("Your destination", { exact: true })
    .fill("https://chatgpt.com/c/synthetic-app");
  await page.getByRole("button", { name: "Test link" }).click();
  expect(
    await page.evaluate(() =>
      JSON.parse(sessionStorage.getItem("synthetic-app-test")!),
    ),
  ).toMatchObject({ mode: "app", url: "https://chatgpt.com/c/synthetic-app" });
  await page.getByLabel("I tested this link").check();
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.locator("#private-controls")).toBeHidden();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Finish setup" }).click();
  await expect(page.locator("#status")).toContainText("reopens automatically");
  await page.reload();
  await expect(
    page.getByRole("region", { name: "First-run setup" }),
  ).toBeHidden();
  await expect(page.getByLabel("Chat connection")).toHaveValue("app");
  await expect(
    page.getByLabel("Your destination", { exact: true }),
  ).toHaveValue("https://chatgpt.com/c/synthetic-app");
});

test("dedicated-chat pet activates the app route without a relay reply badge", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.addInitScript((defaults) => {
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
            ...defaults,
            desktopChat: true,
            chatEnabled: false,
            configured: true,
            hidden: false,
          };
        if (command === "companion_action") {
          sessionStorage.setItem(
            "synthetic-app-activation",
            args?.action || "",
          );
          return;
        }
        throw new Error(`Unexpected command: ${command}`);
      },
    };
  }, defaults);
  await page.goto("/?view=companion");
  await expect(page.locator("#pet")).toHaveAccessibleName("Chat with my dot");
  await expect(page.locator("#pet-reply")).toBeHidden();
  await page.locator("#pet").click();
  expect(
    await page.evaluate(() =>
      sessionStorage.getItem("synthetic-app-activation"),
    ),
  ).toBe("activate");
});
