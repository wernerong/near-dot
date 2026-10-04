import pkg from "../package.json" with { type: "json" };
const { version } = pkg;
import { invoke, isTauri } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { defaults, type Snapshot } from "./types";
export const preview = !isTauri();
let previewPreferences = { ...defaults };
// Browser preview is deliberately inert: no launch, persistence, update or OS simulation.
export async function call<T = void>(
  command: string,
  args?: Record<string, unknown>,
): Promise<T> {
  if (!preview) return invoke<T>(command, args);
  if (command === "get_preferences")
    return {
      preferences: previewPreferences,
      warning: null,
      version,
      updatesConfigured: false,
      setupRequired:
        !previewPreferences.setupCompleted && !previewPreferences.verified,
      chatEnabled: false,
      updateStatus: null,
    } satisfies Snapshot as T;
  if (command === "get_companion")
    return {
      ...previewPreferences,
      hidden: false,
      configured: false,
      chatEnabled: false,
    } as T;
  if (command === "get_chat")
    return {
      connected: false,
      state: "preview",
      expiresIn: null,
      messages: [],
    } as T;
  if (command === "get_avatar") return { dataUrl: null, warning: null } as T;
  if (command === "save_preferences") {
    previewPreferences = { ...(args?.preferences as typeof defaults) };
    return undefined as T;
  }
  if (command === "repair_preferences") {
    previewPreferences = { ...defaults };
    return undefined as T;
  }
  throw new Error(
    "Browser preview only. Run the desktop app to use this action.",
  );
}
export async function on<T>(event: string, handler: (payload: T) => void) {
  if (!preview) return listen<T>(event, (e) => handler(e.payload));
  return () => {};
}
