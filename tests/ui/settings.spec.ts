import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
test("settings passes automated WCAG A/AA accessibility checks", async ({
  page,
}) => {
  await page.goto("/");
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  expect(
    results.violations.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
});
test("setup exposes its boundary and rejects unsafe destinations", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Your dot. One click away." }),
  ).toBeVisible();
  await expect(page.getByText("Browser preview •")).toBeVisible();
  await page
    .getByLabel("Your destination", { exact: true })
    .fill("https://chatgpt.com.evil.test/c/synthetic");
  await page.getByRole("button", { name: "Test link" }).click();
  await expect(page.locator("#status")).toHaveText(
    "Only HTTPS links on chatgpt.com are allowed.",
  );
  await page
    .getByLabel("Your destination", { exact: true })
    .fill("https://chatgpt.com/c/synthetic-test");
  await page.getByLabel("I tested this link").click();
  await expect(page.getByLabel("I tested this link")).not.toBeChecked();
  await expect(page.locator("#status")).toContainText("Use Test link");
});
test("settings save locally in inert preview and update failure is honest", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByLabel("Pause animation", { exact: true }).check();
  await page.getByRole("button", { name: "Save settings" }).click();
  await expect(page.locator("#status")).toContainText("Saved on this device.");
  await page.getByRole("button", { name: "Check for updates" }).click();
  await expect(page.locator("#update-status")).toContainText(
    "Browser preview only.",
  );
  await expect(
    page.getByRole("button", { name: "Install update" }),
  ).toBeHidden();
});
test("keyboard setup, reduced motion and public screenshot", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await page.getByLabel("Your destination", { exact: true }).focus();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Test link" })).toBeFocused();
  await page.screenshot({ path: "docs/settings-preview.png", fullPage: true });
  await page.goto("/?view=companion");
  await expect(page.locator("#pet")).toHaveAccessibleName("Chat with my dot");
  expect(
    await page
      .locator(".pet")
      .evaluate((e) => getComputedStyle(e).animationName),
  ).toBe("none");
  await page.setViewportSize({ width: 156, height: 176 });
  await page.screenshot({
    path: "docs/companion-preview.png",
    omitBackground: true,
  });
});

test("local image setup states privacy and does not invent dot activity", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByText("Idle movement is decorative.", { exact: false }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Choose local image", exact: true })
    .click();
  await expect(page.locator("#status")).toContainText("Browser preview only.");
  await expect(
    page.getByRole("button", { name: "Choose local image", exact: true }),
  ).toBeEnabled();
  await expect(page.locator("#hero-image")).toHaveAttribute(
    "src",
    "/companion.svg",
  );
});

test("chat preview is accessible, keyboard ready and cannot fabricate messages", async ({
  page,
}) => {
  await page.goto("/?view=chat");
  await expect(
    page.getByRole("heading", { name: "Your dot", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Connection unavailable", { exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("Message your dot", { exact: true })
    .fill("Explicit synthetic offline UI test");
  await expect(
    page.getByRole("button", { name: "Send ↑", exact: true }),
  ).toBeDisabled();
  expect(await page.locator(".chat-message").count()).toBe(0);
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  expect(
    results.violations.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
});

test("reply bubble has accessible read and dismiss actions", async ({
  page,
}) => {
  await page.goto("/?view=bubble");
  await expect(
    page.getByRole("button", {
      name: "Your dot replied Click to read and respond.",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Dismiss reply", exact: true }),
  ).toBeVisible();
});
