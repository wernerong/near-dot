import { test, expect } from "@playwright/test";
import { defaults } from "../../src/types";
import pkg from "../../package.json" with { type: "json" };
const { version } = pkg;

// UI contract test only: synthetic IPC does not prove ChatGPT access or OS launching.
test("fresh setup tests a link, saves choices and stays complete after reopening", async ({
  page,
}) => {
  await page.addInitScript(
    ({ defaults, version }) => {
      const w = window as unknown as {
        isTauri: boolean;
        __TAURI_INTERNALS__: object;
      };
      w.isTauri = true;
      let tested = "";
      w.__TAURI_INTERNALS__ = {
        transformCallback: () => 1,
        invoke: async (
          command: string,
          args: { preferences?: typeof defaults; url?: string },
        ) => {
          const stored = sessionStorage.getItem("synthetic-preferences");
          const preferences = stored ? JSON.parse(stored) : defaults;
          if (command === "get_preferences")
            return {
              preferences,
              version,
              warning: null,
              setupRequired: !preferences.setupCompleted,
              chatEnabled: false,
              updatesConfigured: true,
              updateStatus: null,
            };
          if (command === "get_avatar") return { dataUrl: null, warning: null };
          if (command === "plugin:event|listen") return 1;
          if (command === "test_destination") {
            tested = args.url!;
            return;
          }
          if (command === "save_preferences") {
            if (
              args.preferences!.verified &&
              !preferences.verified &&
              tested !== args.preferences!.destination
            )
              throw new Error("Use Test link first.");
            sessionStorage.setItem(
              "synthetic-preferences",
              JSON.stringify(args.preferences),
            );
            return;
          }
          throw new Error("Unsupported synthetic UI command");
        },
      };
    },
    { defaults, version },
  );
  await page.goto("/");
  await expect(
    page.getByRole("region", { name: "First-run setup" }),
  ).toBeVisible();
  await expect(page.locator("#version")).toHaveText(`v${version}`);
  await expect(page.getByLabel("Start at login", { exact: true })).toBeHidden();
  await expect(
    page.getByRole("button", { name: "Chat with my dot", exact: true }),
  ).toBeHidden();
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.locator("#status")).toContainText("Test your link");
  await page
    .getByLabel("Your destination", { exact: true })
    .fill("https://chatgpt.com/c/synthetic-setup");
  await page.getByRole("button", { name: "Test link" }).click();
  await page.getByLabel("I tested this link").check();
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByLabel("Always on top", { exact: true })).toBeChecked();
  await expect(
    page.getByLabel("Start at login", { exact: true }),
  ).not.toBeChecked();
  await page.getByLabel("Pause animation", { exact: true }).check();
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(
    page.getByLabel("Check automatically every 6 hours"),
  ).toBeChecked();
  await expect(page.getByLabel("Channel", { exact: true })).toHaveValue(
    "preview",
  );
  await page.locator("#preview-note").evaluate((e) => {
    (e as HTMLElement).hidden = false;
    e.textContent =
      "Setup UI preview · synthetic preferences; OS launching and update service are not exercised.";
  });
  await page.screenshot({
    path: "docs/onboarding-preview.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Finish setup" }).click();
  await expect(page.locator("#status")).toContainText("Setup complete");
  await page.reload();
  await expect(
    page.getByRole("region", { name: "First-run setup" }),
  ).toBeHidden();
  await expect(
    page.getByLabel("Pause animation", { exact: true }),
  ).toBeChecked();
  await expect(
    page.getByLabel("Your destination", { exact: true }),
  ).toHaveValue("https://chatgpt.com/c/synthetic-setup");
});
