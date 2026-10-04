import { describe, expect, it } from "vitest";
import { destinationError, shouldDrag } from "../src/validation";
describe("destination input", () => {
  it("accepts a synthetic private path without assuming it is a dot", () =>
    expect(
      destinationError("https://chatgpt.com/c/synthetic-test"),
    ).toBeNull());
  it.each([
    "https://chatgpt.com/share/example",
    "https://chatgpt.com.evil.test/c/test",
    "file:///test.exe",
    "https://chatgpt.com/files/unsafe.exe",
    "javascript:alert(1)",
    "https://user:pass@chatgpt.com/c/test",
    "https://chatgpt.com/c/test?token=secret",
    "https://chatgpt.com/c/test#secret",
    "https://chatgpt.com/",
    "https://chatgpt.com/backend-api/test",
  ])("rejects %s", (value) => expect(destinationError(value)).not.toBeNull());
});
it("distinguishes click jitter from intentional dragging", () => {
  expect(shouldDrag([10, 10], [12, 12])).toBe(false);
  expect(shouldDrag([10, 10], [17, 10])).toBe(true);
});
