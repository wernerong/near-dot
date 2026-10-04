export interface Preferences {
  schema: number;
  destination: string;
  verified: boolean;
  shortcut: string;
  size: number;
  opacity: number;
  alwaysOnTop: boolean;
  paused: boolean;
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
  shortcut: "CommandOrControl+Shift+D",
  size: 156,
  opacity: 1,
  alwaysOnTop: false,
  paused: false,
  startup: false,
  autoCheck: true,
  unattendedNextLaunch: false,
  channel: "stable",
  skippedVersion: "",
  position: null,
  cohort: 0,
};
export interface Snapshot {
  preferences: Preferences;
  warning: string | null;
  version: string;
  updatesConfigured: boolean;
  updateStatus: UpdateStatus | null;
}
export interface Companion {
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
