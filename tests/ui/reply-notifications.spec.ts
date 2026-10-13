import { test, expect, type Page } from "@playwright/test";
import { defaults } from "../../src/types";

async function receiverFixture(page: Page, notifications = false) {
  await page.addInitScript(
    ({ defaults, notifications }) => {
      const w = window as unknown as {
        isTauri: boolean;
        __TAURI_INTERNALS__: object;
        syntheticNotice: (event: string, payload: unknown) => void;
      };
      w.isTauri = true;
      let serial = 0;
      const callbacks = new Map<number, (value: unknown) => void>();
      const events = new Map<string, number>();
      w.syntheticNotice = (event, payload) =>
        callbacks.get(events.get(event)!)?.({ payload });
      w.__TAURI_INTERNALS__ = {
        transformCallback: (callback: (value: unknown) => void) => {
          callbacks.set(++serial, callback);
          return serial;
        },
        invoke: async (
          command: string,
          args?: {
            event?: string;
            handler?: number;
            action?: string;
            preferences?: typeof defaults;
          },
        ) => {
          const preferences = JSON.parse(
            sessionStorage.getItem("synthetic-notification-settings") || "null",
          ) || {
            ...defaults,
            chatMode: "app",
            replyNotifications: notifications,
            setupCompleted: true,
            verified: true,
          destination: "https://chatgpt.com/c/synthetic-notice",
          };
          if (command === "plugin:event|listen") {
            events.set(args!.event!, args!.handler!);
            return serial;
          }
          if (command === "get_avatar") return { dataUrl: null, warning: null };
          if (command === "get_preferences")
            return {
              preferences,
              version: "1.2.0",
              setupRequired: false,
              warning: null,
              desktopChatSupported: true,
              chatEnabled: true,
              chatTransportEnabled: true,
              updatesConfigured: false,
              updateStatus: null,
            };
          if (command === "get_companion")
            return {
              ...preferences,
              desktopChat: true,
              chatEnabled: false,
              hidden: false,
              configured: true,
            };
          if (command === "save_preferences") {
            sessionStorage.setItem(
              "synthetic-notification-settings",
              JSON.stringify(args!.preferences),
            );
            return;
          }
          if (command === "companion_action") {
            sessionStorage.setItem(
              "synthetic-notification-action",
              args!.action!,
            );
            return;
          }
          throw new Error(
            `Unexpected synthetic notification command: ${command}`,
          );
        },
      };
    },
    { defaults, notifications },
  );
}

test("reply notification opt-in persists while chat stays in the dedicated browser", async ({
  page,
}) => {
  await receiverFixture(page);
  await page.goto("/");
  await expect(
    page.getByLabel("Incoming reply notifications beside the pet"),
  ).not.toBeChecked();
  await expect(page.locator("#private-controls")).toBeHidden();
  await page.getByLabel("Incoming reply notifications beside the pet").check();
  await expect(
    page.getByLabel("Show message text in desktop reply bubbles"),
  ).not.toBeChecked();
  await page.getByRole("button", { name: "Save settings" }).click();
  await page.reload();
  await expect(
    page.getByLabel("Incoming reply notifications beside the pet"),
  ).toBeChecked();
  await expect(page.getByLabel("Chat connection")).toHaveValue("app");
  await expect(page.locator("#private-controls")).toBeHidden();
  await page
    .getByRole("button", { name: "Connect reply notifications", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toContainText(
    "does not inspect the browser",
  );
});

test("connected notification badge opens the latest notice without a relay composer", async ({
  page,
}) => {
  await receiverFixture(page, true);
  await page.goto("/?view=companion");
  await expect(page.locator("#pet-reply")).toBeVisible();
  await page.evaluate(() =>
    (
      window as unknown as {
        syntheticNotice: (event: string, payload: unknown) => void;
      }
    ).syntheticNotice("reply-available", true),
  );
  await expect(page.locator("#pet-reply")).toContainText("●");
  await page.locator("#pet-reply").click();
  expect(
    await page.evaluate(() =>
      sessionStorage.getItem("synthetic-notification-action"),
    ),
  ).toBe("latest-reply");
});

test("a bubble treats incoming previews as literal text and opens the actual chat route", async ({
  page,
}) => {
  await receiverFixture(page, true);
  await page.goto("/?view=bubble");
  const text = '<img src="synthetic" onerror="synthetic">';
  await page.evaluate(
    (text) =>
      (
        window as unknown as {
          syntheticNotice: (event: string, payload: unknown) => void;
        }
      ).syntheticNotice("reply-preview", { text }),
    text,
  );
  await expect(page.locator("#bubble-text")).toHaveText(text);
  await expect(page.locator("#bubble-text img")).toHaveCount(0);
  await page.locator("#bubble-open").click();
  expect(
    await page.evaluate(() =>
      sessionStorage.getItem("synthetic-notification-action"),
    ),
  ).toBe("chat");
});
