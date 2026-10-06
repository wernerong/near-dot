import pkg from "../package.json" with { type: "json" };
const { version } = pkg;

export interface Preferences {
  schema: number;
  destination: string;
  verified: boolean;
  setupCompleted: boolean;
  shortcut: string;
  size: number;
  opacity: number;
  alwaysOnTop: boolean;
  paused: boolean;
  replyPreview: boolean;
  startup: boolean;
  autoCheck: boolean;
  unattendedNextLaunch: boolean;
  channel: string;
  skippedVersion: string;
  position: [number, number] | null;
  cohort: number;
}
export const defaults: Preferences = {
  schema: 1,
  destination: "",
  verified: false,
  setupCompleted: false,
  shortcut: "CommandOrControl+Shift+D",
  size: 156,
  opacity: 1,
  alwaysOnTop: true,
  paused: false,
  replyPreview: false,
  startup: false,
  autoCheck: true,
  unattendedNextLaunch: false,
  channel: version.includes("-") ? "preview" : "stable",
  skippedVersion: "",
  position: null,
  cohort: 0,
};
export interface Snapshot {
  preferences: Preferences;
  warning: string | null;
  version: string;
  updatesConfigured: boolean;
  setupRequired: boolean;
  chatEnabled: boolean;
  chatTransportEnabled: boolean;
  updateStatus: UpdateStatus | null;
}
export interface Companion {
  chatEnabled: boolean;
  alwaysOnTop: boolean;
  size: number;
  opacity: number;
  paused: boolean;
  hidden: boolean;
  configured: boolean;
}
export interface Avatar {
  dataUrl: string | null;
  warning: string | null;
}
export interface UpdateStatus {
  state: string;
  version: string;
  notes: string;
  progress: number | null;
}

export interface ChatMessage {
  id: string;
  text: string;
  created: number;
  delivered: number;
  reply: string | null;
}
export interface ChatSnapshot {
  setupSupported?: boolean;
  connected: boolean;
  state: string;
  expiresIn: number | null;
  messages: ChatMessage[];
}
