import fs from "node:fs";
import path from "node:path";
const repo = process.env.NEAR_DOT_UPDATE_REPO;
const key = process.env.NEAR_DOT_UPDATER_PUBLIC_KEY;
const version = JSON.parse(fs.readFileSync("package.json", "utf8")).version;
const tauriVersion = JSON.parse(
  fs.readFileSync("src-tauri/tauri.conf.json", "utf8"),
).version;
const cargoVersion = fs
  .readFileSync("src-tauri/Cargo.toml", "utf8")
  .match(/^version\s*=\s*"([^"]+)"/m)?.[1];
if (version !== tauriVersion || version !== cargoVersion)
  throw new Error(
    "Package, Tauri and Cargo versions must match before release.",
  );
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
const config = {
  bundle: { createUpdaterArtifacts: true },
  plugins: {
    updater: {
      pubkey: key,
      endpoints: [
        `https://raw.githubusercontent.com/${repo}/main/channels/stable.json`,
      ],
    },
  },
};
if (process.platform === "win32")
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
fs.writeFileSync("release-config.json", JSON.stringify(config, null, 2) + "\n");
console.log("Release configuration generated with a public verification key.");
