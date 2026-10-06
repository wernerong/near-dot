import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

for (const viewport of [
  { width: 390, height: 540 },
  { width: 320, height: 400 },
]) {
  test(`chat reserves space for messages at ${viewport.width}×${viewport.height}`, async ({
    page,
  }) => {
    await page.setViewportSize(viewport);
    // Synthetic IPC checks layout and composer behavior, not a live connection.
    await page.addInitScript(() => {
      const w = window as unknown as {
        isTauri: boolean;
        __TAURI_INTERNALS__: object;
      };
      w.isTauri = true;
      const snapshot = {
        connected: true,
        state: "connected",
        expiresIn: null,
        messages: [
          {
            id: "synthetic-layout",
            text: "Synthetic layout question",
            reply: "Synthetic reply.\n".repeat(35),
            delivered: 1,
            created: 0,
          },
        ],
      };
      w.__TAURI_INTERNALS__ = {
        transformCallback: () => 1,
        invoke: async (command: string, args?: { text?: string }) => {
          if (command === "plugin:event|listen") return 1;
          if (command === "get_avatar") return { dataUrl: null, warning: null };
          if (command === "get_chat") return snapshot;
          if (command === "send_chat") {
            sessionStorage.setItem("synthetic-sent-text", args?.text || "");
            return snapshot;
          }
          throw new Error("Unexpected synthetic command");
        },
      };
    });
    await page.goto("/?view=chat");
    await expect(page.locator("#connection-state")).toHaveText(
      "Connected to your dot",
    );
    const messages = page.locator("#chat-messages");
    await expect(page.locator(".chat-message")).toHaveCount(2);
    expect((await messages.boundingBox())!.height).toBeGreaterThan(
      viewport.height * 0.53,
    );
    expect(
      (await page.locator(".chat-footer").boundingBox())!.height,
    ).toBeLessThan(36);
    expect(
      await messages.evaluate((e) => e.scrollHeight > e.clientHeight),
    ).toBe(true);
    expect(
      await page.evaluate(() => document.body.scrollHeight <= innerHeight),
    ).toBe(true);

    const composer = page.getByLabel("Message your dot", { exact: true });
    const initialHeight = (await composer.boundingBox())!.height;
    await composer.fill("Synthetic first line");
    await composer.press("Shift+Enter");
    await composer.press("Shift+Enter");
    await composer.press("Shift+Enter");
    await expect(composer).toHaveValue("Synthetic first line\n\n\n");
    expect((await composer.boundingBox())!.height).toBeGreaterThan(
      initialHeight,
    );
    expect((await composer.boundingBox())!.height).toBeLessThanOrEqual(80);
    await composer.press("Enter");
    await expect(composer).toHaveValue("");
    expect((await composer.boundingBox())!.height).toBe(initialHeight);
    expect(
      await page.evaluate(() => sessionStorage.getItem("synthetic-sent-text")),
    ).toBe("Synthetic first line\n\n\n");

    const summary = page.getByText("Connection options", { exact: true });
    await summary.focus();
    await summary.press("Enter");
    for (const id of ["chat-setup", "chat-reconnect", "chat-browser"])
      await expect(page.locator(`#${id}`)).toBeVisible();
    expect(
      await page.evaluate(() => document.body.scrollHeight <= innerHeight),
    ).toBe(true);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(
      results.violations.map((v) => ({
        id: v.id,
        targets: v.nodes.map((n) => n.target),
      })),
    ).toEqual([]);
    await summary.press("Enter");
    expect((await messages.boundingBox())!.height).toBeGreaterThan(
      viewport.height * 0.53,
    );
  });
}
