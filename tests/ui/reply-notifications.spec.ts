import { test, expect, type Page } from "@playwright/test";
import { defaults } from "../../src/types";

async function receiverFixture(
  page: Page,
  notifications = false,
  initialPreview = "Click to read and respond.",
  delayedPreview = false,
) {
  await page.addInitScript(
    ({ defaults, notifications, initialPreview, delayedPreview }) => {
      const w = window as unknown as {
        isTauri: boolean;
        __TAURI_INTERNALS__: object;
        syntheticNotice: (event: string, payload: unknown) => void;
        syntheticResolvePreview: (text: string) => void;
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
          if (command === "get_reply_preview") {
            if (delayedPreview)
              return new Promise((resolve) => {
                w.syntheticResolvePreview = (text) => resolve({ text });
              });
            return { text: initialPreview };
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
    { defaults, notifications, initialPreview, delayedPreview },
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

for (const size of [48, 68]) {
  test(`opening and focus errors leave the ${size}px pet visible and clickable`, async ({
    page,
  }) => {
    await receiverFixture(page, true);
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.setViewportSize({ width: size, height: size });
    await page.goto("/?view=companion");
    const pet = page.locator("#pet");
    const image = page.locator("#companion-image");
    const before = await image.boundingBox();
    const notice = async (event: string, payload: unknown) =>
      page.evaluate(
        ({ event, payload }) =>
          (
            window as unknown as {
              syntheticNotice: (event: string, payload: unknown) => void;
            }
          ).syntheticNotice(event, payload),
        { event, payload },
      );
    await expect(page.locator("#pet-error")).toBeHidden();
    await notice("desktop-opening", true);
    await expect(pet).toBeDisabled();
    await expect(page.locator("#pet-error")).toHaveText("…");
    const message =
      "ChatGPT is visible beside the pet. Windows blocked keyboard focus; click the chat to type.";
    await notice("desktop-error", message);
    await notice("desktop-opening", false);
    const badge = page.locator("#pet-error");
    await expect(badge).toHaveText("!");
    await expect(badge).toHaveAccessibleName(message);
    await expect(badge).toHaveAttribute("title", message);
    await expect(pet).toBeEnabled();
    expect(await image.boundingBox()).toEqual(before);
    const bounds = await badge.boundingBox();
    expect(bounds!.width).toBeLessThanOrEqual(16);
    expect(bounds!.height).toBeLessThanOrEqual(16);
    expect(
      await page.evaluate(() => {
        const image = document
          .getElementById("companion-image")!
          .getBoundingClientRect();
        return document.elementFromPoint(
          image.x + image.width / 2,
          image.y + image.height / 2,
        )?.id;
      }),
    ).toBe("pet");
    await badge.click();
    expect(
      await page.evaluate(() =>
        sessionStorage.getItem("synthetic-notification-action"),
      ),
    ).toBe("desktop-status");
    await notice("desktop-opening", true);
    await notice("desktop-opening", false);
    await expect(badge).toBeHidden();
    await pet.click();
    expect(
      await page.evaluate(() =>
        sessionStorage.getItem("synthetic-notification-action"),
      ),
    ).toBe("activate");
  });
}

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

test("the first visible bubble loads the whole bounded preview without a click or event", async ({
  page,
}) => {
  const text = "合成".repeat(80);
  await receiverFixture(page, true, text);
  await page.setViewportSize({ width: 300, height: 200 });
  await page.goto("/?view=bubble");
  await expect(page.locator("#bubble-text")).toHaveText(text);
  const bounds = await page.locator("#bubble-text").boundingBox();
  expect(bounds!.y + bounds!.height).toBeLessThan(196);
  expect(
    await page
      .locator("#bubble-text")
      .evaluate((node) => node.scrollHeight <= node.clientHeight),
  ).toBe(true);
  expect(
    await page.evaluate(() =>
      sessionStorage.getItem("synthetic-notification-action"),
    ),
  ).toBeNull();
});

test("an incoming preview wins over a delayed initial snapshot", async ({
  page,
}) => {
  await receiverFixture(page, true, "Synthetic old preview", true);
  await page.goto("/?view=bubble");
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          typeof (window as unknown as { syntheticResolvePreview?: unknown })
            .syntheticResolvePreview,
      ),
    )
    .toBe("function");
  await page.evaluate(() => {
    const w = window as unknown as {
      syntheticNotice: (event: string, payload: unknown) => void;
      syntheticResolvePreview: (text: string) => void;
    };
    w.syntheticNotice("reply-preview", { text: "Synthetic current preview" });
    w.syntheticResolvePreview("Synthetic old preview");
  });
  await expect(page.locator("#bubble-text")).toHaveText(
    "Synthetic current preview",
  );
});
