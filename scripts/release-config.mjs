import fs from "node:fs";
import path from "node:path";
import { checkVersions } from "./versions.mjs";
const repo = process.env.NEAR_DOT_UPDATE_REPO;
const key = process.env.NEAR_DOT_UPDATER_PUBLIC_KEY;
checkVersions();
if (!repo || !/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(repo))
  throw new Error(
    "Set NEAR_DOT_UPDATE_REPO to the reviewed public owner/repository.",
  );
const decodedKey = Buffer.from(key || "", "base64")
  .toString()
  .trim()
  .split(/\r?\n/);
const publicBytes = Buffer.from(decodedKey[1] || "", "base64");
if (
  !key ||
  decodedKey.length !== 2 ||
  !decodedKey[0].startsWith("untrusted comment: minisign public key") ||
  publicBytes.length !== 42 ||
  publicBytes.subarray(0, 2).toString("ascii") !== "Ed"
)
  throw new Error(
    "Set the Tauri verification PUBLIC key. Never provide a private key here.",
  );
if (key !== fs.readFileSync("updater-public-key.txt", "utf8").trim())
  throw new Error(
    "Release verification key does not match the reviewed source key.",
  );
const config = {
  bundle: { createUpdaterArtifacts: true },
  plugins: {
    updater: {
      pubkey: key,
      requireSignedVersion: true,
      endpoints: [
        `https://raw.githubusercontent.com/${repo}/main/channels/stable.json`,
      ],
    },
  },
};
const osSigning = process.env.NEAR_DOT_OS_SIGNING || "signed";
if (!["signed", "unsigned"].includes(osSigning))
  throw new Error("Choose signed or unsigned OS distribution explicitly.");
if (process.platform === "win32" && osSigning === "signed")
  config.bundle.windows = {
    signCommand: {
      cmd: "powershell",
      args: [
        "-NoProfile",
        "-File",
        path.resolve("scripts/sign-windows.ps1"),
        "%1",
      ],
    },
  };
if (process.platform === "darwin" && osSigning === "unsigned")
  config.bundle.macOS = { signingIdentity: "-" };
fs.writeFileSync("release-config.json", JSON.stringify(config, null, 2) + "\n");
console.log("Release configuration generated with a public verification key.");
